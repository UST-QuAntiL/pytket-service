import re
import os

from pytket.extensions.qiskit import qiskit_to_tk
from pytket.extensions.pyquil import pyquil_to_tk, tk_to_pyquil
from pytket.extensions.qiskit import IBMQBackend, NoIBMQAccountError
from app.forest_backend import ForestBackend
from pyquil.api import ForestConnection
from pytket import Circuit as TKCircuit
from pytket.circuit import OpType
from pytket.qasm import circuit_to_qasm_str
from flask import abort

from qiskit.compiler import transpile
from qiskit import IBMQ
import qiskit.circuit.library as qiskit_gates

# Get environment variables
qvm_hostname = os.environ.get('QVM_HOSTNAME', default='localhost')
qvm_port = os.environ.get('QVM_PORT', default=5016)
quilc_hostname = os.environ.get("QUILC_HOSTNAME", default="localhost")
quilc_port = os.environ.get("QUILC_PORT", default=5017)


def prepare_transpile_response(circuit, provider):
    if provider.lower() in ['rigetti']:
        transpiled_quil = tk_to_pyquil(circuit)
        return {'transpiled-quil': str(transpiled_quil), 'language': "Quil"}
    else:
        # convert the circuit to QASM string
        transpiled_qasm = get_circuit_qasm(circuit)
        return {'transpiled-qasm': transpiled_qasm, 'language': "OpenQASM"}


def get_depth_without_barrier(circuit):
    """
    Get the depth of the circuit without counting barriers.
    This is equivalent to the Qiskit style of counting.
    :param circuit:
    :return:
    """
    circuit_ops = set(map(lambda c: c.op.type, circuit.get_commands())) - {OpType.Barrier}
    return circuit.depth_by_type(circuit_ops)


def setup_credentials(provider, **kwargs):
    if provider.lower() == "ibmq":
        if 'token' in kwargs:
            IBMQ.save_account(token=kwargs['token'], overwrite=True)
            IBMQ.load_account()
        else:
            abort(400)


def get_circuit_conversion_for(impl_language):
    """
    Get the circuit conversion function by name.
    :param impl_language:
    :return:
    """

    if not impl_language:
        return lambda x: x

    assert isinstance(impl_language, str)

    if impl_language.lower() == "qiskit":
        return qiskit_to_tk

    if impl_language.lower() in ["pyquil", "quil"]:
        return pyquil_to_tk

    if impl_language.lower() == "openqasm":
        return lambda x: x

    # Default if no impl_language matched
    return None


def get_backend(provider, qpu):
    """
    Get the backend instance by name
    :param provider:
    :param qpu:
    :return:
    """

    if provider.lower() == "ibmq":
        try:
            return IBMQBackend(qpu)
        except NoIBMQAccountError:
            return None

    if provider.lower() == "rigetti":
        # Create a connection to the forest SDK
        connection = ForestConnection(
            sync_endpoint=f"http://{qvm_hostname}:{qvm_port}",
            compiler_endpoint=f"tcp://{quilc_hostname}:{quilc_port}")

        return ForestBackend(qpu, simulator=True, connection=connection)

    # Default if no provider matched
    return None


def is_tk_circuit(circuit):
    return isinstance(circuit, TKCircuit)


def pretranspile_circuit(circuit, impl_language):
    """
    Pre-transpiles the circuit using the SDKs transpiler if available
    :param circuit:
    :param impl_language:
    :return:
    """

    if impl_language.lower() == "qiskit":
        return pretranspile_qiskit_circuit(circuit)
    else:
        return circuit


def pretranspile_qiskit_circuit(circuit):
    """
    Pre-transpiles the qiskit circuit to a set of gates that are supported by the Tket compiler.
    This is only for compatibility reasons.

    :param circuit:
    :return:
    """

    # Transpile the circuit without any optimizations (i.e. optimization_level=0)
    return transpile(circuits=circuit,
                     basis_gates=[
                         qiskit_gates.IGate().name,
                         qiskit_gates.XGate().name,
                         qiskit_gates.YGate().name,
                         qiskit_gates.ZGate().name,
                         qiskit_gates.SGate().name,
                         qiskit_gates.SdgGate().name,
                         qiskit_gates.TGate().name,
                         qiskit_gates.TdgGate().name,
                         qiskit_gates.HGate().name,
                         'rx',
                         'ry',
                         'rz',
                         'u1',
                         'u2',
                         'u3',
                         qiskit_gates.CXGate().name,
                         qiskit_gates.CYGate().name,
                         qiskit_gates.CZGate().name,
                         qiskit_gates.CHGate().name,
                         qiskit_gates.SwapGate().name,
                         qiskit_gates.CCXGate().name,
                         qiskit_gates.CSwapGate().name,
                         'crz',
                         'cu1',
                         'cu3'
                     ],
                     optimization_level=0)


class UnsupportedGateException(Exception):
    def __init__(self, gate):
        self.gate = gate


class TooManyQubitsException(Exception):
    pass


def tket_transpile_circuit(circuit, impl_language, backend, short_impl_name, logger=None, precompile_circuit=False):
    if precompile_circuit:
        if logger:
            logger(f"Precompiling {short_impl_name} using {impl_language} standard compiler...")
        circuit = pretranspile_circuit(circuit, impl_language)
    try:
        # Convert the given Circuit (implemented with impl_language) to a standard TKet circuit
        to_tk = get_circuit_conversion_for(impl_language)
        circuit = to_tk(circuit)

    except KeyError as e:
        # unsupported gate type caused circuit conversion to fail
        raise UnsupportedGateException(str(e))

    try:
        # Use tket to compile the circuit
        backend.compile_circuit(circuit, optimisation_level=2)
    except RuntimeError as e:
        if re.match(".* MaxNQubitsPredicate\\([0-9]+\\)", str(e)):
            raise TooManyQubitsException()
        else:
            raise e

    return circuit


def get_circuit_qasm(circuit):
    return circuit_to_qasm_str(circuit)


def get_number_of_multi_qubit_gates(circuit):
    number_of_multi_qubit_gates = circuit.n_gates_of_type(OpType.CX) + \
                                  circuit.n_gates_of_type(OpType.CY) + \
                                  circuit.n_gates_of_type(OpType.CZ) + \
                                  circuit.n_gates_of_type(OpType.CH) + \
                                  circuit.n_gates_of_type(OpType.CV) + \
                                  circuit.n_gates_of_type(OpType.CVdg) + \
                                  circuit.n_gates_of_type(OpType.CRx) + \
                                  circuit.n_gates_of_type(OpType.CRy) + \
                                  circuit.n_gates_of_type(OpType.CRz) + \
                                  circuit.n_gates_of_type(OpType.CU1) + \
                                  circuit.n_gates_of_type(OpType.CU3) + \
                                  circuit.n_gates_of_type(OpType.CCX) + \
                                  circuit.n_gates_of_type(OpType.ECR) + \
                                  circuit.n_gates_of_type(OpType.SWAP) + \
                                  circuit.n_gates_of_type(OpType.CSWAP) + \
                                  circuit.n_gates_of_type(OpType.BRIDGE) + \
                                  circuit.n_gates_of_type(OpType.Unitary2qBox) + \
                                  circuit.n_gates_of_type(OpType.Unitary3qBox) + \
                                  circuit.n_gates_of_type(OpType.ExpBox) + \
                                  circuit.n_gates_of_type(OpType.QControlBox) + \
                                  circuit.n_gates_of_type(OpType.ISWAP) + \
                                  circuit.n_gates_of_type(OpType.PhasedISWAP) + \
                                  circuit.n_gates_of_type(OpType.XXPhase) + \
                                  circuit.n_gates_of_type(OpType.YYPhase) + \
                                  circuit.n_gates_of_type(OpType.CnRy) + \
                                  circuit.n_gates_of_type(OpType.CnX) + \
                                  circuit.n_gates_of_type(OpType.ZZMax) + \
                                  circuit.n_gates_of_type(OpType.ESWAP) + \
                                  circuit.n_gates_of_type(OpType.FSim) + \
                                  circuit.n_gates_of_type(OpType.ISWAPMax)

    return number_of_multi_qubit_gates


def get_multi_qubit_gate_depth(circuit):
    multi_qubit_gate_depth = circuit.depth_by_type({OpType.CX,
                                                    OpType.CY,
                                                    OpType.CZ,
                                                    OpType.CH,
                                                    OpType.CV,
                                                    OpType.CVdg,
                                                    OpType.CRx,
                                                    OpType.CRy,
                                                    OpType.CRz,
                                                    OpType.CU1,
                                                    OpType.CU3,
                                                    OpType.CCX,
                                                    OpType.ECR,
                                                    OpType.SWAP,
                                                    OpType.CSWAP,
                                                    OpType.BRIDGE,
                                                    OpType.Unitary2qBox,
                                                    OpType.Unitary3qBox,
                                                    OpType.ExpBox,
                                                    OpType.QControlBox,
                                                    OpType.ISWAP,
                                                    OpType.PhasedISWAP,
                                                    OpType.XXPhase,
                                                    OpType.YYPhase,
                                                    OpType.CnRy,
                                                    OpType.CnX,
                                                    OpType.ZZMax,
                                                    OpType.ESWAP,
                                                    OpType.FSim,
                                                    OpType.ISWAPMax})
    return multi_qubit_gate_depth
