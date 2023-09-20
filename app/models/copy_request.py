# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import json
import uuid

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator

from app.resources.error_handler import APIException

from .base import APIResponse
from .base import EAPIResponseCode
from .base import PaginationRequest


class POSTRequest(BaseModel):
    entity_ids: list[str]
    destination_id: str
    source_id: str
    note: str
    submitted_by: str

    @validator('note')
    def valid_note(cls, value):
        if value == '':
            raise APIException(EAPIResponseCode.bad_request.value, 'Note is required')
        return value


class POSTRequestResponse(APIResponse):
    result: dict = Field(
        {}, example={'code': 200, 'error_msg': '', 'num_of_pages': 1, 'page': 0, 'result': 'success', 'total': 1}
    )


class GETRequest(PaginationRequest):
    status: str
    submitted_by: str = None


class GETRequestResponse(APIResponse):
    result: dict = Field(
        {}, example={'code': 200, 'error_msg': '', 'num_of_pages': 1, 'page': 0, 'result': [], 'total': 1}
    )


class GETRequestFiles(PaginationRequest):
    request_id: uuid.UUID
    parent_id: str = ''
    query: str = '{}'
    partial: str = '[]'
    order_by: str = 'uploaded_at'

    @validator('query', 'partial')
    def valid_json(cls, value):
        try:
            value = json.loads(value)
        except Exception:
            raise APIException(EAPIResponseCode.bad_request.value, 'Invalid json: {value}')
        return value


class GETRequestFilesResponse(APIResponse):
    result: dict = Field(
        {}, example={'code': 200, 'error_msg': '', 'num_of_pages': 1, 'page': 0, 'result': [], 'total': 1}
    )


class PUTRequest(BaseModel):
    request_id: uuid.UUID
    status: str
    review_notes: str = ''
    username: str

    @validator('status')
    def valid_status(cls, value):
        if value != 'complete':
            raise APIException(EAPIResponseCode.bad_request.value, 'invalid review status')
        return value


class PUTRequestFiles(BaseModel):
    request_id: uuid.UUID
    review_status: str
    session_id: str
    username: str

    @validator('review_status')
    def valid_review_status(cls, value):
        if value not in ['approved', 'denied']:
            raise APIException(EAPIResponseCode.bad_request.value, 'invalid review status')
        return value


class PATCHRequestFiles(BaseModel):
    entity_ids: list[str]
    request_id: uuid.UUID
    review_status: str
    username: str
    session_id: str

    @validator('review_status')
    def valid_review_status(cls, value):
        if value not in ['approved', 'denied']:
            raise APIException(EAPIResponseCode.bad_request.value, 'invalid review status')
        return value


class PUTRequestFilesResponse(APIResponse):
    result: dict = Field(
        {}, example={'code': 200, 'error_msg': '', 'num_of_pages': 1, 'page': 0, 'result': [], 'total': 1}
    )


class GETRequestPending(BaseModel):
    request_id: uuid.UUID


class GETPendingResponse(APIResponse):
    result: dict = Field(
        {},
        example={
            'code': 200,
            'error_msg': '',
            'num_of_pages': 1,
            'page': 0,
            'result': {
                'pending_count': 1,
                'pending_entities': ['geid'],
            },
            'total': 1,
        },
    )


class PUTCopyStatus(BaseModel):
    entities: list[str]
    copy_status: str

    @validator('copy_status')
    def valid_copy_status(cls, value):
        if value not in ['copied', 'pending']:
            raise ValueError('invalid copy status')
        return value


class PUTCopyStatusResponse(APIResponse):
    result: dict = Field(
        {}, example={'code': 200, 'error_msg': '', 'num_of_pages': 1, 'page': 0, 'result': [], 'total': 1}
    )
