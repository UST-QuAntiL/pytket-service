# pytket-service

This service takes an implementation via an URL and compiles it using the **tket** compiler and optionally executed. 
It returns either its resulting depth & width (Transpilation Request) or its results (Execution Request) depending on the input data and selected backend.

## Setup


## After implementation changes


## Transpilation Request
Send implementation, input, QPU information, and your authentication token to the API to get depth and width of resulting circuit.

`POST /pytket-service/api/v1.0/transpile`  
```
{  
    "impl-url": "URL-OF-IMPLEMENTATION",
    "qpu-name": "NAME-OF-QPU",
    "input-params": {
        "PARAM-NAME-1": {
            "rawValue": "YOUR-VALUE-1",
            "type": "Integer"
        },
        "PARAM-NAME-2": {
            "rawValue": "YOUR-VALUE-2",
            "type": "String"
        },
        ...
        "token": {
            "rawValue": "YOUR-IBMQ-TOKEN",
            "type": "Unknown"
        },
    },
    "token": "YOUR-IBMQ-TOKEN"
}
  
```

## Execution Request
Send implementation, input, QPU information, and your authentication token to the API to execute your circuit and get the result.

`POST /pytket-service/api/v1.0/execute`  
```
{  
    "impl-url": "URL-OF-IMPLEMENTATION",
    "qpu-name": "NAME-OF-QPU",
    "input-params": {
        "PARAM-NAME-1": {
            "rawValue": "YOUR-VALUE-1",
            "type": "Integer"
        },
        "PARAM-NAME-2": {
            "rawValue": "YOUR-VALUE-2",
            "type": "String"
        },
        ...
        "token": {
            "rawValue": "YOUR-IBMQ-TOKEN",
            "type": "Unknown"
        },
    },
    "token": "YOUR-IBMQ-TOKEN"
}
```

Returns a content location for the result. Access it via `GET`.

## Haftungsausschluss

Dies ist ein Forschungsprototyp.
Die Haftung für entgangenen Gewinn, Produktionsausfall, Betriebsunterbrechung, entgangene Nutzungen, Verlust von Daten und Informationen, Finanzierungsaufwendungen sowie sonstige Vermögens- und Folgeschäden ist, außer in Fällen von grober Fahrlässigkeit, Vorsatz und Personenschäden, ausgeschlossen.

## Disclaimer of Warranty

Unless required by applicable law or agreed to in writing, Licensor provides the Work (and each Contributor provides its Contributions) on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, including, without limitation, any warranties or conditions of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR PURPOSE.
You are solely responsible for determining the appropriateness of using or redistributing the Work and assume any risks associated with Your exercise of permissions under this License.
