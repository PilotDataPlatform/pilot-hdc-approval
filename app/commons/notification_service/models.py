# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import json
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic import conlist


class CopyRequestAction(Enum):
    APPROVAL = 'approval'
    DENIAL = 'denial'
    CLOSE = 'close'


class NotificationType(str, Enum):
    COPY_REQUEST = 'copy-request'


class TargetType(str, Enum):
    FILE = 'file'
    FOLDER = 'folder'


class Location(BaseModel):
    id: UUID
    path: str
    zone: int


class Target(BaseModel):
    id: UUID
    name: str
    type: TargetType


class CopyRequestNotification(BaseModel):
    type: NotificationType = NotificationType.COPY_REQUEST
    recipient_username: str
    action: CopyRequestAction
    initiator_username: str
    project_code: str
    copy_request_id: UUID
    source: Optional[Location]
    destination: Optional[Location]
    targets: Optional[conlist(Target, min_items=1)]

    def to_json(self):
        return json.loads(self.json())


class Node(dict):
    """Store information about one node."""

    def __str__(self) -> str:
        return f'{self.id} | {self.name}'

    def __dict__(self) -> dict:
        return self

    @property
    def parent(self) -> str:
        return self['parent']

    @property
    def parent_path(self) -> str:
        return self['parent_path']

    @property
    def id(self) -> str:
        return self['id']

    @property
    def name(self) -> str:
        return self['name']

    @property
    def size(self) -> int:
        return self.get('size', 0)

    @property
    def container_code(self) -> str:
        return self.get('container_code')

    @property
    def owner(self) -> str:
        return self.get('owner')

    @property
    def namespace(self) -> str:
        result = {1: 'Core'}.get(self.get('zone'), 'Greenroom')
        return result

    @property
    def zone(self) -> int:
        return self.get('zone')

    @property
    def entity_type(self) -> str:
        return self.get('type')

    @property
    def display_path(self) -> Path:
        if self['parent_path']:
            full_path = '{}/{}'.format(self['parent_path'], self['name'])
        else:
            full_path = self['name']
        display_path = Path(full_path)

        if display_path.is_absolute():
            display_path = display_path.relative_to('/')

        return display_path
