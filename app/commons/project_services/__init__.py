# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from common.project.project_client import ProjectClient

from app.config import ConfigClass


async def query_project(project_code: str) -> dict:
    project_client = ProjectClient(ConfigClass.PROJECT_SERVICE, ConfigClass.REDIS_URI)
    project = await project_client.get(code=project_code)
    return project
