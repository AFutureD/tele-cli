from __future__ import annotations

import inspect
from typing import Callable

import telethon
from telethon import TelegramClient
from telethon.errors import RPCError

from . import types
from .session import TGSession, load_session, session_ensure_current_valid


class TGClient(TelegramClient):
    async def _start_without_login(self) -> "TGClient":
        if not self.is_connected():
            await self.connect()
        return self

    async def async_start(
        self,
        phone: Callable[[], str],
        code: Callable[[], str | int],
        password: Callable[[], str],
    ) -> None:
        result = self.start(phone=phone, password=password, code_callback=code)
        if inspect.isawaitable(result):
            await result

    async def __aenter__(self):
        """
        override super `__aenter__` to avoid login process.
        """
        return await self._start_without_login()


class TeleCLI:
    @staticmethod
    async def create(session_name: str | None, config: types.Config, with_current: bool = True) -> TeleCLI:
        session: TGSession = load_session(session_name, with_current=with_current)

        client = TGClient(
            session=session,
            api_id=config.api_id,
            api_hash=config.api_hash,
        )

        return TeleCLI(client=client)

    def __init__(self, client: TGClient):
        self._client = client

    def client(self) -> TGClient:
        return self._client

    async def get_me(self) -> telethon.types.User | None:
        async with self.client() as client:
            await client.is_user_authorized()
            me = await client.get_me()
            return me if isinstance(me, telethon.types.User) else None

    async def logout(self) -> telethon.types.User | None:
        async with self.client() as client:
            me = await client.get_me()
            await client.log_out()
            session_ensure_current_valid(session=None)
            return me if isinstance(me, telethon.types.User) else None

    async def login(
        self,
        phone: Callable[[], str],
        code: Callable[[], str],
        password: Callable[[], str],
    ) -> telethon.types.User | None:
        try:
            async with self.client() as client:
                await client.async_start(phone=phone, code=code, password=password)
                me = await client.get_me()

                session_ensure_current_valid(session=client.session)

                return me if isinstance(me, telethon.types.User) else None
        except RPCError:
            session_ensure_current_valid(session=None)
        except KeyboardInterrupt:
            session_ensure_current_valid(session=None)
