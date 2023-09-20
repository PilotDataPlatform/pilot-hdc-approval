# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_sqlalchemy import DBSessionMiddleware

from app.resources.error_handler import APIException

from .api_registry import api_registry
from .config import ConfigClass


def create_app():
    """create app function."""
    app = FastAPI(
        title='Service Approval', description='Service Approval', docs_url='/v1/api-doc', version=ConfigClass.version
    )

    app.add_middleware(DBSessionMiddleware, db_url=ConfigClass.DB_URI)
    app.add_middleware(
        CORSMiddleware,
        allow_origins='*',
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    api_registry(app)

    @app.exception_handler(APIException)
    async def http_exception_handler(request: Request, exc: APIException):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.content,
        )

    return app
