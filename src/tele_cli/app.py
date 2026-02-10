from __future__ import annotations

import inspect
from typing import Callable

import telethon
from telethon import TelegramClient
from telethon import hints
from telethon.custom import Dialog
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

    async def send_message(
        self,
        receiver: str | int,
        message: str = "",
        reply_to: int | None = None,
        link_preview: bool = True,
        file: list[hints.FileLike] | None = None,
        thumb: hints.FileLike | None = None,
        force_document: bool = False,
        supports_streaming: bool = False,
        comment_to: int | None = None,
    ) -> bool:
        """
        Send a message to a Telegram entity.

        Receiver resolution:
        - `int`: treated as a peer ID (see https://core.telegram.org/api/peers#peer-id).
        - `str`: first try Telethon's resolver (username, phone, etc).
          If that fails, fall back to scanning dialogs and picking the *unique* match by:
          - dialog name contains `receiver` (case-insensitive), or
          - dialog peer id equals `receiver`, or
          - dialog entity id equals `receiver`.

        Notes:
        - If multiple dialogs match the fallback scan, `receiver` is passed through unchanged
          (i.e. no guessing).
        - `file` and `thumb` are forwarded to Telethon's `send_message` as-is.
        """

        async with self.client() as client:

            async def _resolve_entity(target: str | int) -> hints.EntityLike:
                # Fast path: let Telethon resolve usernames/phones/IDs without scanning dialogs.
                try:
                    return await client.get_input_entity(target)
                except Exception:
                    pass

                # NOTICE: do not convert str to int by default.
                #         the phone and the peer_id can not be determined.

                # if input is int, it must be peer_id, and we do not need do any matching.
                if isinstance(target, int):
                    return target

                # Fallback: scan dialogs for a unique match (avoid building the full list).
                target_norm = target.casefold()
                async for dialog in client.iter_dialogs():
                    name = (dialog.name or "").casefold()
                    if target_norm and target_norm in name:
                        return dialog.entity

                    if str(dialog.id) == target or str(dialog.entity.id) == target:
                        return dialog.entity

                # If no match found, return the original target
                return target

            entity = await _resolve_entity(receiver)

            await client.send_message(
                entity,
                message,
                reply_to=reply_to,  # type: ignore[arg-type]
                link_preview=link_preview,
                file=file,  # type: ignore[arg-type]
                thumb=thumb,  # type: ignore[arg-type]
                force_document=force_document,
                supports_streaming=supports_streaming,
                comment_to=comment_to,  # type: ignore[arg-type]
            )
            return True

    async def list_dialogs(self, with_archived: bool = False) -> list[Dialog]:
        async with self.client() as client:
            archived = None if with_archived else False
            return [item async for item in client.iter_dialogs(archived=archived)]
