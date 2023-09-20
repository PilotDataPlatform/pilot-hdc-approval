# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import httpx

from app.commons.notifier_service.email_service import SrvEmail
from app.commons.project_services import query_project
from app.config import ConfigClass


async def get_user(username: str) -> dict:
    query = {
        'username': username,
        'exact': True,
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(ConfigClass.AUTH_SERVICE + 'admin/user', params=query)
    if response.status_code != 200:
        raise Exception(f'Error getting user {username} from auth service: ' + str(response.json()))
    return response.json()['result']


async def notify_project_admins(username: str, project_code: str, request_timestamp: str):
    user_node = await get_user(username)
    project = await query_project(project_code)
    payload = {
        'role_names': [f'{project_code}-admin'],
        'status': 'active',
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(ConfigClass.AUTH_SERVICE + 'admin/roles/users', json=payload)
    project_admins = response.json()['result']
    for project_admin in project_admins:
        email_service = SrvEmail()
        await email_service.send(
            'A new request to copy data to Core needs your approval',
            project_admin['email'],
            ConfigClass.EMAIL_SUPPORT,
            msg_type='html',
            template='copy_request/new_request.html',
            template_kwargs={
                'admin_first_name': project_admin.get('first_name', project_admin['username']),
                'user_first_name': user_node.get('first_name', user_node['username']),
                'user_last_name': user_node.get('last_name'),
                'project_name': project.name,
                'request_timestamp': request_timestamp,
            },
        )


async def notify_user(
    username: str, admin_username: str, project_code: str, request_timestamp: str, complete_timestamp: str
):
    user_node = await get_user(username)
    admin_node = await get_user(admin_username)
    project = await query_project(project_code)
    email_service = SrvEmail()
    await email_service.send(
        'Your request to copy data to Core is Completed',
        user_node['email'],
        ConfigClass.EMAIL_SUPPORT,
        msg_type='html',
        template='copy_request/complete_request.html',
        template_kwargs={
            'user_first_name': user_node.get('first_name', user_node['username']),
            'admin_first_name': admin_node.get('first_name', admin_node['username']),
            'admin_last_name': admin_node.get('last_name'),
            'request_timestamp': request_timestamp,
            'complete_timestamp': complete_timestamp,
            'project_name': project.name,
        },
    )
