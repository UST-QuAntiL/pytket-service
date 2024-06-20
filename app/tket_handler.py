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

import re
import os

import boto3
import pytket.extensions.qiskit
from braket.aws.aws_session import AwsSession
from pytket.extensions.braket import BraketBackend
from pytket.extensions.qiskit import qiskit_to_tk, IBMQBackend, set_ibmq_config, AerBackend
from pytket.extensions.pyquil import pyquil_to_tk, tk_to_pyquil
from pytket.extensions.ionq import IonQBackend, set_ionq_config
from pytket import Circuit as TKCircuit
from pytket.circuit import OpType
from pytket.qasm import circuit_to_qasm_str
from flask import abort

from qiskit.compiler import transpile
from qiskit import IBMQ
import qiskit.circuit.library as qiskit_gates
from qiskit_aer import AerSimulator

AWS_BRAKET_HOSTED_PROVIDERS = ['rigetti', 'aws']
# Get environment variables
qvm_hostname = os.environ.get('QVM_HOSTNAME', default='localhost')
qvm_port = os.environ.get('QVM_PORT', default=5016)
quilc_hostname = os.environ.get("QUILC_HOSTNAME", default="localhost")
quilc_port = os.environ.get("QUILC_PORT", default=5017)

# The AWS Session that will be used to access the AWS Braket service
aws_session = None
aws_qpu_to_region = {
    'ionq': "us-east-1",
    'aws': "us-east-1",
    'rigetti': "us-west-1"
}

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
            hub = 'ibm-q'
            group = 'open'
            project = 'main'
            set_ibmq_config(ibmq_api_token=kwargs['token'], instance=f"{hub}/{group}/{project}")
        else:
            abort(400)
    elif provider.lower() == "ionq":
        if 'token' in kwargs:
            set_ionq_config(kwargs['token'])
        else:
            abort(400)
    elif provider.lower() in AWS_BRAKET_HOSTED_PROVIDERS:
        if 'aws-access-key-id' in kwargs and 'aws-secret-access-key' in kwargs:
            boto_session = boto3.Session(
                aws_access_key_id= kwargs['aws-access-key-id'],
                aws_secret_access_key=kwargs['aws-secret-access-key'],
                region_name=kwargs.get('region', 'eu-west-2')
            )
            global aws_session
            aws_session = AwsSession(boto_session)
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
    Expects for AWS that the setup_credentials method is called before
    :param provider:
    :param qpu:
    :return:
    """

    if provider.lower() == "ibmq":
        try:
            if (qpu == 'ibmq_qasm_simulator') or (qpu == 'aer_simulator'):
                return AerBackend()
            return IBMQBackend(qpu)
        except ValueError:
            return None
    if provider.lower() == "ionq":
        try:
            qpu = qpu.replace(" ", "-")
            for backend in IonQBackend.available_devices():
                if qpu.lower() in backend.device_name.lower():
                    qpu = backend.device_name.lower()
                    break
            return IonQBackend(qpu)
        except ValueError:
            return None
    if aws_session is not None and provider.lower() == "aws":
        qpu_provider_for_aws = provider
        if "Aria" in qpu or "Harmony" in qpu:
            qpu_provider_for_aws = 'ionq'
        qpu_name_for_request = qpu.replace(" ", "-")
        backend = BraketBackend(device=qpu_name_for_request, device_type='qpu', provider=qpu_provider_for_aws,
                                region=aws_qpu_to_region[provider], aws_session=aws_session)
        return backend
    """ Disabled as migration from pyquil v2 -> v3 is non-trivial
    if provider.lower() == "rigetti":
        # Create a connection to the forest SDK
        connection = ForestConnection(
            sync_endpoint=f"http://{qvm_hostname}:{qvm_port}",
            compiler_endpoint=f"tcp://{quilc_hostname}:{quilc_port}")

        return ForestBackend(qpu, simulator=True, connection=connection)
    """
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


def tket_analyze_original_circuit(circuit, impl_language, short_impl_name, logger=None, precompile_circuit=False):
    if precompile_circuit:
        if logger:
            logger(f"Precompiling {short_impl_name} using {impl_language} standard compiler...")
        circuit = pretranspile_circuit(circuit, impl_language)
    try:
        # Convert the given Circuit (implemented with impl_language) to a standard TKet circuit
        to_tk = get_circuit_conversion_for(impl_language)
        circuit = to_tk(circuit)

        non_transpiled_width = circuit.n_qubits
        non_transpiled_depth = get_depth_without_barrier(circuit)
        non_transpiled_multi_qubit_gate_depth = get_multi_qubit_gate_depth(circuit)
        non_transpiled_total_number_of_operations = circuit.n_gates
        non_transpiled_number_of_multi_qubit_gates = get_number_of_multi_qubit_gates(circuit)
        non_transpiled_number_of_measurement_operations = get_number_of_measurement_operations(circuit)
        non_transpiled_number_of_single_qubit_gates = non_transpiled_total_number_of_operations \
                                                      - non_transpiled_number_of_multi_qubit_gates \
                                                      - non_transpiled_number_of_measurement_operations

    except KeyError as e:
        # unsupported gate type caused circuit conversion to fail
        raise UnsupportedGateException(str(e))

    return circuit, \
           non_transpiled_width, \
           non_transpiled_depth, \
           non_transpiled_multi_qubit_gate_depth, \
           non_transpiled_total_number_of_operations, \
           non_transpiled_number_of_multi_qubit_gates, \
           non_transpiled_number_of_measurement_operations, \
           non_transpiled_number_of_single_qubit_gates

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
        # backend.compile_circuit(circuit, optimisation_level=2) -> Does not exist anymore for pytket backend
        compiled_circuit = backend.get_compiled_circuit(circuit, optimisation_level=2)
    except RuntimeError as e:
        if re.match(".* MaxNQubitsPredicate\\([0-9]+\\)", str(e)):
            raise TooManyQubitsException()
        else:
            raise e

    return compiled_circuit

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


def get_number_of_measurement_operations(circuit):
    return circuit.n_gates_of_type(OpType.Measure)
