# Approval Service

[![Run Tests](https://github.com/PilotDataPlatform/approval/actions/workflows/run-tests.yml/badge.svg?branch=develop)](https://github.com/PilotDataPlatform/approval/actions/workflows/run-tests.yml)
[![Python](https://img.shields.io/badge/python-3.10-brightgreen.svg)](https://www.python.org/)

## About

Logic for request and approval of files to be copied to core.

## Build With
- Python
- FastAPI
- Postgres

##  Running the service

Configure the setting either in docker-compose or .env

Start API with docker-compose
```
docker-compose up
```

### URLs
Port can be configured in with environment variable `PORT`
- API: http://localhost:8000
- API documentation: http://localhost:8000/v1/api-doc

## Acknowledgements
The development of the HealthDataCloud open source software was supported by the EBRAINS research infrastructure, funded from the European Union's Horizon 2020 Framework Programme for Research and Innovation under the Specific Grant Agreement No. 945539 (Human Brain Project SGA3) and H2020 Research and Innovation Action Grant Interactive Computing E-Infrastructure for the Human Brain Project ICEI 800858.
