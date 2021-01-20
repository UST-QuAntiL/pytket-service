import re

from pytket.qiskit import qiskit_to_tk, tk_to_qiskit
from pytket.cirq import cirq_to_tk, tk_to_cirq
from pytket.backends.ibm import IBMQBackend, AerBackend, NoIBMQAccountError
from pytket.backends.braket import BraketBackend
from pytket.circuit import Circuit as TKCircuit
from pytket.circuit import OpType

from qiskit.compiler import transpile
from qiskit import IBMQ
import qiskit.circuit.library as qiskit_gates


def get_depth_without_barrier(circuit):
    """
    Get the depth of the circuit without counting barriers.
    This is equivalent to the Qiskit style of counting.
    :param circuit:
    :return:
    """
    circuit_ops = set(map(lambda c: c.op.type, circuit.get_commands())) - {OpType.Barrier}
    return circuit.depth_by_type(circuit_ops)


def setup_credentials(sdk, **kwargs):

    if sdk == "Qiskit":
        if IBMQ.stored_account():
            IBMQ.delete_account()
        if 'token' in kwargs:
            IBMQ.save_account(token=kwargs['token'])
            IBMQ.load_account()


def get_circuit_conversion_for(sdk):
    """
    Get the circuit conversion function by name.
    :param sdk:
    :return:
    """

    if sdk.lower() == "qiskit":
        return qiskit_to_tk

    if sdk.lower() == "cirq":
        return cirq_to_tk

    if sdk.lower() == "qasm":
        return lambda x: x

    # Default if no SDK matched
    return None

def get_backend(provider, qpu):
    """
    Get the backend instance by name
    :param provider:
    :param qpu:
    :return:
    """

    if provider == "IBMQ":
        try:
            return IBMQBackend(qpu)
        except NoIBMQAccountError as e:
            return None

    if provider == "Braket":
        # TODO: error handling ???
        return BraketBackend(device= qpu)

    # Default if no provider matched
    return None

def is_tk_circuit(circuit):
    return isinstance(circuit, TKCircuit)


def pretranspile_circuit(circuit, sdk):
    """
    Pre-transpiles the circuit using the SDKs transpiler if available
    :param circuit:
    :param sdk:
    :return:
    """

    if sdk == "Qiskit":
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
    return transpile(circuits= circuit,
              basis_gates= [
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
              optimization_level= 0)


class UnsupportedGateException(Exception):
    def __init__(self, gate):
        self.gate = gate

class TooManyQubitsException(Exception):
    pass


def tket_transpile_circuit(circuit, sdk, backend, short_impl_name, logger=None, precompile_circuit=False):

    if precompile_circuit:
        if logger:
            logger(f"Precompiling {short_impl_name} using {sdk} standard compiler...")
        circuit = pretranspile_circuit(circuit, sdk)
    try:
        # Convert the given Circuit (implemented with SDK) to a standard TKet circuit
        to_tk = get_circuit_conversion_for(sdk=sdk)
        circuit = to_tk(circuit)

    except KeyError as e:
        # unsupported gate type caused circuit conversion to fail
        raise UnsupportedGateException(str(e))

    try:
        # Use tket to compile the circuit
        backend.compile_circuit(circuit, optimisation_level=0)
    except RuntimeError as e:
        if re.match(".* MaxNQubitsPredicate\\([0-9]+\\)", str(e)):
            raise TooManyQubitsException()
        else:
            raise e

    return circuit

