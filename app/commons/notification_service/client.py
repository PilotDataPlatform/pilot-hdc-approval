# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from typing import List
from typing import Optional
from uuid import UUID

import httpx
from common import LoggerFactory

from app.commons.meta_services import bulk_get_by_ids
from app.commons.notification_service.models import CopyRequestAction
from app.commons.notification_service.models import CopyRequestNotification
from app.commons.notification_service.models import Location
from app.commons.notification_service.models import Node
from app.commons.notification_service.models import Target
from app.commons.notification_service.models import TargetType
from app.config import ConfigClass

logger = LoggerFactory(
    'api_copy_request',
    level_default=ConfigClass.LOG_LEVEL_DEFAULT,
    level_file=ConfigClass.LOG_LEVEL_FILE,
    level_stdout=ConfigClass.LOG_LEVEL_STDOUT,
    level_stderr=ConfigClass.LOG_LEVEL_STDERR,
).get_logger()


class Notification:
    def __init__(
        self,
        recipient_username: str,
        include_ids: Optional[list[str]],
        initiator_username: str,
        source_id: Optional[str],
        destination_id: Optional[str],
        project_code: str,
        action: CopyRequestAction,
        request_id: UUID,
    ) -> None:
        self.recipient_username = recipient_username
        self.include_ids = include_ids
        self.initiator_username = initiator_username
        self.source_id = source_id
        self.destination_id = destination_id
        self.project_code = project_code
        self.action = action
        self.request_id = request_id

    async def set_location(self, entity_id: str) -> Location:
        result = await bulk_get_by_ids([entity_id])
        node = Node(result[0])
        return Location(id=node.id, path=str(node.display_path), zone=node.zone)

    async def set_targets(self) -> List[Target]:
        result = await bulk_get_by_ids(self.include_ids)
        nodes = {node['id']: Node(node) for node in result}
        targets = []
        for _node, file_node in nodes.items():
            targets.append(Target(id=file_node.id, name=file_node.name, type=TargetType(file_node.entity_type)))
        return targets

    async def to_copy_request_notification(self):
        source_folder = await self.set_location(self.source_id) if self.source_id else None
        targets_entity = await self.set_targets() if self.include_ids else None
        destination_folder = await self.set_location(self.destination_id) if self.destination_id else None
        notification = CopyRequestNotification(
            recipient_username=self.recipient_username,
            action=self.action,
            initiator_username=self.initiator_username,
            project_code=self.project_code,
            copy_request_id=self.request_id,
            source=source_folder,
            destination=destination_folder,
            targets=targets_entity,
        )
        return notification


class NotificationServiceClient:
    """Client for sending notifications into Notification Service."""

    def __init__(self, endpoint: str) -> None:
        self.endpoint = f'{endpoint}/v1'

    async def send_notification(self, notification: CopyRequestNotification) -> None:
        """Calling notification service API to create notification."""
        payload = notification.to_json()
        async with httpx.AsyncClient() as client:
            response = await client.post(f'{self.endpoint}/all/notifications/', json=payload)
        if response.status_code != 204:
            logger.error('Failed to create notification for copy request')
            raise Exception('Unable to create notifications for copy request')
