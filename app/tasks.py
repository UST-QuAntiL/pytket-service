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
import json

from pyquil import Program as PyQuilProgram
from pytket.extensions.pyquil import pyquil_to_tk, tk_to_pyquil
from pytket.passes import DefaultMappingPass
from pytket.predicates import ConnectivityPredicate
from pytket.qasm import circuit_to_qasm_str, circuit_from_qasm_str
from qiskit_ibm_runtime import Sampler
from rq import get_current_job

from app import implementation_handler, db, app, tket_handler
from app.generated_circuit_model import Generated_Circuit
from app.result_model import Result
from app.tket_handler import tket_transpile_circuit, UnsupportedGateException, get_backend, setup_credentials, \
    get_circuit_qasm


def convert_counts_to_json(counts):
    result = {}
    for bits, count in counts.items():
        # bitstring = np.binary_repr(bits)
        bitstring = "".join([str(b) for b in bits])
        # reverse the string to be uniform with IBM Quantum results
        result[bitstring[::-1]] = int(count)

    return json.dumps(result)


def rename_qreg_lowercase(circuit, *regs):
    """
    Renames qubit-registers to lowercase names, because uppercase letters in register names causes the execution to fail.
    :param circuit: the circuit
    :param regs: list of registers
    :return:
    """

    qasm = circuit_to_qasm_str(circuit)

    for reg in regs:
        qasm = qasm.replace(reg, reg.lower())

    return circuit_from_qasm_str(qasm)


def generate(impl_url, impl_data, impl_language, input_params, bearer_token):
    app.logger.info("Starting generate task...")
    job = get_current_job()
    short_impl_name = 'GeneratedCircuit'

    generated_circuit_code = None
    if impl_url or impl_data:
        generated_circuit_code, short_impl_name = implementation_handler.prepare_code(impl_url, impl_data,
                                                                                      impl_language, input_params,
                                                                                      bearer_token)
    else:
        generated_circuit_object = Generated_Circuit.query.get(job.get_id())
        generated_circuit_object.generated_circuit = json.dumps({'error': 'generating circuit failed'})
        generated_circuit_object.complete = True
        db.session.commit()

    if generated_circuit_code:
        generated_circuit_object = Generated_Circuit.query.get(job.get_id())
        if impl_language.lower() == 'pyquil':
            generated_circuit_object.generated_circuit = str(generated_circuit_code)
        elif impl_language.lower() == 'qiskit':
            # convert the circuit to QASM string
            generated_circuit_object.generated_circuit = generated_circuit_code.qasm()
        generated_circuit_code, generated_circuit_object.original_width, generated_circuit_object.original_depth, generated_circuit_object.original_multi_qubit_gate_depth, generated_circuit_object.original_total_number_of_operations, generated_circuit_object.original_number_of_multi_qubit_gates, generated_circuit_object.original_number_of_measurement_operations, generated_circuit_object.original_number_of_single_qubit_gates = tket_handler.tket_analyze_original_circuit(
            generated_circuit_code, impl_language=impl_language, short_impl_name=short_impl_name,
            logger=app.logger.info, precompile_circuit=False)

        generated_circuit_object.input_params = json.dumps(input_params)
        app.logger.info(f"Received input params for circuit generation: {generated_circuit_object.input_params}")
        generated_circuit_object.complete = True
        db.session.commit()


def execute(correlation_id, impl_url, impl_data, transpiled_qasm, transpiled_quil, input_params, provider, qpu_name,
            impl_language, shots, bearer_token: str = ""):
    """Create database entry for result. Get implementation code, prepare it, and execute it. Save result in db"""
    job = get_current_job()

    # setup the SDK credentials first
    setup_credentials(provider, **input_params)
    # Get the backend
    backend = get_backend(provider, qpu_name)

    if (impl_url or impl_data) and not correlation_id:
        circuit, short_impl_name = implementation_handler.prepare_code(impl_url, impl_data, impl_language, input_params,
                                                                       bearer_token)
        # Transpile the circuit for the backend
        try:
            circuit = tket_transpile_circuit(circuit, impl_language=impl_language, backend=backend,
                                             short_impl_name=short_impl_name, logger=None, precompile_circuit=False)
        except UnsupportedGateException:
            circuit = tket_transpile_circuit(circuit, impl_language=impl_language, backend=backend,
                                             short_impl_name=short_impl_name, logger=None, precompile_circuit=True)
        finally:
            if not backend.valid_circuit(circuit):
                result = Result.query.get(job.get_id())
                result.result = json.dumps({'error': 'execution failed'})
                result.complete = True
                db.session.commit()
                return
    elif transpiled_qasm:
        circuit = circuit_from_qasm_str(transpiled_qasm)

        if not backend.valid_circuit(circuit):
            result = Result.query.get(job.get_id())
            result.result = json.dumps({'error': "transpiled QASM doesn't meet QPU requirements"})
            result.complete = True
            db.session.commit()
            return
    elif transpiled_quil:
        circuit = pyquil_to_tk(PyQuilProgram(transpiled_quil))

        missed_predicates = list(filter(lambda p: not p.verify(circuit), backend.required_predicates))
        if len(missed_predicates) == 1 and isinstance(missed_predicates[0], ConnectivityPredicate):
            # Quil doesn't persist the name of the mapped QPU nodes
            # use a default mapping to restore it
            DefaultMappingPass(backend.backend_info.architecture).apply(circuit)

        if not backend.valid_circuit(circuit):
            result = Result.query.get(job.get_id())
            result.result = json.dumps({'error': "transpiled Quil doesn't meet QPU requirements"})
            result.complete = True
            db.session.commit()
            return

    # Rename registers to lower case
    register_names = set(map(lambda q: q.reg_name, circuit.qubits))
    circuit = rename_qreg_lowercase(circuit, *register_names)

    # fix bug in pytket-qiskit by monkey patching
    original_run = Sampler.run

    def fixed_run(self, **kwargs):
        kwargs.pop("dynamic", None)  # remove "dynamic" argument, as it is no longer supported

        return original_run(self, **kwargs)

    Sampler.run = fixed_run

    # Execute the circuit on the backend
    # validity was checked before
    job_handle = backend.process_circuit(circuit, n_shots=shots, valid_check=False)
    job_status = backend.circuit_status(job_handle)
    job_result = backend.get_result(job_handle)

    result = Result.query.get(job.get_id())
    counts = job_result.get_counts()
    print(counts)
    result.result = convert_counts_to_json(counts)
    # check if implementation contains post processing of execution results that has to be executed
    if correlation_id and (impl_url or impl_data):
        result.generated_circuit_id = correlation_id
        # prepare input data containing execution results and initial input params for generating the circuit
        generated_circuit = Generated_Circuit.query.get(correlation_id)
        input_params_for_post_processing = json.loads(generated_circuit.input_params)
        input_params_for_post_processing['counts'] = json.loads(result.result)

        if impl_url:
            post_p_result = implementation_handler.prepare_code_from_url(url=impl_url,
                                                                         input_params=input_params_for_post_processing,
                                                                         bearer_token=bearer_token,
                                                                         post_processing=True)
        elif impl_data:
            post_p_result = implementation_handler.prepare_post_processing_code_from_data(data=impl_data,
                                                                                          input_params=input_params_for_post_processing)
        result.post_processing_result = json.loads(post_p_result)
    result.complete = True
    db.session.commit()
