# pytket-service

This service takes a Qiskit, OpenQASM, or PyQuil implementation as data or via an URL and compiles it using the **tket** compiler and returns either compiled circuit properties and the transpiled OpenQASM String (Transpilation Request) or its results (Execution Request) depending on the input data and selected backend. 

## Setup
* Clone repository:
```
git clone https://github.com/UST-QuAntiL/qiskit-service.git 
git clone git@github.com:UST-QuAntiL/qiskit-service.git
```

* Start containers:
```
docker-compose pull
docker-compose up
```

Now the pytket-service is available on http://localhost:5015/.

## After implementation changes
* Update container:
```
docker build -t planqk/qiskit-service:latest .
docker push planqk/qiskit-service:latest
```

* Start containers:
```
docker-compose pull
docker-compose up
```

## Analysis of Original Circuit
 Request an analysis of the original circuit.

 `POST /pytket-service/api/v1.0/analyze-original-circuit`
 ```
 {
     "impl-url": "URL-OF-IMPLEMENTATION",
     "impl-language": "Qiskit"/"OpenQASM"/"PyQuil",
 }
 ```

## Transpilation/Compilation Request
Send implementation, input, QPU information, and your IBM Quantum Experience token to the API to get properties of the transpiled circuit and the transpiled OpenQASM circuit itself.
`POST /pytket-service/api/v1.0/transpile`  

#### Transpilation/Compilation via URL
```
{  
    "impl-url": "URL-OF-IMPLEMENTATION",
    "impl-language": "Qiskit"/"OpenQASM/PyQuil"
    "qpu-name": "NAME-OF-QPU",
    "provider": "PROVIDER, e.g. IBMQ",
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
        }
    }
}
```
#### Transpilation via File
```
{  
    "impl-data": "BASE64-ENCODED-IMPLEMENTATION",
    "impl-language": "Qiskit"/"OpenQASM/PyQuil"
    "qpu-name": "NAME-OF-QPU",
    "provider": "PROVIDER, e.g. IBMQ",
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
        }
    }
}
```

## Execution Request
Send implementation, input, QPU information, and your IBM Quantum Experience token to the API to execute your circuit and get the result.

`POST /pytket-service/api/v1.0/execute`  
#### Execution via URL
```
{  
    "impl-url": "URL-OF-IMPLEMENTATION",
    "impl-language": "Qiskit"/"OpenQASM/PyQuil",
    "qpu-name": "NAME-OF-QPU",
    "provider": "PROVIDER, e.g. IBMQ",
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
        }
    }
}
```
#### Execution via data
```
{  
    "impl-data": "BASE64-ENCODED-IMPLEMENTATION",
    "impl-language": "Qiskit"/"OpenQASM/PyQuil",
    "qpu-name": "NAME-OF-QPU",
    "provider": "PROVIDER, e.g. IBMQ",
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
        }
    }
}
```
#### Execution via transpiled OpenQASM String
```
{  
    "transpiled-qasm": "TRANSPILED-QASM-STRING",
    "qpu-name": "NAME-OF-QPU",
    "provider": "PROVIDER, e.g. IBMQ",
    "input-params": {
        "token": {
            "rawValue": "YOUR-IBMQ-TOKEN",
            "type": "Unknown"
        }
    }
}
```
Returns a content location for the result. Access it via `GET`.

## Haftungsausschluss

Dies ist ein Forschungsprototyp.
Die Haftung für entgangenen Gewinn, Produktionsausfall, Betriebsunterbrechung, entgangene Nutzungen, Verlust von Daten und Informationen, Finanzierungsaufwendungen sowie sonstige Vermögens- und Folgeschäden ist, außer in Fällen von grober Fahrlässigkeit, Vorsatz und Personenschäden, ausgeschlossen.

## Disclaimer of Warranty

Unless required by applicable law or agreed to in writing, Licensor provides the Work (and each Contributor provides its Contributions) on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, including, without limitation, any warranties or conditions of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR PURPOSE.
You are solely responsible for determining the appropriateness of using or redistributing the Work and assume any risks associated with Your exercise of permissions under this License.
