# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import uvicorn

from app.config import ConfigClass
from app.main import create_app

app = create_app()

if __name__ == '__main__':
    uvicorn.run('run:app', host=ConfigClass.HOST, port=ConfigClass.PORT, log_level=ConfigClass.LOGGING_LEVEL)
