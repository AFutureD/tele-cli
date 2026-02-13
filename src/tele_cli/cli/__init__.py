from __future__ import annotations

import asyncio
import builtins
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Annotated, Tuple

from tele_cli.types.tl import DialogType, EntityType
import typer
from telethon import events
from telethon import hints
from telethon.tl.custom import Dialog, Message
from telethon.tl.types import UpdateUserStatus, UserStatusOnline

from tele_cli import utils
from tele_cli.app import TGClient, TeleCLI
from tele_cli.config import load_config
from tele_cli.types import OutputFormat, OutputOrder, get_dialog_type
from tele_cli.constant import VERSION
from tele_cli.utils import print

from .auth import auth_cli
from .types import SharedArgs

cli = typer.Typer(
    epilog="Made by Huanan",
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="""
    The Telegram CLI.

    Quick Start:

    1. tele auth login
    2. tele me
    3. tele dialog list
    4. tele message list <dialog_id> -n 20

    WARNING: DO NOT SUPPORT BOT FOR NOW.
    """,
)
dialog_cli = typer.Typer(
    no_args_is_help=True,
    help="""
    List chats, groups and channels from your account.
    """,
)
message_cli = typer.Typer(
    no_args_is_help=True,
    help="""
    Inspect dialog messages.
    """,
)
daemon_cli = typer.Typer(
    no_args_is_help=True,
    help="""
    Run long-lived worker process.
    """,
)
cli.add_typer(auth_cli, name="auth")
cli.add_typer(dialog_cli, name="dialog")
cli.add_typer(message_cli, name="message")
cli.add_typer(daemon_cli, name="daemon")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"tele-cli, version {VERSION}")
        raise typer.Exit()


@cli.callback()
def main(
    ctx: typer.Context,
    # meta
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
    # shared args
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Path to config TOML file. \\[default: ~/.config/tele/config.toml]",
            file_okay=True,
            writable=True,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
    session: Annotated[
        str | None,
        typer.Option(help="Session name. List via `tele auth list`. \\[default: Current]"),
    ] = None,
    fmt: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format."),
    ] = OutputFormat.text,
) -> None:
    """Hei Hei"""
    _ = version
    ctx.obj = SharedArgs(fmt=fmt, config_file=config_file, session=session)


@cli.command(name="me")
def me_get(ctx: typer.Context) -> None:
    """
    Show the current authenticated Telegram account.
    """

    cli_args: SharedArgs = ctx.obj

    async def _run() -> bool:
        app = await TeleCLI.create(session_name=cli_args.session, config=load_config(config_file=cli_args.config_file))

        me = await app.get_me()
        if not me:
            return False

        print(utils.fmt.format_me(me, cli_args.fmt), fmt=cli_args.fmt)
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@dialog_cli.command(name="list")
def dialog_list(
    ctx: typer.Context,
    dialog_type_filters: Annotated[
        list[DialogType] | None,
        typer.Option("--type", "-t", help="Filter by dialog type."),
    ] = None,
    archived: Annotated[
        bool,
        typer.Option("--archived", help="Include archived dialogs (otherwise hidden)."),
    ] = False,
):
    """
    List dialogs from your account.

    Archived dialogs are hidden by default; use `--archived` to include them.

    Text Format Template:

    `[TYPE.UI.STATE] [UNREAD COUNT] [DIALOG_ID] NAME`

    - TYPE: Dialog type. U: user; G: group; C: channel;
    - UI: The UI State of dialog. P: pinned, A: archived; -: normal.
    - STATE: Dialog State. M: muted; -: not muted.

    Examples:
    - `tele dialog list -t user`
    - `tele dialog list -t user -t channel --archived`
    """

    cli_args: SharedArgs = ctx.obj

    async def _run() -> bool:
        app = await TeleCLI.create(session_name=cli_args.session, config=load_config(config_file=cli_args.config_file))

        dialog_list: list[Dialog] = await app.list_dialogs(with_archived=archived)

        def _filter_dialogs(dialogs: list[Dialog], dialog_types: list[DialogType] | None = None) -> list[Dialog]:
            if not dialog_types:
                return dialogs

            return [d for d in dialogs if get_dialog_type(d) in dialog_types]

        dialog_list = _filter_dialogs(dialog_list, dialog_types=dialog_type_filters)

        print(utils.fmt.format_dialog_list(dialog_list, cli_args.fmt), fmt=cli_args.fmt)
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@message_cli.command(name="list")
def messages_list(
    ctx: typer.Context,
    dialog_id: Annotated[int, typer.Argument(help="Dialog peer ID (see `tele dialog list`).")],
    from_str: Annotated[str | None, typer.Option("--from", help="Start boundary")] = None,
    to_str: Annotated[str | None, typer.Option("--to", help="End boundary")] = None,
    range_str: Annotated[
        str | None,
        typer.Option("--range", help="Natural-language date range (overrides --from/--to)."),
    ] = None,
    num: Annotated[int | None, typer.Option("--num", "-n", help="Maximum number of messages to fetch.")] = None,
    offset_id: Annotated[int, typer.Option("--offset_id", help="Pagination offset message ID (excluded).")] = 0,
    order: Annotated[
        OutputOrder,
        typer.Option("--order", help="Output order by time."),
    ] = OutputOrder.asc,
):
    """
    List messages from a dialog.

    By default (no --num and no date filters), it fetches the latest message.

    Filtering:
    - Limit with --num/-n.
    - Date filters: --from, --to, or --range.
    - --range takes priority over --from and --to.

    Date input:
    - --from/--to use `dateparser.parse`, e.g. "+1d", "yesterday", "2 weeks ago".
    - --range uses `dateparser.search.search_dates`, e.g. "last week", "next month".
      Special case: "this week" is treated as Sunday..Saturday.

    Examples:
    1. `tele message list 1375282077 -n 10`
    2. `tele message list 1375282077 --range "last week"`
    3. `tele message list 1375282077 --from "2025-02-05" --to "yestarday"`
    4. `tele message list 1375282077 --from "-5d"`
    5. `tele message list 1375282077 --from "today" -n 100`
    """
    cli_args: SharedArgs = ctx.obj

    date_range: Tuple[datetime | None, datetime | None] = (None, None)
    if True:
        """convert from_str, to_str, range_str to date_range"""
        import dateparser
        from dateparser.search import search_dates

        date_from: datetime | None = None
        if from_str:
            date_from = dateparser.parse(from_str)
            date_from = date_from and date_from.replace(hour=0, minute=0, second=0, microsecond=0)

        date_to: datetime | None = None
        if to_str:
            date_to = dateparser.parse(to_str)
            date_to = date_to and date_to.replace(hour=23, minute=59, second=59, microsecond=0)

        date_span: list[datetime] | None = None
        if range_str and range_str == "this week":
            start_date = dateparser.parse("sunday")
            assert start_date is not None
            date_span = [start_date, start_date + timedelta(days=6)]
        elif range_str:
            dates = search_dates(range_str, settings={"RETURN_TIME_SPAN": True}) or []
            if len(dates) == 2:
                # https://github.com/scrapinghub/dateparser/blob/cd5f226454e0ed3fe93164e7eff55b00f57e57c7/dateparser/search/search.py#L202
                start = next((x for (s, x) in dates if "start" in s), None)
                end = next((x for (s, x) in dates if "end" in s), None)
                if start and end:
                    date_span = [start, end]
        if date_span:
            date_range = (date_span[0], date_span[1])
        else:
            date_range = (date_from, date_to)

    limit: int | None = None
    if num:
        limit = num
    if limit == 0 and date_range == (None, None):
        limit = 1

    async def _run() -> bool:
        app = await TeleCLI.create(session_name=cli_args.session, config=load_config(config_file=cli_args.config_file))

        (date_start, date_end) = date_range
        earliest_message: Message | None = None
        if date_start:
            async with app.client() as client:
                ret: list[Message] = [msg async for msg in client.iter_messages(dialog_id, offset_date=date_start, limit=1, offset_id=-1)]
                earliest_message = ret[0] if len(ret) >= 1 else None

        min_id: int = earliest_message.id if earliest_message else 0

        async with app.client() as client:
            messages: list[Message] = [
                msg
                async for msg in client.iter_messages(
                    dialog_id,
                    min_id=min_id,
                    add_offset=(-1 if min_id else 0),
                    offset_id=offset_id,
                    offset_date=date_end,
                    limit=limit,  # type: ignore[arg-type]  # Telethon accepts None despite annotation
                )
            ]
            if order == OutputOrder.asc:
                messages = list(reversed(messages))

            print(utils.fmt.format_message_list(messages, cli_args.fmt), fmt=cli_args.fmt)

        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@message_cli.command(name="send", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def message_send(
    ctx: typer.Context,
    receiver: Annotated[
        str,
        typer.Argument(
            help="Receiver: username/phone/peer_id",
        ),
    ],
    content: Annotated[str, typer.Argument(help="Message text.")] = "",
    entity_type: Annotated[
        EntityType | None,
        typer.Option("--entity", "-t", help="How to interpret RECEIVER (e.g. `peer_id`)."),
    ] = None,
    reply_to: Annotated[
        int | None,
        typer.Option("--reply-to", help="Reply to a specific message id."),
    ] = None,
    file: Annotated[
        list[Path] | None,
        typer.Option("--file", help="Attach local file(s). Can be used multiple times."),
    ] = None,
):
    """
    Send a message to RECEIVER.

    RECEIVER can be a username, phone number, dialog name, or a numeric `peer_id`.
    List known dialogs with `tele dialog list`.

    How RECEIVER is resolved:
    - With `--entity/-t <type>`, RECEIVER is passed through as that type and no matching is attempted.
    - Without `--entity`, it tries to match the most likely dialog; if nothing matches, RECEIVER is passed through unchanged.

    Examples:
    1. `tele message send alice "hi"`
    2. `tele message send "+15551234567" "hi"`
    3. `tele message send "My Group" "hi"`
    4. `tele message send -t peer_id "-1001234567890" "hi"`
    """
    cli_args: SharedArgs = ctx.obj

    entity: int | str
    match entity_type:
        case EntityType.peer_id:
            entity = int(receiver)
        case _:
            entity = receiver

    async def _run() -> bool:
        app = await TeleCLI.create(session_name=cli_args.session, config=load_config(config_file=cli_args.config_file))
        file_args = [str(item) for item in (file or [])]
        await app.send_message(
            entity,
            content,
            reply_to=reply_to,
            file=file_args or None,
        )

        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@daemon_cli.command(name="start")
def daemon_start(
    ctx: typer.Context,
    rpc_stdio: Annotated[
        bool,
        typer.Option(
            "--rpc-stdio",
            help="Enable newline-delimited JSON RPC over stdio.",
        ),
    ] = False,
) -> None:
    """
    Start daemon and print all incoming new messages.
    """

    cli_args: SharedArgs = ctx.obj

    async def _resolve_entity_with_client(client: TGClient, target: str | int) -> hints.EntityLike:
        # Fast path: Telethon resolver (username, phone, id).
        try:
            ret = await client.get_input_entity(target)
            return ret
        except Exception:
            pass

        if isinstance(target, int):
            return target

        target_norm = target.casefold()
        async for dialog in client.iter_dialogs():
            name = (dialog.name or "").casefold()
            if target_norm and target_norm in name:
                return dialog.entity

            if str(dialog.id) == target or str(dialog.entity.id) == target:
                return dialog.entity

        return target

    async def _send_message_with_connected_client(
        client: TGClient,
        receiver: str | int,
        message: str,
        entity_type_str: str | None = None,
        reply_to: int | None = None,
        file_paths: list[str] | None = None,
    ) -> bool:
        entity: str | int = receiver
        if entity_type_str == EntityType.peer_id.value:
            entity = int(receiver)

        resolved = await _resolve_entity_with_client(client=client, target=entity)
        await client.send_message(
            resolved,
            message,
            reply_to=reply_to,
            file=file_paths or None,
        )
        return True

    async def _run() -> bool:
        app = await TeleCLI.create(session_name=cli_args.session, config=load_config(config_file=cli_args.config_file))
        async with app.client() as client:
            is_authorized = await client.is_user_authorized()
            if not is_authorized:
                return False

            emit_lock = asyncio.Lock()
            stop_event = asyncio.Event()
            me = await client.get_me()
            self_user_id = int(me.id) if me is not None else None
            self_online = isinstance(getattr(me, "status", None), UserStatusOnline)

            def _json_default(value: object) -> object:
                if isinstance(value, datetime):
                    return value.isoformat()
                if isinstance(value, timedelta):
                    return value.total_seconds()
                if isinstance(value, bytes):
                    try:
                        return value.decode("utf-8")
                    except UnicodeDecodeError:
                        return value.hex()
                if isinstance(value, Path):
                    return str(value)
                to_dict = getattr(value, "to_dict", None)
                if callable(to_dict):
                    try:
                        return to_dict()
                    except Exception:
                        pass
                return repr(value)

            async def _emit_json(obj: dict[str, object]) -> None:
                line = json.dumps(obj, ensure_ascii=False, default=_json_default)
                async with emit_lock:
                    while True:
                        try:
                            builtins.print(line, flush=True)
                            return
                        except BlockingIOError:
                            try:
                                loop = asyncio.get_running_loop()
                                writable = loop.create_future()

                                def _on_writable() -> None:
                                    if not writable.done():
                                        writable.set_result(None)

                                fd = sys.stdout.fileno()
                                loop.add_writer(fd, _on_writable)
                                try:
                                    await writable
                                finally:
                                    loop.remove_writer(fd)
                            except Exception:
                                await asyncio.sleep(0.01)
                        except BrokenPipeError:
                            # Downstream consumer closed stdout; stop emitting.
                            return

            def _normalize_username(value: object) -> str | None:
                if not isinstance(value, str):
                    return None
                raw = value.strip()
                if not raw:
                    return None
                return raw[1:] if raw.startswith("@") else raw

            def _build_name(*parts: object) -> str | None:
                tokens = [str(part).strip() for part in parts if isinstance(part, str) and str(part).strip()]
                if not tokens:
                    return None
                return " ".join(tokens)

            async def _refresh_self_online() -> None:
                nonlocal self_online
                try:
                    current = await client.get_me()
                    if current is None:
                        return
                    self_online = isinstance(getattr(current, "status", None), UserStatusOnline)
                except Exception:
                    return

            async def on_raw_update(update: object) -> None:
                nonlocal self_online
                if self_user_id is None:
                    return
                if not isinstance(update, UpdateUserStatus):
                    return
                try:
                    if int(update.user_id) != self_user_id:
                        return
                except Exception:
                    return
                self_online = isinstance(update.status, UserStatusOnline)

            async def on_new_message(event: events.NewMessage.Event) -> None:
                msg = event.message
                if not isinstance(msg, Message):
                    return
                if not rpc_stdio:
                    print(utils.fmt.format_message_list([msg], cli_args.fmt), fmt=cli_args.fmt)
                    return
                try:
                    sender_name: str | None = None
                    sender_username: str | None = None
                    chat_title: str | None = None
                    chat_username: str | None = None
                    try:
                        sender = await event.get_sender()
                        sender_name = _build_name(
                            getattr(sender, "first_name", None),
                            getattr(sender, "last_name", None),
                        ) or (
                            getattr(sender, "title", None).strip()
                            if isinstance(getattr(sender, "title", None), str)
                            and getattr(sender, "title", None).strip()
                            else None
                        )
                        sender_username = _normalize_username(getattr(sender, "username", None))
                    except Exception:
                        pass
                    try:
                        chat = await event.get_chat()
                        if isinstance(getattr(chat, "title", None), str) and getattr(chat, "title", None).strip():
                            chat_title = getattr(chat, "title", None).strip()
                        chat_username = _normalize_username(getattr(chat, "username", None))
                    except Exception:
                        pass

                    # Keep daemon event payload compact to avoid stdout back-pressure stalls.
                    payload: dict[str, object] = {
                        "id": msg.id,
                        "message": msg.message,
                        "date": msg.date,
                        "out": msg.out,
                        "post": msg.post,
                        "peer_id": msg.peer_id.to_dict() if getattr(msg, "peer_id", None) is not None else None,
                        "from_id": msg.from_id.to_dict() if getattr(msg, "from_id", None) is not None else None,
                        "sender_id": msg.sender_id,
                        "sender_name": sender_name,
                        "sender_username": sender_username,
                        "chat_title": chat_title,
                        "chat_username": chat_username,
                        "self_online": self_online,
                    }
                    await _emit_json(
                        {
                            "type": "event",
                            "event": "new_message",
                            "payload": payload,
                        }
                    )
                except Exception:
                    # Never crash the Telethon update loop because of stdout back-pressure.
                    return

            async def _presence_loop() -> None:
                while not stop_event.is_set():
                    await _refresh_self_online()
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=15)
                    except TimeoutError:
                        continue

            client.add_event_handler(on_new_message, events.NewMessage())
            client.add_event_handler(on_raw_update, events.Raw())

            async def _rpc_loop() -> None:
                loop = asyncio.get_running_loop()
                reader = asyncio.StreamReader()
                protocol = asyncio.StreamReaderProtocol(reader)
                await loop.connect_read_pipe(lambda: protocol, sys.stdin)

                while True:
                    raw_line = await reader.readline()
                    if not raw_line:
                        break
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue

                    req_id: str | None = None
                    try:
                        packet = json.loads(line)
                        if not isinstance(packet, dict):
                            raise ValueError("request must be an object")
                        req_id = str(packet.get("id", ""))
                        method = packet.get("method")
                        params = packet.get("params")
                        if not isinstance(method, str):
                            raise ValueError("method must be a string")
                        if params is None:
                            params = {}
                        if not isinstance(params, dict):
                            raise ValueError("params must be an object")

                        if method == "ping":
                            await _emit_json({"type": "response", "id": req_id, "ok": True, "result": {"pong": True}})
                            continue

                        if method == "send_message":
                            receiver_raw = params.get("receiver")
                            if receiver_raw is None:
                                raise ValueError("receiver is required")
                            message_raw = params.get("message", "")
                            entity_type_raw = params.get("entity_type")
                            reply_to_raw = params.get("reply_to")
                            file_raw = params.get("file")
                            receiver = str(receiver_raw)
                            message = str(message_raw)
                            entity_type_str = str(entity_type_raw) if entity_type_raw is not None else None
                            reply_to: int | None = None
                            if isinstance(reply_to_raw, int):
                                reply_to = reply_to_raw
                            elif isinstance(reply_to_raw, str):
                                trimmed_reply = reply_to_raw.strip()
                                if trimmed_reply:
                                    reply_to = int(trimmed_reply)
                            file_paths: list[str] | None = None
                            if isinstance(file_raw, str):
                                trimmed = file_raw.strip()
                                file_paths = [trimmed] if trimmed else None
                            elif isinstance(file_raw, list):
                                parsed_paths = [str(item).strip() for item in file_raw if str(item).strip()]
                                file_paths = parsed_paths or None

                            await _send_message_with_connected_client(
                                client=client,
                                receiver=receiver,
                                message=message,
                                entity_type_str=entity_type_str,
                                reply_to=reply_to,
                                file_paths=file_paths,
                            )
                            await _emit_json(
                                {
                                    "type": "response",
                                    "id": req_id,
                                    "ok": True,
                                    "result": {
                                        "sent": True,
                                        "receiver": receiver,
                                    },
                                }
                            )
                            continue

                        if method == "stop":
                            stop_event.set()
                            await _emit_json({"type": "response", "id": req_id, "ok": True, "result": {"stopping": True}})
                            continue

                        raise ValueError(f"unknown method: {method}")
                    except Exception as err:
                        await _emit_json(
                            {
                                "type": "response",
                                "id": req_id or "",
                                "ok": False,
                                "error": str(err),
                            }
                        )

            rpc_task: asyncio.Task[None] | None = None
            presence_task = asyncio.create_task(_presence_loop())
            if rpc_stdio:
                await _emit_json({"type": "ready", "mode": "rpc_stdio", "self_online": self_online})
                rpc_task = asyncio.create_task(_rpc_loop())
            else:
                print("daemon started, waiting for new messages...", fmt=cli_args.fmt)

            wait_tasks: set[asyncio.Task[Any]] = {
                asyncio.ensure_future(client.disconnected),
                asyncio.create_task(stop_event.wait()),
                presence_task,
            }
            if rpc_task:
                wait_tasks.add(rpc_task)

            done, pending = await asyncio.wait(wait_tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()

            if stop_event.is_set():
                await client.disconnect()
            else:
                for task in done:
                    if task is rpc_task and rpc_task.exception():
                        raise rpc_task.exception()  # type: ignore[misc]

        return True

    try:
        ok = asyncio.run(_run())
    except KeyboardInterrupt:
        raise typer.Exit(code=0)
    if not ok:
        raise typer.Exit(code=1)
