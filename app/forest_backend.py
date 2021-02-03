
from pytket.backends.forest import ForestBackend as BaseForestBackend
from pytket.backends import Backend
from pytket.backends.resulthandle import ResultHandle
from pytket.device import Device
from pytket.pyquil import process_characterisation
from pytket.routing import Architecture
from pyquil import get_qc
from pyquil.api import QuantumComputer, ForestConnection


class ForestBackend(BaseForestBackend):

    def __init__(self, qc_name: str, simulator: bool = True, connection: ForestConnection = None):
        """Backend for running circuits on a Rigetti QCS device or simulating with the QVM.

        :param qc_name: The name of the particular QuantumComputer to use. See the pyQuil docs for more details.
        :type qc_name: str
        :param simulator: Simulate the device with the QVM (True), or run on the QCS (False). Defaults to True.
        :type simulator: bool, optional
        :param connection: Customized connection to the rigetti backend
        :type
        """

        # skip the constructor of BaseForestBackend
        super(Backend, self).__init__()

        self._cache = {}

        self._qc: QuantumComputer = get_qc(qc_name, as_qvm=simulator, connection=connection)
        self._characterisation: dict = process_characterisation(self._qc)
        self._device: Device = Device(
            self._characterisation.get("NodeErrors", {}),
            self._characterisation.get("EdgeErrors", {}),
            self._characterisation.get("Architecture", Architecture([])),
        )

    def cancel(self, handle: ResultHandle) -> None:
        pass