from __future__ import annotations

import uuid
from pathlib import Path

import telethon
from telethon import TelegramClient
from telethon.sessions import SQLiteSession

from . import types
from .shared import get_app_user_defualt_dir


def get_app_session_folder() -> Path:
    ret = get_app_user_defualt_dir() / "sessions"
    ret.mkdir(parents=True, exist_ok=True)
    return ret


def get_app_session_current() -> Path:
    return get_app_session_folder() / "Current.session"


def _get_session_path(session_name: str | None) -> Path:
    if session_name:
        return get_app_session_folder() / session_name

    current = get_app_session_current()
    if current.exists():
        return current

    return get_app_session_folder() / str(uuid.uuid4())


def load_session(session_name: str | None) -> SQLiteSession:
    session_path = _get_session_path(session_name=session_name)
    return SQLiteSession(str(session_path))


class TeleCLI:
    @staticmethod
    async def create(session: str | None, config: types.Config) -> TeleCLI:
        session: SQLiteSession = load_session(session)

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
            if not isinstance(me, telethon.types.User):
                return None
            return me
