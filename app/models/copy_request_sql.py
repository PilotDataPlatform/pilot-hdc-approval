# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

from app.config import ConfigClass

Base = declarative_base()


class RequestModel(Base):
    __tablename__ = 'approval_request'
    __table_args__ = {'schema': ConfigClass.RDS_SCHEMA_DEFAULT}
    id = Column(UUID(as_uuid=True), unique=True, primary_key=True, default=uuid4)
    status = Column(String())
    submitted_by = Column(String())
    submitted_at = Column(DateTime(), default=datetime.utcnow)
    destination_id = Column(UUID(as_uuid=True))
    source_id = Column(UUID(as_uuid=True))
    note = Column(String())
    project_code = Column(String())
    destination_path = Column(String())
    source_path = Column(String())
    review_notes = Column(String())
    completed_by = Column(String())
    completed_at = Column(DateTime())

    def to_dict(self):
        result = {}
        for field in self.__table__.columns.keys():
            if field in ['submitted_at', 'completed_at']:
                if getattr(self, field):
                    result[field] = str(getattr(self, field).isoformat()[:-3] + 'Z')
                else:
                    result[field] = None
            elif field in ['id', 'destination_id', 'source_id']:
                result[field] = str(getattr(self, field))
            else:
                result[field] = getattr(self, field)
        return result


class EntityModel(Base):
    __tablename__ = 'approval_entity'
    __table_args__ = {'schema': ConfigClass.RDS_SCHEMA_DEFAULT}
    id = Column(UUID(as_uuid=True), unique=True, primary_key=True, default=uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey(RequestModel.id))
    entity_id = Column(UUID(as_uuid=True))
    entity_type = Column(String())
    review_status = Column(String())
    reviewed_by = Column(String())
    reviewed_at = Column(String())
    parent_id = Column(UUID(as_uuid=True))
    copy_status = Column(String())
    name = Column(String())
    uploaded_by = Column(String(), nullable=True)
    uploaded_at = Column(DateTime(), default=datetime.utcnow)
    file_size = Column(BigInteger(), nullable=True)

    def to_dict(self):
        result = {}
        for field in self.__table__.columns.keys():
            if field == 'uploaded_at':
                result[field] = str(getattr(self, field).isoformat()[:-3] + 'Z')
            elif field in ['id', 'request_id', 'entity_id', 'parent_id']:
                result[field] = str(getattr(self, field))
            else:
                result[field] = getattr(self, field)
        return result
