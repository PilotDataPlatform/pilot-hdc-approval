# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from fastapi import FastAPI

from .routers import api_root
from .routers.v1.api_copy_request import api_copy_request
from .routers.v1.api_health import api_health


def api_registry(app: FastAPI):
    app.include_router(api_health.router, prefix='/v1')
    app.include_router(api_root.router, prefix='/v1')
    app.include_router(api_copy_request.router, prefix='/v1')
