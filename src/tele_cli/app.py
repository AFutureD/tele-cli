from __future__ import annotations

import telethon
from telethon import TelegramClient
from telethon.sessions import SQLiteSession

from . import types
from .session import load_session


class TeleCLI:
    @staticmethod
    async def create(
        session: str | None, config: types.Config, with_current: bool = True
    ) -> TeleCLI:
        session: SQLiteSession = load_session(session, with_current=with_current)

        client = TelegramClient(
            session=session,
            api_id=config.api_id,
            api_hash=config.api_hash,
        )

        return TeleCLI(client)

    def __init__(self, client: TelegramClient):
        self._client = client

    def client(self) -> TelegramClient:
        return self._client

    async def get_me(self) -> telethon.types.User | None:
        async with self.client() as client:
            me = await client.get_me()
            return me if isinstance(me, telethon.types.User) else None

    async def logout(self) -> telethon.types.User | None:
        try:
            await self.client().connect()
            me = await self.client().get_me()
            await self.client().log_out()

            return me if isinstance(me, telethon.types.User) else None
        finally:
            # noinspection PyUnresolvedReferences
            await self.client().disconnect()
