# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import re
from uuid import uuid4

import pytest

from app.commons.meta_services.models import MetadataItemStatus
from app.config import ConfigClass
from tests.conftest import DEST_FOLDER_ID
from tests.conftest import FILE_DATA
from tests.conftest import FOLDER_DATA
from tests.conftest import SRC_FOLDER_ID
from tests.conftest import TEST_ID_1
from tests.conftest import TEST_ID_2
from tests.conftest import TEST_ID_3


@pytest.mark.dependency()
def test_create_request_200(test_client, httpx_mock, mock_project, mock_src, mock_dest, mock_user, mock_roles):
    # entity_geids file
    FILE_DATA_1 = FILE_DATA.copy()
    FILE_DATA_1['id'] = TEST_ID_1
    FILE_DATA_1['parent'] = TEST_ID_2
    mock_data = {'result': [FILE_DATA_1, FOLDER_DATA]}
    url = re.compile('^' + ConfigClass.META_SERVICE + 'items/batch.*$')
    httpx_mock.add_response(method='GET', url=url, json=mock_data, status_code=200)

    # mock notification
    httpx_mock.add_response(method='POST', url=ConfigClass.EMAIL_SERVICE + 'email/', json={})

    # mock get file list
    mock_data = {'result': [FILE_DATA_1]}
    url = re.compile('^' + ConfigClass.META_SERVICE + 'items/search.*$')
    httpx_mock.add_response(method='GET', url=url, json=mock_data, status_code=200)

    payload = {
        'entity_ids': [TEST_ID_1, TEST_ID_2],
        'destination_id': DEST_FOLDER_ID,
        'source_id': SRC_FOLDER_ID,
        'note': 'testing',
        'submitted_by': 'admin',
    }
    headers = {'Authorization': 'fake'}
    response = test_client.post('/v1/request/copy/approval_fake_project', json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()['result']['destination_id'] == DEST_FOLDER_ID
    assert response.json()['result']['note'] == 'testing'
    request = httpx_mock.get_request(url=url)
    assert request.headers['Authorization'] == headers['Authorization']


@pytest.mark.dependency(depends=['test_create_request_200'])
def test_list_requests_200(test_client):
    payload = {'status': 'pending'}
    response = test_client.get('/v1/request/copy/approval_fake_project', params=payload)
    assert response.status_code == 200
    assert response.json()['result'][0]['destination_id'] == DEST_FOLDER_ID
    assert response.json()['result'][0]['note'] == 'testing'


@pytest.mark.dependency(depends=['test_create_request_200'])
def test_list_request_files_200(test_client):
    payload = {'status': 'pending'}
    response = test_client.get('/v1/request/copy/approval_fake_project', params=payload)
    request_obj = response.json()['result'][0]

    payload = {
        'request_id': request_obj['id'],
        'order_by': 'name',
        'order_type': 'desc',
    }
    response = test_client.get('/v1/request/copy/approval_fake_project/files', params=payload)
    assert response.status_code == 200
    assert len(response.json()['result']['data']) == 2
    assert len(response.json()['result']['routing']) == 0
    assert response.json()['result']['data'][0]['name'] == 'test_folder'
    assert response.json()['result']['data'][1]['name'] == 'test_file'


@pytest.mark.dependency(depends=['test_create_request_200'])
def test_list_request_files_query_200(test_client):
    payload = {
        'status': 'pending',
    }
    response = test_client.get('/v1/request/copy/approval_fake_project', params=payload)
    request_obj = response.json()['result'][0]

    payload = {
        'request_id': request_obj['id'],
        'order_by': 'name',
        'order_type': 'desc',
        'query': '{"name": "test_file"}',
        'parent_id': TEST_ID_2,
    }
    response = test_client.get('/v1/request/copy/approval_fake_project/files', params=payload)
    assert response.status_code == 200
    assert len(response.json()['result']['data']) == 1
    assert len(response.json()['result']['routing']) == 0
    assert response.json()['result']['data'][0]['name'] == 'test_file'


@pytest.mark.dependency(depends=['test_create_request_200'])
def test_approve_partial_files_200(
    test_client,
    httpx_mock,
    mock_project,
    mock_bulk_get_src,
    mock_bulk_get_dest,
    mock_bulk_get_id,
    mock_notification_send,
):
    payload = {'status': 'pending'}
    response = test_client.get('/v1/request/copy/approval_fake_project', params=payload)
    request_obj = response.json()['result'][0]

    # mock trigger pipeline
    httpx_mock.add_response(
        method='POST', url=ConfigClass.DATA_UTILITY_SERVICE + 'files/actions/', json={'operation_info': ''}
    )

    payload = {
        'entity_ids': [TEST_ID_1],
        'request_id': request_obj['id'],
        'review_status': 'approved',
        'username': 'admin',
        'session_id': 'admin-123',
    }
    headers = {
        'Authorization': 'fake',
        'Refresh-Token': 'fake',
    }
    response = test_client.patch('/v1/request/copy/approval_fake_project/files', json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()['result']['updated'] == 2
    assert response.json()['result']['approved'] == 0
    assert response.json()['result']['denied'] == 0


@pytest.mark.dependency(depends=['test_create_request_200'])
def test_approve_all_files_200(test_client, httpx_mock, mock_project):
    payload = {'status': 'pending'}
    response = test_client.get('/v1/request/copy/approval_fake_project', params=payload)
    request_obj = response.json()['result'][0]

    payload = {
        'request_id': request_obj['id'],
        'review_status': 'approved',
        'username': 'admin',
        'session_id': 'admin-123',
    }
    headers = {
        'Authorization': 'fake',
        'Refresh-Token': 'fake',
    }
    response = test_client.put('/v1/request/copy/approval_fake_project/files', json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()['result']['updated'] == 0
    assert response.json()['result']['approved'] == 2
    assert response.json()['result']['denied'] == 0


@pytest.mark.dependency(depends=['test_create_request_200'])
def test_complete_request_200(
    test_client,
    httpx_mock,
    mock_user,
    mock_project,
    mock_notification_send,
):
    payload = {'status': 'pending'}
    response = test_client.get('/v1/request/copy/approval_fake_project', params=payload)
    request_obj = response.json()['result'][0]

    # mock notification
    httpx_mock.add_response(method='POST', url=ConfigClass.EMAIL_SERVICE + 'email/', json={})

    payload = {
        'request_id': request_obj['id'],
        'session_id': 'admin-123',
        'status': 'complete',
        'review_notes': 'done',
        'username': 'admin',
    }
    response = test_client.put('/v1/request/copy/approval_fake_project', json=payload)
    assert response.status_code == 200
    assert response.json()['result']['status'] == 'complete'
    assert response.json()['result']['pending_count'] == 0


def test_create_request_sub_file_200(test_client, httpx_mock, mock_project, mock_dest, mock_src, mock_user, mock_roles):
    folder_data = FILE_DATA.copy()
    folder_data['id'] = str(uuid4())
    folder_data['parent_path'] = ''
    folder_data['type'] = 'folder'

    file_data = FILE_DATA.copy()
    file_data['id'] = str(uuid4())

    # mock notification
    httpx_mock.add_response(method='POST', url=ConfigClass.EMAIL_SERVICE + 'email/', json={})

    mock_data = {'result': [folder_data]}
    url = re.compile('^' + ConfigClass.META_SERVICE + 'items/batch.*$')
    httpx_mock.add_response(method='GET', url=url, json=mock_data, status_code=200)

    mock_data = {'result': [file_data]}
    url = re.compile('^' + ConfigClass.META_SERVICE + 'items/search.*$')
    httpx_mock.add_response(method='GET', url=url, json=mock_data, status_code=200)

    payload = {
        'entity_ids': [file_data['id']],
        'destination_id': DEST_FOLDER_ID,
        'source_id': SRC_FOLDER_ID,
        'note': 'testing',
        'submitted_by': 'admin',
    }
    response = test_client.post('/v1/request/copy/approval_fake_project', json=payload)
    assert response.status_code == 200
    assert response.json()['result']['destination_id'] == DEST_FOLDER_ID
    assert response.json()['result']['note'] == 'testing'


def test_deny_partial_files_200(test_client):
    payload = {'status': 'pending'}
    response = test_client.get('/v1/request/copy/approval_fake_project', params=payload)
    request_obj = response.json()['result'][0]

    payload = {
        'entity_ids': [
            FILE_DATA['id'],
        ],
        'request_id': request_obj['id'],
        'review_status': 'denied',
        'username': 'admin',
        'session_id': 'admin-123',
    }
    headers = {
        'Authorization': 'fake',
        'Refresh-Token': 'fake',
    }
    response = test_client.patch('/v1/request/copy/approval_fake_project/files', json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()['result']['updated'] == 0
    assert response.json()['result']['approved'] == 0
    assert response.json()['result']['denied'] == 0


def test_partial_approved_200(
    test_client,
    httpx_mock,
    mock_dest,
    mock_src,
    mock_user,
    mock_project,
    mock_roles,
    mock_bulk_get_src,
    mock_bulk_get_dest,
    mock_notification_send,
):
    FILE_DATA_2 = FILE_DATA.copy()
    FILE_DATA_2['id'] = TEST_ID_3

    # mock trigger pipeline
    httpx_mock.add_response(
        method='POST', url=ConfigClass.DATA_UTILITY_SERVICE + 'files/actions/', json={'operation_info': ''}
    )

    # entity_geids file
    mock_data = {'result': [FILE_DATA_2]}
    url = re.compile('^' + ConfigClass.META_SERVICE + 'items/batch.*$')
    httpx_mock.add_response(method='GET', url=url, json=mock_data, status_code=200)

    # mock notification
    httpx_mock.add_response(method='POST', url=ConfigClass.EMAIL_SERVICE + 'email/', json={})

    payload = {
        'entity_ids': [FILE_DATA['id'], FILE_DATA_2['id']],
        'destination_id': DEST_FOLDER_ID,
        'source_id': SRC_FOLDER_ID,
        'note': 'testing',
        'submitted_by': 'admin',
    }
    response = test_client.post('/v1/request/copy/approval_fake_project', json=payload)
    assert response.status_code == 200
    assert response.json()['result']['destination_id'] == DEST_FOLDER_ID
    assert response.json()['result']['note'] == 'testing'

    request_obj = response.json()['result']

    payload = {
        'entity_ids': [FILE_DATA['id']],
        'request_id': request_obj['id'],
        'review_status': 'denied',
        'username': 'admin',
        'session_id': 'admin-123',
    }
    headers = {
        'Authorization': 'fake',
        'Refresh-Token': 'fake',
    }
    response = test_client.patch('/v1/request/copy/approval_fake_project/files', json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()['result']['updated'] == 0
    assert response.json()['result']['approved'] == 0
    assert response.json()['result']['denied'] == 0

    payload = {
        'entity_ids': [FILE_DATA_2['id']],
        'request_id': request_obj['id'],
        'review_status': 'approved',
        'username': 'admin',
        'session_id': 'admin-123',
    }
    headers = {
        'Authorization': 'fake',
        'Refresh-Token': 'fake',
    }
    response = test_client.patch('/v1/request/copy/approval_fake_project/files', json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()['result']['updated'] == 1
    assert response.json()['result']['approved'] == 0
    assert response.json()['result']['denied'] == 0


def test_complete_pending_400(
    test_client,
    httpx_mock,
    mock_dest,
    mock_src,
    mock_user,
    mock_project,
    mock_roles,
):
    FILE_DATA_2 = FILE_DATA.copy()
    FILE_DATA_2['id'] = TEST_ID_3

    # entity_geids file
    mock_data = {'result': [FILE_DATA_2]}
    url = re.compile('^' + ConfigClass.META_SERVICE + 'items/batch.*$')
    httpx_mock.add_response(method='GET', url=url, json=mock_data, status_code=200)

    # mock notification
    httpx_mock.add_response(method='POST', url=ConfigClass.EMAIL_SERVICE + 'email/', json={})

    payload = {
        'entity_ids': [FILE_DATA_2['id']],
        'destination_id': DEST_FOLDER_ID,
        'source_id': SRC_FOLDER_ID,
        'note': 'testing',
        'submitted_by': 'admin',
    }
    response = test_client.post('/v1/request/copy/approval_fake_project', json=payload)
    assert response.status_code == 200
    assert response.json()['result']['destination_id'] == DEST_FOLDER_ID
    assert response.json()['result']['note'] == 'testing'

    request_obj = response.json()['result']

    payload = {
        'request_id': request_obj['id'],
        'session_id': 'admin-123',
        'status': 'complete',
        'review_notes': 'done',
        'username': 'admin',
    }
    response = test_client.put('/v1/request/copy/approval_fake_project', json=payload)
    assert response.status_code == 400
    assert response.json()['result']['status'] == 'pending'
    assert response.json()['result']['pending_count'] == 1


def test_pending_files_list_200(test_client, httpx_mock):
    # entity_geids file
    mock_data = {'result': [FILE_DATA]}
    url = re.compile('^' + ConfigClass.META_SERVICE + 'items/batch.*$')
    httpx_mock.add_response(method='GET', url=url, json=mock_data, status_code=200)

    payload = {'status': 'pending'}
    response = test_client.get('/v1/request/copy/approval_fake_project', params=payload)
    request_obj = response.json()['result'][0]

    payload = {
        'request_id': request_obj['id'],
    }
    response = test_client.get('/v1/request/copy/approval_fake_project/pending-files', params=payload)

    assert response.status_code == 200
    assert response.json()['result']['pending_entities'] == [TEST_ID_3]
    assert response.json()['result']['pending_count'] == 1


def test_pending_files_list_handle_archived_200(test_client, httpx_mock, create_copy_request):
    archived_data = FILE_DATA.copy()
    archived_data['id'] = TEST_ID_1
    archived_data['status'] = MetadataItemStatus.ARCHIVED
    mock_data = {'result': [archived_data]}
    url = re.compile('^' + ConfigClass.META_SERVICE + 'items/batch.*$')
    httpx_mock.add_response(method='GET', url=url, json=mock_data, status_code=200)

    payload = {'status': 'pending'}
    response = test_client.get('/v1/request/copy/fake_project', params=payload)
    request_obj = response.json()['result'][0]

    payload = {
        'request_id': request_obj['id'],
    }
    response = test_client.get('/v1/request/copy/fake_project/pending-files', params=payload)

    assert response.status_code == 200
    assert response.json()['result']['pending_entities'] == []
    assert response.json()['result']['pending_count'] == 0


def test_update_copy_status_200(test_client, httpx_mock):
    payload = {'status': 'pending'}
    response = test_client.get('/v1/request/copy/approval_fake_project', params=payload)
    request_obj = response.json()['result'][0]
    request_id = request_obj['id']
    payload = {'entities': [TEST_ID_3], 'copy_status': 'copied'}
    response = test_client.put(f'/v1/request/{request_id}/copy-status', json=payload)
    assert response.status_code == 200
    assert response.json()['result'][0]['copy_status'] == 'copied'


def test_update_copy_status_400(test_client, httpx_mock):
    payload = {'status': 'pending'}
    response = test_client.get('/v1/request/copy/approval_fake_project', params=payload)
    request_obj = response.json()['result'][0]
    request_id = request_obj['id']
    payload = {'entities': ['not_exist'], 'copy_status': 'copied'}
    response = test_client.put(f'/v1/request/{request_id}/copy-status', json=payload)
    assert response.status_code == 400
