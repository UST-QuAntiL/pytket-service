# pytket-service

This service takes a Qiskit, OpenQASM, or PyQuil implementation as data or via an URL and compiles it using the **tket** compiler and returns either compiled circuit properties and the transpiled OpenQASM String (Transpilation Request) or its results (Execution Request) depending on the input data and selected backend. 

## Setup
* Clone repository:
```
git clone https://github.com/UST-QuAntiL/pytket-service.git 
git clone git@github.com:UST-QuAntiL/pytket-service.git
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
docker build -t planqk/pytket-service:latest .
docker push planqk/pytket-service:latest
```

* Start containers:
```
docker-compose pull
docker-compose up
```

## API Documentation
The pytket-service provides a Swagger UI, specifying the request schemas and showcasing exemplary requests for all API endpoints.
* http://localhost:5013/api/swagger-ui

The OpenAPI specifications are also statically available:
[OpenAPI JSON](./docs/openapi.json)  
[OpenAPI YAML](./docs/openapi.yaml)

## Haftungsausschluss

Dies ist ein Forschungsprototyp.
Die Haftung für entgangenen Gewinn, Produktionsausfall, Betriebsunterbrechung, entgangene Nutzungen, Verlust von Daten und Informationen, Finanzierungsaufwendungen sowie sonstige Vermögens- und Folgeschäden ist, außer in Fällen von grober Fahrlässigkeit, Vorsatz und Personenschäden, ausgeschlossen.

## Disclaimer of Warranty

Unless required by applicable law or agreed to in writing, Licensor provides the Work (and each Contributor provides its Contributions) on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, including, without limitation, any warranties or conditions of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR PURPOSE.
You are solely responsible for determining the appropriateness of using or redistributing the Work and assume any risks associated with Your exercise of permissions under this License.
