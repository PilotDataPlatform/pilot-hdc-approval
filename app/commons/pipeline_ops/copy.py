# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import httpx

from app.config import ConfigClass
from app.logger import logger
from app.models.base import EAPIResponseCode
from app.resources.error_handler import APIException


async def trigger_copy_pipeline(
    request_id: str,
    project_code: str,
    source_id: str,
    destination_id: str,
    entity_ids: list[str],
    username: str,
    session_id: str,
    auth: dict,
    all_entities: set,
) -> dict:

    copy_data = {
        'payload': {
            'targets': [{'id': str(i)} for i in entity_ids],
            'destination': str(destination_id),
            'source': str(source_id),
            'request_info': {request_id: list(all_entities)},
        },
        'operator': username,
        'operation': 'copy',
        'project_code': project_code,
        'session_id': session_id,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(ConfigClass.DATA_UTILITY_SERVICE + 'files/actions/', json=copy_data, headers=auth)
    if response.status_code >= 300:
        error_msg = f'Failed to start copy pipeline: {response.content}'
        logger.error(error_msg)
        raise APIException(error_msg=error_msg, status_code=EAPIResponseCode.internal_error.value)
    return response.json()['operation_info']
