# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from uuid import UUID

from fastapi_sqlalchemy import db

from app.models.copy_request_sql import EntityModel


def get_sql_files_recursive(request_id: str, folder_id: str, file_ids: list[str] = None) -> list[EntityModel]:
    if not file_ids:
        file_ids = []

    entities = db.session.query(EntityModel).filter_by(request_id=request_id, parent_id=folder_id)
    for entity in entities:
        if entity.entity_type == 'file':
            if entity.review_status == 'pending':
                file_ids.append(entity.entity_id)
        else:
            file_ids = get_sql_files_recursive(request_id, entity.entity_id, file_ids=file_ids)
    return file_ids


def get_all_sub_files(request_id: str, entity_ids: list[str]) -> list[str]:
    entities = (
        db.session.query(EntityModel).filter_by(request_id=request_id).filter(EntityModel.entity_id.in_(entity_ids))
    )
    file_ids = []
    for entity in entities:
        if entity.entity_type == 'file' and entity.review_status == 'pending':
            file_ids.append(entity.entity_id)
        else:
            file_ids = get_sql_files_recursive(request_id, entity.entity_id, file_ids=file_ids)
    return file_ids


def get_files_until_top_parent(request_id: UUID, file_ids: list[str]) -> set:
    entity_ids = set()
    entities = (
        db.session.query(EntityModel).filter_by(request_id=request_id).filter(EntityModel.entity_id.in_(file_ids))
    )
    for entity in entities:
        current = entity
        while current is not None:
            entity_ids.add(str(current.entity_id))
            current = (
                db.session.query(EntityModel).filter_by(request_id=request_id, entity_id=current.parent_id).first()
            )
    return entity_ids


def get_sql_file_nodes_recursive(
    request_id: str, folder_id: str, review_status: str, files: list = None
) -> list[EntityModel]:
    if not files:
        files = []

    entities = db.session.query(EntityModel).filter_by(request_id=request_id, parent_id=folder_id)
    for entity in entities:
        if entity.entity_type == 'file':
            if entity.review_status == review_status:
                files.append(entity.entity_id)
        else:
            files = get_sql_file_nodes_recursive(request_id, entity.entity_id, review_status, files=files)
    return files


def get_all_sub_folder_nodes(request_id: str, entity_ids: list[str], review_status: str) -> list[str]:
    entities = (
        db.session.query(EntityModel).filter_by(request_id=request_id).filter(EntityModel.entity_id.in_(entity_ids))
    )
    files = []
    for entity in entities:
        if entity.entity_type == 'folder':
            files = get_sql_file_nodes_recursive(request_id, entity.entity_id, review_status, files=files)
        elif entity.review_status == review_status:
            files.append(entity.entity_id)
    return files


def update_files_sql(request_id: UUID, updated_data: dict, file_ids: list[str]):
    files = db.session.query(EntityModel).filter_by(request_id=request_id).filter(EntityModel.entity_id.in_(file_ids))
    files.update(updated_data)
    db.session.commit()
    return files


def create_entity_from_node(request_id: str, entity: dict) -> EntityModel:
    """Create entity in psql given meta."""

    entity_data = {
        'request_id': request_id,
        'entity_id': entity['id'],
        'entity_type': entity['type'],
        'parent_id': entity['parent'],
        'name': entity['name'],
        'uploaded_by': entity['owner'],
        'uploaded_at': entity['created_time'],
    }
    if entity['type'] == 'file':
        entity_data['review_status'] = 'pending'
        entity_data['file_size'] = entity['size']
        entity_data['copy_status'] = 'pending'
    entity_obj = EntityModel(**entity_data)
    db.session.add(entity_obj)
    db.session.commit()
    return entity_obj
