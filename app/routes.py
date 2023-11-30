# ******************************************************************************
#  Copyright (c) 2020-2021 University of Stuttgart
#
#  See the NOTICE file(s) distributed with this work for additional
#  information regarding copyright ownership.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ******************************************************************************

from app import app, implementation_handler, db, parameters
from app.result_model import Result
from app.tket_handler import get_backend, is_tk_circuit, setup_credentials, tket_analyze_original_circuit, \
    tket_transpile_circuit, UnsupportedGateException, TooManyQubitsException, get_depth_without_barrier, \
    prepare_transpile_response, get_number_of_multi_qubit_gates, get_multi_qubit_gate_depth, \
    get_number_of_measurement_operations

from flask import jsonify, abort, request
import logging
import json
import base64


@app.route('/pytket-service/api/v1.0/analyze-original-circuit', methods=['POST'])
def analyze_original_circuit():
    if not request.json or not 'impl-language' in request.json:
        abort(400)

    impl_language = request.json["impl-language"]

    circuit = None
    short_impl_name = ""

    impl_url = request.json['impl-url'] if 'impl-url' in request.json else None
    impl_data = base64.standard_b64decode(
        request.json['impl-data'].encode()).decode() if 'impl-data' in request.json else None

    bearer_token = request.json.get("bearer-token", "")

    try:
        circuit, short_impl_name = implementation_handler.prepare_code(impl_url, impl_data, impl_language, {'token': ''},
                                                                       bearer_token)
    except ValueError:
        abort(400)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    if not circuit:
        app.logger.info(f"Analysis of original circuit {short_impl_name}: Failed to create circuit.")
        return jsonify({'error': "Failed to create circuit."}), 400

    non_transpiled_width = None
    non_transpiled_depth = None
    non_transpiled_multi_qubit_gate_depth = None
    non_transpiled_total_number_of_operations = None
    non_transpiled_number_of_multi_qubit_gates = None
    non_transpiled_number_of_measurement_operations = None
    non_transpiled_number_of_single_qubit_gates = None

    precompiled_circuit = False
    while not is_tk_circuit(circuit):

        try:
            circuit, \
            non_transpiled_width, \
            non_transpiled_depth, \
            non_transpiled_multi_qubit_gate_depth, \
            non_transpiled_total_number_of_operations, \
            non_transpiled_number_of_multi_qubit_gates, \
            non_transpiled_number_of_measurement_operations, \
            non_transpiled_number_of_single_qubit_gates \
                = tket_analyze_original_circuit(circuit,
                                                impl_language=impl_language,
                                                short_impl_name=short_impl_name,
                                                logger=app.logger.info,
                                                precompile_circuit=precompiled_circuit)

        except UnsupportedGateException as e:

            # unsupported gate type caused circuit conversion to fail
            app.logger.warn(f"Unsupported gate ({e.gate}) in implementation {short_impl_name}.")

            # precompile the circuit and retry
            if not precompiled_circuit:
                precompiled_circuit = True
                continue
            else:
                app.logger.warn(f"Precompiling {short_impl_name} failed.")
                break

        except Exception as e:
            app.logger.warn(f"Circuit analysis unexpectedly failed for {short_impl_name}: {str(e)}")
            abort(500)

    response = {'original-width': non_transpiled_width,
                'original-depth': non_transpiled_depth,
                'original-multi-qubit-gate-depth': non_transpiled_multi_qubit_gate_depth,
                'original-total-number-of-operations': non_transpiled_total_number_of_operations,
                'original-number-of-single-qubit-gates': non_transpiled_number_of_single_qubit_gates,
                'original-number-of-multi-qubit-gates': non_transpiled_number_of_multi_qubit_gates,
                'original-number-of-measurement-operations': non_transpiled_number_of_measurement_operations}

    return jsonify(response), 200


@app.route('/pytket-service/api/v1.0/transpile', methods=['POST'])
def transpile_circuit():
    """Get implementation from URL. Pass input into implementation. Generate and transpile circuit
    and return depth and width."""

    if not request.json or not 'qpu-name' in request.json or not 'provider' in request.json or not 'impl-language' in request.json:
        abort(400)

    provider = request.json["provider"]
    impl_language = request.json["impl-language"]
    qpu_name = request.json['qpu-name']
    input_params = request.json.get('input-params', "")
    input_params = parameters.ParameterDictionary(input_params)

    # setup the SDK credentials first
    setup_credentials(provider, **input_params)
    circuit = None
    short_impl_name = ""

    impl_url = request.json['impl-url'] if 'impl-url' in request.json else None
    impl_data = base64.standard_b64decode(
        request.json['impl-data'].encode()).decode() if 'impl-data' in request.json else None

    bearer_token = request.json.get("bearer-token", "")

    try:
        circuit, short_impl_name = implementation_handler.prepare_code(impl_url, impl_data, impl_language, input_params,
                                                                       bearer_token)
    except ValueError:
        abort(400)
    except Exception as e:
        app.logger.info(f"Transpile {short_impl_name} for {qpu_name}: {str(e)}")
        return jsonify({'error': str(e)}), 400

    if not circuit:
        app.logger.info(f"Transpile {short_impl_name} for {qpu_name}: Failed to create circuit.")
        return jsonify({'error': "Failed to create circuit."}), 400

    # Identify the backend given provider and qpu name
    backend = get_backend(provider, qpu_name)

    if not backend:
        app.logger.warning(f"{qpu_name} not found.")
        abort(404)

    non_transpiled_width = circuit.n_qubits
    non_transpiled_depth = get_depth_without_barrier(circuit)
    non_transpiled_multi_qubit_gate_depth = get_multi_qubit_gate_depth(circuit)
    non_transpiled_total_number_of_operations = circuit.n_gates
    non_transpiled_number_of_multi_qubit_gates = get_number_of_multi_qubit_gates(circuit)
    non_transpiled_number_of_measurement_operations = get_number_of_measurement_operations(circuit)
    non_transpiled_number_of_single_qubit_gates = non_transpiled_total_number_of_operations \
                                                  - non_transpiled_number_of_multi_qubit_gates \
                                                  - non_transpiled_number_of_measurement_operations

    precompiled_circuit = False
    while not is_tk_circuit(circuit) or not backend.valid_circuit(circuit):

        try:
            circuit = tket_transpile_circuit(circuit,
                                         impl_language=impl_language,
                                         backend=backend,
                                         short_impl_name=short_impl_name,
                                         logger=app.logger.info,
                                         precompile_circuit=precompiled_circuit)

        except UnsupportedGateException as e:

            # unsupported gate type caused circuit conversion to fail
            app.logger.warning(f"Unsupported gate ({e.gate}) in implementation {short_impl_name}.")

            # precompile the circuit and retry
            if not precompiled_circuit:
                precompiled_circuit = True
                continue
            else:
                app.logger.warning(f"Precompiling {short_impl_name} failed.")
                break

        except TooManyQubitsException:
            # Too many qubits required for the provided backend
            app.logger.info(f"Transpile {short_impl_name} for {qpu_name}: too many qubits required")
            return jsonify({'error': 'too many qubits required'}), 200

        except Exception as e:
            app.logger.warning(f"Circuit compilation unexpectedly failed for {short_impl_name}: {str(e)}")
            abort(500)

    # After compilation the circuit should be valid
    if not backend.valid_circuit(circuit):
        app.logger.warning(f"Circuit compilation unexpectedly failed for {short_impl_name}.")
        abort(500)

    response = prepare_transpile_response(circuit, provider)

    # get statistics about the compiled circuit
    width = circuit.n_qubits
    depth = get_depth_without_barrier(circuit)
    multi_qubit_gate_depth = get_multi_qubit_gate_depth(circuit)
    total_number_of_operations = circuit.n_gates
    number_of_multi_qubit_gates = get_number_of_multi_qubit_gates(circuit)
    number_of_measurement_operations = get_number_of_measurement_operations(circuit)
    number_of_single_qubit_gates = total_number_of_operations - number_of_multi_qubit_gates \
                                   - number_of_measurement_operations

    response['original-width'] = non_transpiled_width
    response['original-depth'] = non_transpiled_depth
    response['original-multi-qubit-gate-depth'] = non_transpiled_multi_qubit_gate_depth
    response['original-total-number-of-operations'] = non_transpiled_total_number_of_operations
    response['original-number-of-single-qubit-gates'] = non_transpiled_number_of_single_qubit_gates
    response['original-number-of-multi-qubit-gates'] = non_transpiled_number_of_multi_qubit_gates
    response['original-number-of-measurement-operations'] = non_transpiled_number_of_measurement_operations
    response['width'] = width
    response['depth'] = depth
    response['multi-qubit-gate-depth'] = multi_qubit_gate_depth
    response['number-of-gates'] = total_number_of_operations
    response['number-of-single-qubit-gates'] = number_of_single_qubit_gates
    response['number-of-multi-qubit-gates'] = number_of_multi_qubit_gates
    response['number-of-measurement-operations'] = number_of_measurement_operations

    app.logger.info(f"Transpiled {short_impl_name} for {qpu_name}: "
                    f"w={width}, "
                    f"d={depth}, "
                    f"mutli qubit gate depth={multi_qubit_gate_depth}"
                    f"total number of operations={total_number_of_operations}, "
                    f"number of single qubit gates={number_of_single_qubit_gates}, "
                    f"number of multi qubit gates={number_of_multi_qubit_gates}, "
                    f"number of measurement operations={number_of_measurement_operations}")
    return jsonify(response), 200


@app.route('/pytket-service/api/v1.0/execute', methods=['POST'])
def execute_circuit():
    """Put execution job in queue. Return location of the later result."""
    if not request.json or not 'qpu-name' in request.json or not 'provider' in request.json:
        abort(400)

    provider = request.json["provider"]
    qpu_name = request.json['qpu-name']

    impl_url = request.json.get('impl-url')
    bearer_token = request.json.get("bearer-token", "")
    impl_language = request.json.get("impl-language")
    impl_data = request.json.get('impl-data')
    transpiled_qasm = request.json.get('transpiled-qasm')
    transpiled_quil = request.json.get('transpiled-quil')

    input_params = request.json.get('input-params', "")
    input_params = parameters.ParameterDictionary(input_params)
    shots = request.json.get('shots', 1024)

    job = app.execute_queue.enqueue('app.tasks.execute', impl_url=impl_url, impl_data=impl_data,
                                    transpiled_qasm=transpiled_qasm,
                                    transpiled_quil=transpiled_quil, qpu_name=qpu_name,
                                    input_params=input_params, shots=shots, provider=provider,
                                    impl_language=impl_language, bearer_token=bearer_token)
    result = Result(id=job.get_id(), backend=qpu_name, shots=shots)
    db.session.add(result)
    db.session.commit()

    logging.info('Returning HTTP response to client...')
    content_location = '/pytket-service/api/v1.0/results/' + result.id
    response = jsonify({'Location': content_location})
    response.status_code = 202
    response.headers['Location'] = content_location
    response.autocorrect_location_header = True
    return response


@app.route('/pytket-service/api/v1.0/results/<result_id>', methods=['GET'])
def get_result(result_id):
    """Return result when it is available."""
    result = Result.query.get(result_id)
    if result.complete:
        result_dict = json.loads(result.result)
        return jsonify({'id': result.id, 'complete': result.complete, 'result': result_dict,
                        'backend': result.backend, 'shots': result.shots}), 200
    else:
        return jsonify({'id': result.id, 'complete': result.complete}), 200


@app.route('/pytket-service/api/v1.0/version', methods=['GET'])
def version():
    return jsonify({'version': '1.0'})
