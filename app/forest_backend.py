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

from pytket.extensions.pyquil import ForestBackend as BaseForestBackend
from pytket.backends import Backend
from pytket.backends.resulthandle import ResultHandle
from pytket.backends.backendinfo import BackendInfo
from pytket.extensions.pyquil.pyquil_convert import process_characterisation, get_avg_characterisation
from pytket.routing import Architecture
from pyquil import get_qc
from pyquil.api import QuantumComputer, ForestConnection
from pytket.circuit import OpType


class ForestBackend(BaseForestBackend):

    _GATE_SET = {OpType.CZ, OpType.Rx, OpType.Rz, OpType.Measure, OpType.Barrier}

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
        averaged_errors = get_avg_characterisation(self._characterisation)
        self._backend_info: BackendInfo = BackendInfo(
            name=type(self).__name__,
            device_name=qc_name,
            version="0.14.0",
            architecture=self._characterisation.get("Architecture", Architecture([])),
            gate_set=self._GATE_SET,
            all_node_gate_errors=self._characterisation.get("NodeErrors", {}),
            all_edge_gate_errors=self._characterisation.get("EdgeErrors", {}),
            averaged_node_gate_errors = averaged_errors["node_errors"],
            averaged_edge_gate_errors = averaged_errors["link_errors"]
        )

    def cancel(self, handle: ResultHandle) -> None:
        pass
