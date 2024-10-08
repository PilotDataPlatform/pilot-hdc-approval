# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import httpx

from app.config import ConfigClass


class SrvEmail:
    async def send(self, subject, receiver, sender, content='', msg_type='plain', template=None, template_kwargs=None):
        if template_kwargs is None:
            template_kwargs = {}
        url = ConfigClass.EMAIL_SERVICE + 'email/'
        payload = {
            'subject': subject,
            'sender': sender,
            'receiver': [receiver],
            'msg_type': msg_type,
        }
        if content:
            payload['message'] = content
        if template:
            payload['template'] = template
            payload['template_kwargs'] = template_kwargs
        async with httpx.AsyncClient() as client:
            res = await client.post(url=url, json=payload)
        return res.json()
