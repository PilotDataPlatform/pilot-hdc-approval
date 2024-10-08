# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import logging
from functools import lru_cache
from typing import Any
from typing import Dict

from common import VaultClient
from pydantic import BaseSettings
from pydantic import Extra
from starlette.config import Config

config = Config('.env')
SRV_NAMESPACE = config('APP_NAME', cast=str, default='service_approval')
CONFIG_CENTER_ENABLED = config('CONFIG_CENTER_ENABLED', cast=str, default='false')


def load_vault_settings(settings: BaseSettings) -> Dict[str, Any]:
    if CONFIG_CENTER_ENABLED == 'false':
        return {}
    else:
        return vault_factory()


def vault_factory() -> dict:
    vc = VaultClient(config('VAULT_URL'), config('VAULT_CRT'), config('VAULT_TOKEN'))
    return vc.get_from_vault(SRV_NAMESPACE)


class Settings(BaseSettings):
    APP_NAME: str = 'approval_service'
    version: str = '2.1.0'

    PORT: int = 8000
    HOST: str = '0.0.0.0'

    LOGGING_LEVEL: int = logging.INFO
    LOGGING_FORMAT: str = 'json'

    AUTH_SERVICE: str = 'http://127.0.0.1:5061'
    DATAOPS_SERVICE: str = 'http://127.0.0.1:5063'
    EMAIL_SERVICE: str = 'http://127.0.0.1:5065'
    METADATA_SERVICE: str = 'http://127.0.0.1:5065'
    PROJECT_SERVICE: str = 'http://127.0.0.1:5064'
    NOTIFICATION_SERVICE: str = 'http://127.0.0.1:5065'

    RDS_SCHEMA_DEFAULT: str = 'public'
    RDS_DB: str = 'approval'
    RDS_HOST: str = 'localhost'
    RDS_USER: str = 'postgres'
    RDS_PASSWORD: str = 'postgres'
    RDS_PORT: str = '5432'

    REDIS_DB: int = 0
    REDIS_HOST: str = '127.0.0.1'
    REDIS_PASSWORD: str = ''
    REDIS_PORT: int = 6379

    EMAIL_SUPPORT: str = 'random_email@not_a_host.not'

    def __init__(self, *args: Any, **kwds: Any) -> None:
        super().__init__(*args, **kwds)

        self.AUTH_SERVICE = self.AUTH_SERVICE + '/v1/'
        self.DATA_UTILITY_SERVICE = self.DATAOPS_SERVICE + '/v1/'
        self.EMAIL_SERVICE = self.EMAIL_SERVICE + '/v1/'
        self.META_SERVICE = self.METADATA_SERVICE + '/v1/'
        self.REDIS_URI = f'redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:' f'{self.REDIS_PORT}/{self.REDIS_DB}'
        self.DB_URI = (
            f'postgresql://{self.RDS_USER}:{self.RDS_PASSWORD}@{self.RDS_HOST}:' f'{self.RDS_PORT}/{self.RDS_DB}'
        )

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = Extra.allow

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            return env_settings, load_vault_settings, init_settings, file_secret_settings


@lru_cache(1)
def get_settings():
    settings = Settings()
    return settings


ConfigClass = get_settings()
