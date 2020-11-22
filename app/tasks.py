# ******************************************************************************
#  Copyright (c) 2020 University of Stuttgart
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

from app import implementation_handler, db
from qiskit import transpile
from qiskit.transpiler.exceptions import TranspilerError
from rq import get_current_job
from app.tket_handler import tket_transpile_circuit, UnsupportedGateException, get_backend
from app.result_model import Result
import logging
import json
import re
import numpy as np
from pytket.circuit import Qubit

def convert_counts_to_json(counts):

    result = {}
    for bits, count in counts.items():
        #bitstring = np.binary_repr(bits)
        bitstring = "".join([str(b) for b in bits])
        result[bitstring] = int(count)

    return json.dumps(result)




def execute(impl_url, input_params, provider, qpu_name, sdk, shots):
    """Create database entry for result. Get implementation code, prepare it, and execute it. Save result in db"""
    job = get_current_job()
    short_impl_name = re.match(".*/(?P<file>.*\\.py)", impl_url).group('file')

    # Download and execute the implementation
    circuit = implementation_handler.prepare_code_from_url(impl_url, input_params)

    # Get the backend
    backend = get_backend(provider, qpu_name)

    # Transpile the circuit for the backend
    try:
        circuit = tket_transpile_circuit(circuit,
                                         sdk=sdk,
                                         backend=backend,
                                         short_impl_name=short_impl_name,
                                         logger=None, precompile_circuit=False)
    except UnsupportedGateException as e:
        circuit = tket_transpile_circuit(circuit,
                                         sdk=sdk,
                                         backend=backend,
                                         short_impl_name=short_impl_name,
                                         logger=None, precompile_circuit=True)
    finally:
        if not backend.valid_circuit(circuit):
            #TODO: store in the result database
            result = Result.query.get(job.get_id())
            result.result = json.dumps({'error': 'execution failed'})
            result.complete = True
            db.session.commit()
    """
    # Try to simplify the circuit
    if not circuit.is_simple:

        transformation = {}

        for q in circuit.qubits:
            print(q)
            new_q = Qubit(name="q", index=q.index)
            transformation[q] = new_q

        circuit.rename_units(transformation)
    """
    print("Stats:")
    print(circuit.is_simple)
    print(circuit.qubits)
    print(circuit.get_commands())

    # Execute the circuit on the backend
    job_handle = backend.process_circuit(circuit, n_shots=shots)
    job_status = backend.circuit_status(job_handle)
    job_result = backend.get_result(job_handle)

    result = Result.query.get(job.get_id())
    counts = job_result.get_counts()
    print(counts)
    result.result = convert_counts_to_json(counts)
    result.complete = True
    db.session.commit()

