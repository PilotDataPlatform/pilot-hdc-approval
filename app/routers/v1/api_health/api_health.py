# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from aioredis import StrictRedis
from fastapi import APIRouter
from fastapi.responses import Response
from fastapi_sqlalchemy import db
from fastapi_utils import cbv

from app.config import ConfigClass
from app.logger import logger
from app.models.copy_request_sql import RequestModel
from app.resources.error_handler import APIException

router = APIRouter(tags=['Health'])


async def db_health_check():
    try:
        db.session.query(RequestModel).first()
    except Exception as e:
        error_msg = f'Could not connect to pilot_approval.approval_request table: {e}'
        logger.error(error_msg)
        raise APIException(error_msg=error_msg, status_code=503)

    return True


async def redis_health_check():
    try:
        redis = StrictRedis.from_url(ConfigClass.REDIS_URI)
        await redis.ping()
    except Exception as e:
        error_msg = f'Could not connect to redis: {e}'
        logger.error(error_msg)
        raise APIException(error_msg=error_msg, status_code=503)

    return True


@cbv.cbv(router)
class Health:
    @router.get(
        '/health/',
        summary='Health check',
    )
    async def get(self):
        logger.info('Starting api_health checks for approval service')
        await db_health_check()
        await redis_health_check()
        return Response(status_code=204)
