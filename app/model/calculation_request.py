# ******************************************************************************
#  Copyright (c) 2024 University of Stuttgart
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

import marshmallow as ma


class AnalysisOriginalCircuitRequest:
    def __init__(self, impl_url, impl_language, input_params):
        self.impl_url = impl_url
        self.impl_language = impl_language
        self.input_params = input_params


class AnalysisOriginalCircuitRequestSchema(ma.Schema):
    impl_url = ma.fields.String()
    impl_language = ma.fields.String()
    input_params = ma.fields.List(ma.fields.String())
