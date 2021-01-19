import os
import json
from qiskit.providers.models import QasmBackendConfiguration, BackendProperties
from qiskit.test.mock.fake_backend import FakeBackend
from qiskit import QuantumCircuit, transpile


class FakeOwnBackend(FakeBackend):
    def __init__(self):
        dirname = os.path.dirname(__file__)
        filename = "conf_fake_ibmq_armonk.json"
        with open(os.path.join(dirname, filename)) as f_conf:
            conf = json.load(f_conf)

        configuration = QasmBackendConfiguration.from_dict(conf)
        configuration.backend_name = 'fake_ibmq_armonk'
        super().__init__(configuration)

    def properties(self):
        """Returns a snapshot of device properties"""
        dirname = os.path.dirname(__file__)
        filename = "props_fake_ibmq_armonk.json"
        with open(os.path.join(dirname, filename)) as f_prop:
            props = json.load(f_prop)
        return BackendProperties.from_dict(props)


backend = FakeOwnBackend()
print(backend.properties().qubits)

qc = QuantumCircuit(1)
qc.h(0)
qc.measure_all()
print(qc)

transpiled_circuit = transpile(qc, backend)
print(transpiled_circuit)