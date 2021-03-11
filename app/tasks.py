from app import implementation_handler, db
from rq import get_current_job
from app.tket_handler import tket_transpile_circuit, UnsupportedGateException, get_backend, setup_credentials
from app.result_model import Result
import json
from pytket.qasm import circuit_to_qasm_str, circuit_from_qasm_str
from pyquil import Program as PyQuilProgram
from pytket.extensions.pyquil import pyquil_to_tk
from pytket.predicates import ConnectivityPredicate
from pytket.passes import DefaultMappingPass

def convert_counts_to_json(counts):

    result = {}
    for bits, count in counts.items():
        #bitstring = np.binary_repr(bits)
        bitstring = "".join([str(b) for b in bits])
        result[bitstring] = int(count)

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


def execute(impl_url, impl_data, transpiled_qasm, transpiled_quil, input_params, provider, qpu_name, impl_language, shots):
    """Create database entry for result. Get implementation code, prepare it, and execute it. Save result in db"""
    job = get_current_job()

    # setup the SDK credentials first
    setup_credentials(provider, **input_params)
    # Get the backend
    backend = get_backend(provider, qpu_name)

    if not transpiled_qasm and not transpiled_quil:

        circuit, short_impl_name = implementation_handler.prepare_code(impl_url, impl_data, impl_language, input_params)

        # Transpile the circuit for the backend
        try:
            circuit = tket_transpile_circuit(circuit,
                                             impl_language=impl_language,
                                             backend=backend,
                                             short_impl_name=short_impl_name,
                                             logger=None, precompile_circuit=False)
        except UnsupportedGateException as e:
            circuit = tket_transpile_circuit(circuit,
                                             impl_language=impl_language,
                                             backend=backend,
                                             short_impl_name=short_impl_name,
                                             logger=None, precompile_circuit=True)
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
            result.result = json.dumps({'error': "transpiled QASM doesn't meet QPU requirements" })
            result.complete = True
            db.session.commit()
            return
    elif transpiled_quil:
        circuit = pyquil_to_tk(PyQuilProgram(transpiled_quil))

        missed_predicates = list(filter(lambda p : not p.verify(circuit), backend.required_predicates))
        if len(missed_predicates) == 1 and isinstance(missed_predicates[0], ConnectivityPredicate):

            # Quil doesn't persist the name of the mapped QPU nodes
            # use a default mapping to restore it
            DefaultMappingPass(backend.device).apply(circuit)

        if not backend.valid_circuit(circuit):
            result = Result.query.get(job.get_id())
            result.result = json.dumps({'error': "transpiled Quil doesn't meet QPU requirements"})
            result.complete = True
            db.session.commit()
            return


    # Rename registers to lower case
    register_names = set(map(lambda q: q.reg_name, circuit.qubits))
    circuit = rename_qreg_lowercase(circuit, *register_names)

    # Execute the circuit on the backend
    # validity was checked before
    job_handle = backend.process_circuit(circuit, n_shots=shots, valid_check=False)
    job_status = backend.circuit_status(job_handle)
    job_result = backend.get_result(job_handle)

    result = Result.query.get(job.get_id())
    counts = job_result.get_counts()
    print(counts)
    result.result = convert_counts_to_json(counts)
    result.complete = True
    db.session.commit()

