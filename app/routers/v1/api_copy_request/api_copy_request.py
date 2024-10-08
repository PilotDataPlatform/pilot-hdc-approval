# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import math
from datetime import datetime

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi_sqlalchemy import db
from fastapi_utils import cbv

from app.commons.meta_services import bulk_get_by_ids
from app.commons.meta_services import get_files_recursive
from app.commons.meta_services import get_node_by_id
from app.commons.meta_services.models import MetadataItemStatus
from app.commons.notification_service.client import Notification
from app.commons.notification_service.client import NotificationServiceClient
from app.commons.notification_service.models import CopyRequestAction
from app.commons.pipeline_ops.copy import trigger_copy_pipeline
from app.commons.psql_services import create_entity_from_node
from app.commons.psql_services import get_all_sub_files
from app.commons.psql_services import get_all_sub_folder_nodes
from app.commons.psql_services import get_files_until_top_parent
from app.commons.psql_services import update_files_sql
from app.config import ConfigClass
from app.logger import logger
from app.models.base import APIResponse
from app.models.base import EAPIResponseCode
from app.models.copy_request import GETPendingResponse
from app.models.copy_request import GETRequest
from app.models.copy_request import GETRequestFiles
from app.models.copy_request import GETRequestFilesResponse
from app.models.copy_request import GETRequestPending
from app.models.copy_request import GETRequestResponse
from app.models.copy_request import PATCHRequestFiles
from app.models.copy_request import POSTRequest
from app.models.copy_request import POSTRequestResponse
from app.models.copy_request import PUTCopyStatus
from app.models.copy_request import PUTCopyStatusResponse
from app.models.copy_request import PUTRequest
from app.models.copy_request import PUTRequestFiles
from app.models.copy_request import PUTRequestFilesResponse
from app.models.copy_request_sql import EntityModel
from app.models.copy_request_sql import RequestModel

from .request_notify import notify_project_admins
from .request_notify import notify_user

router = APIRouter()
_API_TAG = 'CopyRequest'
_API_NAMESPACE = 'copy_request'


@cbv.cbv(router)
class APICopyRequest:
    @router.post(
        '/request/copy/{project_code}',
        tags=[_API_TAG],
        response_model=POSTRequestResponse,
        summary='Create a copy request',
    )
    async def create_request(self, request: Request, project_code: str, data: POSTRequest):
        logger.info('Create Request called')
        api_response = APIResponse()

        dest_folder_node = get_node_by_id(data.destination_id)
        source_folder_node = get_node_by_id(data.source_id)
        if dest_folder_node['parent_path']:
            dest_path = dest_folder_node['parent_path'] + '/' + dest_folder_node['name']
        else:
            dest_path = dest_folder_node['name']
        if source_folder_node['parent_path']:
            source_path = source_folder_node['parent_path'] + '/' + source_folder_node['name']
        else:
            source_path = source_folder_node['name']
        request_data = {
            'status': 'pending',
            'submitted_by': data.submitted_by,
            'destination_id': data.destination_id,
            'source_id': data.source_id,
            'note': data.note,
            'project_code': project_code,
            'destination_path': dest_path,
            'source_path': source_path,
        }
        request_obj = RequestModel(**request_data)
        db.session.add(request_obj)
        db.session.commit()
        db.session.refresh(request_obj)

        all_files = []
        entities = await bulk_get_by_ids(data.entity_ids)
        for entity in entities:
            entity['parent'] = None
            all_files.append(entity)
            if entity['type'] == 'folder':
                auth = {
                    'Authorization': request.headers.get('Authorization', ''),
                }
                all_files = all_files + get_files_recursive(entity, auth)

        for entity in all_files:
            create_entity_from_node(request_obj.id, entity)

        submitted_at = request_obj.submitted_at.strftime('%Y-%m-%d %H:%M:%S')
        await notify_project_admins(data.submitted_by, project_code, submitted_at)
        api_response.result = request_obj.to_dict()
        return api_response.json_response()

    @router.get(
        '/request/copy/{project_code}',
        tags=[_API_TAG],
        response_model=GETRequestResponse,
        summary='Create a copy request',
    )
    def list_requests(self, project_code: str, params: GETRequest = Depends(GETRequest)):
        logger.info('List Requests called')
        api_response = APIResponse()
        results = db.session.query(RequestModel).filter_by(
            status=params.status,
            project_code=project_code,
        )
        if params.submitted_by:
            results = results.filter_by(submitted_by=params.submitted_by)
        results = results.order_by(RequestModel.submitted_at.desc()).limit(params.page_size)
        results = results.offset(params.page * params.page_size)

        if params.submitted_by:
            total = (
                db.session.query(RequestModel)
                .filter_by(status=params.status, project_code=project_code, submitted_by=params.submitted_by)
                .count()
            )
        else:
            total = (
                db.session.query(RequestModel)
                .filter_by(
                    status=params.status,
                    project_code=project_code,
                )
                .count()
            )
        api_response.result = [i.to_dict() for i in results]
        api_response.total = total
        api_response.page = params.page
        api_response.num_of_pages = math.ceil(total / params.page_size)
        return api_response.json_response()

    @router.get(
        '/request/copy/{project_code}/files',
        tags=[_API_TAG],
        response_model=GETRequestFilesResponse,
        summary='List request files',
    )
    def list_request_files(self, project_code: str, params: GETRequestFiles = Depends(GETRequestFiles)):
        logger.info('List request files called')
        api_response = APIResponse()
        query_params = {'request_id': params.request_id}
        if params.parent_id:
            query_params['parent_id'] = params.parent_id
        else:
            query_params['parent_id'] = None

        sql_query = db.session.query(EntityModel)
        for key, value in params.query.items():
            if key in params.partial:
                sql_query = sql_query.filter(getattr(EntityModel, key).contains(value))
            else:
                query_params[key] = value

        if params.order_type == 'desc':
            order_by = getattr(EntityModel, params.order_by).desc()
        else:
            order_by = getattr(EntityModel, params.order_by).asc()
        sql_query = sql_query.filter_by(**query_params).order_by(EntityModel.entity_type.desc(), order_by)

        results = sql_query.limit(params.page_size).offset(params.page * params.page_size)
        routing = []
        if params.parent_id:
            entity_id = params.parent_id
            while entity_id:
                file = (
                    db.session.query(EntityModel).filter_by(request_id=params.request_id, entity_id=entity_id).first()
                )
                if file:
                    routing.append(file.to_dict())
                    entity_id = file.parent_id
                else:
                    entity_id = None

        total = db.session.query(EntityModel).filter_by(**query_params).count()
        api_response.result = {'data': [i.to_dict() for i in results], 'routing': routing}
        api_response.total = total
        api_response.page = params.page
        api_response.num_of_pages = math.ceil(total / params.page_size)
        return api_response.json_response()

    @router.put(
        '/request/copy/{project_code}/files',
        tags=[_API_TAG],
        response_model=PUTRequestFilesResponse,
        summary='Approve all files and trigger copy pipeline',
    )
    async def review_all_files(self, project_code: str, data: PUTRequestFiles, request: Request):
        logger.info('Review all files called')
        api_response = APIResponse()
        review_status = data.review_status

        approved = db.session.query(EntityModel).filter_by(request_id=data.request_id, review_status='approved')
        denied = db.session.query(EntityModel).filter_by(request_id=data.request_id, review_status='denied')
        skipped_data = {'approved': approved.count(), 'denied': denied.count()}

        entities = db.session.query(EntityModel).filter_by(request_id=data.request_id, review_status='pending')
        file_ids = [i.entity_id for i in entities]
        file_folder_ids = get_files_until_top_parent(data.request_id, file_ids)
        review_data = {
            'review_status': review_status,
            'reviewed_by': data.username,
            'reviewed_at': datetime.utcnow(),
        }
        result = update_files_sql(data.request_id, review_data, file_ids)

        top_level_entities = db.session.query(EntityModel).filter_by(request_id=data.request_id, parent_id=None)
        top_level_ids = [str(i.entity_id) for i in top_level_entities]
        request_obj: RequestModel = db.session.query(RequestModel).get(data.request_id)
        if len(file_ids) != 0:
            notification = Notification(
                request_obj.submitted_by,
                top_level_ids,
                data.username,
                request_obj.source_id,
                request_obj.destination_id,
                project_code,
                CopyRequestAction.APPROVAL if review_status == 'approved' else CopyRequestAction.DENIAL,
                data.request_id,
            )
            notification_client = NotificationServiceClient(ConfigClass.NOTIFICATION_SERVICE)
            notification_object = await notification.to_copy_request_notification()
            await notification_client.send_notification(notification_object)

        if review_status == 'approved' and len(file_ids) != 0:
            if top_level_ids:
                logger.info(f'Triggering pipeline for {top_level_ids}')
                auth = {
                    'Authorization': request.headers.get('Authorization').replace('Bearer ', ''),
                    'Refresh-Token': request.headers.get('Refresh-Token'),
                }
                copy_result = await trigger_copy_pipeline(
                    str(request_obj.id),
                    request_obj.project_code,
                    request_obj.source_id,
                    request_obj.destination_id,
                    top_level_ids,
                    data.username,
                    data.session_id,
                    auth,
                    file_folder_ids,
                )
                logger.info(f'Pipeline trigger for {len(copy_result)} files')

        skipped_data['updated'] = result.count()
        api_response.result = skipped_data
        return api_response.json_response()

    @router.patch(
        '/request/copy/{project_code}/files',
        tags=[_API_TAG],
        response_model=PUTRequestFilesResponse,
        summary='Approve files and trigger copy pipeline',
    )
    async def review_files(self, project_code: str, data: PATCHRequestFiles, request: Request):
        logger.info('Review files called')
        api_response = APIResponse()
        review_status = data.review_status

        approved = get_all_sub_folder_nodes(data.request_id, data.entity_ids, 'approved')
        denied = get_all_sub_folder_nodes(data.request_id, data.entity_ids, 'denied')
        skipped_data = {'approved': len(approved), 'denied': len(denied)}
        file_ids = get_all_sub_files(data.request_id, data.entity_ids)
        file_folder_ids = get_files_until_top_parent(data.request_id, file_ids)
        review_data = {
            'review_status': review_status,
            'reviewed_by': data.username,
            'reviewed_at': datetime.utcnow(),
        }
        result = update_files_sql(data.request_id, review_data, file_ids)

        request_obj: RequestModel = db.session.query(RequestModel).get(data.request_id)
        if len(file_ids) != 0:
            notification = Notification(
                request_obj.submitted_by,
                data.entity_ids,
                data.username,
                request_obj.source_id,
                request_obj.destination_id,
                project_code,
                CopyRequestAction.APPROVAL if review_status == 'approved' else CopyRequestAction.DENIAL,
                data.request_id,
            )
            notification_client = NotificationServiceClient(ConfigClass.NOTIFICATION_SERVICE)
            notification_object = await notification.to_copy_request_notification()
            await notification_client.send_notification(notification_object)

        if review_status == 'approved' and len(file_ids) != 0:
            if data.entity_ids:
                logger.info(f'Triggering pipeline for {data.entity_ids}')
                auth = {
                    'Authorization': request.headers.get('Authorization').replace('Bearer ', ''),
                }
                copy_result = await trigger_copy_pipeline(
                    str(request_obj.id),
                    request_obj.project_code,
                    request_obj.source_id,
                    request_obj.destination_id,
                    data.entity_ids,
                    data.username,
                    data.session_id,
                    auth,
                    file_folder_ids,
                )
                logger.info(f'Pipeline trigger for {len(copy_result)} files')
        skipped_data['updated'] = result.count()
        api_response.result = skipped_data
        return api_response.json_response()

    @router.put(
        '/request/copy/{project_code}', tags=[_API_TAG], response_model=PUTRequestFilesResponse, summary='Approve files'
    )
    async def complete_request(self, project_code: str, data: PUTRequest):
        logger.info('Complete request called')
        api_response = APIResponse()

        request_obj = db.session.query(RequestModel).get(data.request_id)

        query_params = {
            'request_id': data.request_id,
            'review_status': 'pending',
        }
        pending_files = db.session.query(EntityModel).filter_by(**query_params)
        if pending_files.count():
            pending_entities = [str(i.entity_id) for i in pending_files]
            pending_nodes = await bulk_get_by_ids(pending_entities)
            for entity in pending_nodes:
                if entity['status'] == MetadataItemStatus.ARCHIVED:
                    pending_entities.remove(entity['id'])
            if pending_entities:
                error_msg = f'{len(pending_entities)} pending files in request'
                logger.info(error_msg)
                api_response.error_msg = error_msg
                api_response.result = {
                    'status': 'pending',
                    'pending_entities': pending_entities,
                    'pending_count': len(pending_entities),
                }
                api_response.code = EAPIResponseCode.bad_request
                return api_response.json_response()

        request_obj.status = data.status
        request_obj.review_notes = data.review_notes
        request_obj.completed_by = data.username
        request_obj.completed_at = datetime.utcnow()
        db.session.commit()
        db.session.refresh(request_obj)

        submitted_at = request_obj.submitted_at.strftime('%Y-%m-%d %H:%M:%S')
        completed_at = request_obj.completed_at.strftime('%Y-%m-%d %H:%M:%S')
        await notify_user(request_obj.submitted_by, data.username, project_code, submitted_at, completed_at)
        api_response.result = {
            'status': data.status,
            'pending_entities': [],
            'pending_count': 0,
        }
        notification = Notification(
            request_obj.submitted_by,
            None,
            data.username,
            None,
            None,
            project_code,
            CopyRequestAction.CLOSE,
            data.request_id,
        )
        notification_client = NotificationServiceClient(ConfigClass.NOTIFICATION_SERVICE)
        notification_object = await notification.to_copy_request_notification()
        await notification_client.send_notification(notification_object)

        return api_response.json_response()

    @router.get(
        '/request/copy/{project_code}/pending-files',
        tags=[_API_TAG],
        response_model=GETPendingResponse,
        summary='Get pending count',
    )
    async def get_pending(self, project_code: str, params: GETRequestPending = Depends(GETRequestPending)):
        logger.info('Get Pending called')
        api_response = APIResponse()

        query_params = {
            'request_id': params.request_id,
            'review_status': 'pending',
        }
        pending_files = db.session.query(EntityModel).filter_by(**query_params)
        logger.info(f'{pending_files.count()} pending files in request')
        pending_entities = [str(i.entity_id) for i in pending_files]
        if pending_entities:
            pending_nodes = await bulk_get_by_ids(pending_entities)
            for entity in pending_nodes:
                if entity['status'] == MetadataItemStatus.ARCHIVED:
                    pending_entities.remove(entity['id'])
        api_response.result = {
            'pending_entities': pending_entities,
            'pending_count': len(pending_entities),
        }
        return api_response.json_response()

    @router.delete('/request/copy/{project_code}/delete/{request_id}', tags=[_API_TAG], summary='Delete Request')
    def delete_request(self, project_code: str, request_id: str):
        api_response = APIResponse()
        request_files = db.session.query(EntityModel).filter_by(request_id=request_id)
        for request_file in request_files:
            db.session.delete(request_file)
        db.session.commit()

        request_obj = db.session.query(RequestModel).get(request_id)
        db.session.delete(request_obj)
        db.session.commit()
        api_response.result = 'success'
        return api_response.json_response()

    @router.put(
        '/request/{request_id}/copy-status',
        tags=[_API_TAG],
        response_model=PUTCopyStatusResponse,
        summary='Update file copy status',
    )
    def update_copy_status(self, request_id: str, data: PUTCopyStatus):
        api_response = PUTCopyStatusResponse()
        try:
            updated_data = {'copy_status': data.copy_status}
            result = update_files_sql(request_id, updated_data, data.entities)
            api_response.result = [i.to_dict() for i in result]
        except Exception as e:
            logger.error(f'Update copy status failed due to: {e}')
            api_response.error_msg = f'Update copy status failed due to: {e}'
            api_response.code = EAPIResponseCode.bad_request
            return api_response.json_response()
        return api_response.json_response()
