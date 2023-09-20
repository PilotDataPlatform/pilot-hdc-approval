# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import re
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateSchema
from sqlalchemy.schema import CreateTable
from sqlalchemy_utils import create_database
from sqlalchemy_utils import database_exists
from testcontainers.postgres import PostgresContainer

from app.commons.meta_services.models import MetadataItemStatus
from app.config import ConfigClass
from app.main import create_app
from app.models.copy_request_sql import Base
from app.models.copy_request_sql import EntityModel
from app.models.copy_request_sql import RequestModel

DEST_FOLDER_ID = str(uuid4())
SRC_FOLDER_ID = str(uuid4())
TEST_ID_1 = str(uuid4())
TEST_ID_2 = str(uuid4())
TEST_ID_3 = str(uuid4())

FILE_DATA = {
    'id': str(uuid4()),
    'display_path': 'test/',
    'name': 'test_file',
    'created_time': '2021-06-09T13:44:12.381872077',
    'owner': 'admin',
    'size': 123,
    'status': MetadataItemStatus.ACTIVE,
    'parent_path': 'fake/path',
    'container_code': 'testproject',
    'zone': 0,
    'type': 'file',
    'parent': None,
    'parent_id': None,
}

FOLDER_DATA = {
    'id': str(uuid4()),
    'display_path': 'test/',
    'name': 'test_folder',
    'created_time': '2021-06-09T13:44:12.381872077',
    'owner': 'admin',
    'status': MetadataItemStatus.ACTIVE,
    'parent_path': 'fake/path',
    'container_code': 'testproject',
    'zone': 0,
    'type': 'folder',
    'parent': None,
    'parent_id': None,
}

USER_DATA = {
    'first_name': 'Greg',
    'last_name': 'Testing',
    'username': 'greg',
    'email': 'greg@test.com',
}


class TestProject:
    id = 1234
    labels = ['Container']
    global_entity_id = 'test-project-id'
    code = 'testproject'
    roles = ['admin', 'collaborator', 'contributor']
    type = 'Usecase'
    tags = ['tag1', 'tag2', 'tag3']
    path = 'testproject'
    time_lastmodified = '2022-04-06T20:25:07'
    discoverable = True
    system_tags = ['copied-to-core']
    name = 'Fake Test Project'
    time_created = '2021-05-07T16:14:18'


@pytest.fixture
def mock_project(mocker):
    # mock get project
    mocker.patch('common.project.project_client.ProjectClient.get', return_value=TestProject)


@pytest.fixture
def mock_user(httpx_mock: HTTPXMock):
    # mock get user
    user_data = {'result': USER_DATA}
    httpx_mock.add_response(
        method='GET', url=ConfigClass.AUTH_SERVICE + 'admin/user?username=admin&exact=true', json=user_data
    )


@pytest.fixture
def mock_roles(httpx_mock: HTTPXMock):
    result = {
        'result': [
            {
                'email': 'fake@fake.com',
                'username': 'fake',
                'first_name': 'fake',
            }
        ],
    }
    httpx_mock.add_response(method='POST', url=ConfigClass.AUTH_SERVICE + 'admin/roles/users', json=result)


@pytest.fixture
def mock_src(httpx_mock):
    get_by_geid_url = ConfigClass.META_SERVICE + 'item'
    mock_folder = FOLDER_DATA.copy()
    mock_folder['id'] = str(SRC_FOLDER_ID)
    mock_folder['name'] = 'src_folder'
    mock_data = {'result': mock_folder}
    httpx_mock.add_response(
        method='GET', url=get_by_geid_url + '/' + str(SRC_FOLDER_ID) + '/', json=mock_data, status_code=200
    )


@pytest.fixture
def mock_dest(httpx_mock):
    get_by_geid_url = ConfigClass.META_SERVICE + 'item'
    mock_folder = FOLDER_DATA.copy()
    mock_folder['id'] = str(DEST_FOLDER_ID)
    mock_folder['name'] = 'dest_folder'
    mock_data = {'result': mock_folder}
    httpx_mock.add_response(
        method='GET', url=get_by_geid_url + '/' + str(DEST_FOLDER_ID) + '/', json=mock_data, status_code=200
    )


@pytest.fixture
def mock_bulk_get_src(httpx_mock):
    get_by_geid_url = ConfigClass.META_SERVICE + 'items/batch/'
    mock_folder = FOLDER_DATA.copy()
    mock_folder['id'] = str(SRC_FOLDER_ID)
    mock_folder['name'] = 'src_folder'
    mock_data = {'result': [mock_folder]}
    httpx_mock.add_response(
        method='GET', url=f'{get_by_geid_url}?ids={str(SRC_FOLDER_ID)}', json=mock_data, status_code=200
    )


@pytest.fixture
def mock_bulk_get_dest(httpx_mock):
    get_by_geid_url = ConfigClass.META_SERVICE + 'items/batch/'
    mock_folder = FOLDER_DATA.copy()
    mock_folder['id'] = str(DEST_FOLDER_ID)
    mock_folder['name'] = 'dest_folder'
    mock_data = {'result': [mock_folder]}
    httpx_mock.add_response(
        method='GET', url=f'{get_by_geid_url}?ids={str(DEST_FOLDER_ID)}', json=mock_data, status_code=200
    )


@pytest.fixture
def mock_bulk_get_id(httpx_mock):
    mock_file = FILE_DATA.copy()
    mock_file['id'] = str(TEST_ID_1)
    mock_file['name'] = 'TEST_ID_1'
    mock_file2 = FILE_DATA.copy()
    mock_file2['id'] = str(TEST_ID_2)
    mock_file2['name'] = 'TEST_ID_2'
    mock_data = {'result': [mock_file, mock_file2]}
    url = re.compile(f'^{ConfigClass.META_SERVICE}items/batch.*$')
    httpx_mock.add_response(method='GET', url=url, json=mock_data, status_code=200)


@pytest.fixture
def mock_notification_send(httpx_mock):
    get_by_geid_url = ConfigClass.NOTIFICATION_SERVICE + '/v1/all/notifications/'
    mock_data = {'result': 'success'}
    httpx_mock.add_response(method='POST', url=get_by_geid_url, json=mock_data, status_code=204)


@pytest.fixture
def create_copy_request(test_client, httpx_mock, mock_project, mock_src, mock_dest, mock_user, mock_roles):
    FILE_DATA_1 = FILE_DATA.copy()
    FILE_DATA_1['id'] = TEST_ID_1
    FILE_DATA_1['parent'] = TEST_ID_2
    FILE_DATA_1['status'] = MetadataItemStatus.ARCHIVED
    mock_data = {'result': [FILE_DATA_1]}
    url = re.compile('^' + ConfigClass.META_SERVICE + 'items/batch.*$')
    httpx_mock.add_response(method='GET', url=url, json=mock_data, status_code=200)

    # mock notification
    httpx_mock.add_response(method='POST', url=ConfigClass.EMAIL_SERVICE + 'email/', json={})

    payload = {
        'entity_ids': [TEST_ID_1, TEST_ID_2],
        'destination_id': DEST_FOLDER_ID,
        'source_id': SRC_FOLDER_ID,
        'note': 'testing',
        'submitted_by': 'admin',
    }
    headers = {'Authorization': 'fake'}
    response = test_client.post('/v1/request/copy/fake_project', json=payload, headers=headers)
    assert response.status_code == 200


@pytest.fixture(scope='session', autouse=True)
def db():
    with PostgresContainer('postgres:9.5') as postgres:
        postgres_uri = postgres.get_connection_url()
        if not database_exists(postgres_uri):
            create_database(postgres_uri)
        engine = create_engine(postgres_uri)
        CreateTable(RequestModel.__table__).compile(dialect=postgresql.dialect())
        CreateTable(EntityModel.__table__).compile(dialect=postgresql.dialect())
        if not engine.dialect.has_schema(engine, ConfigClass.RDS_SCHEMA_DEFAULT):
            engine.execute(CreateSchema(ConfigClass.RDS_SCHEMA_DEFAULT))
        Base.metadata.create_all(bind=engine)
        yield postgres


@pytest.fixture
def test_client(db):
    ConfigClass.DB_URI = db.get_connection_url()
    app = create_app()
    client = TestClient(app)
    return client
