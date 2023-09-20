# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import httpx

from app.config import ConfigClass
from app.models.base import EAPIResponseCode
from app.resources.error_handler import APIException


def get_node_by_id(entity_id: str) -> dict:
    response = httpx.get(ConfigClass.META_SERVICE + f'item/{entity_id}/')
    if response.status_code != 200:
        error_msg = f'Error calling Meta service get_node_by_id: {response.json()}'
        raise APIException(error_msg=error_msg, status_code=EAPIResponseCode.internal_error.value)
    if not response.json()['result']:
        error_msg = 'Folder not found'
        raise APIException(error_msg=error_msg, status_code=EAPIResponseCode.not_found.value)
    return response.json()['result']


async def bulk_get_by_ids(ids: list[str]) -> list[dict]:
    query_data = {'ids': ids}
    async with httpx.AsyncClient() as client:
        response = await client.get(ConfigClass.META_SERVICE + 'items/batch/', params=query_data)
    if response.status_code != 200:
        error_msg = f'Error calling Meta service bulk_get_by_ids: {response.json()}'
        raise APIException(error_msg=error_msg, status_code=EAPIResponseCode.internal_error.value)
    return response.json()['result']


def get_files_recursive(entity: dict, headers: dict) -> list:
    parent_path = entity['parent_path']
    name = entity['name']
    query_data = {
        'container_code': entity['container_code'],
        'zone': entity['zone'],
        'recursive': True,
        'parent_path': f'{parent_path}/{name}',
    }
    response = httpx.get(ConfigClass.META_SERVICE + 'items/search/', params=query_data, headers=headers)
    if response.status_code != 200:
        error_msg = f'Error calling Meta service get_files_recursive: {response.json()}'
        raise APIException(error_msg=error_msg, status_code=EAPIResponseCode.internal_error.value)
    return response.json()['result']
