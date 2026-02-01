from __future__ import annotations

import pathlib
import typing
from typing import Optional

import telethon
from telethon import TelegramClient
from telethon.sessions import Session


class TeleCLI:
    @staticmethod
    async def create(session: typing.Union[str, pathlib.Path, Session]) -> TeleCLI:
        # TODO: make it from config
        api_id = 611335
        api_hash = "d524b414d21f4d37f08684c1df41ac9c"
        client = TelegramClient(session=session, api_id=api_id, api_hash=api_hash)

        return TeleCLI(client)

    def __init__(self, client: TelegramClient):
        self._client = client

    def client(self) -> TelegramClient:
        return self._client

    async def get_me(self) -> Optional[telethon.types.User]:
        async with self.client() as client:
            me = await client.get_me()
            if not isinstance(me, telethon.types.User):
                return None
            return me
