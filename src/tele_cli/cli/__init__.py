from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Tuple

from tele_cli.types.tl import DialogType, EntityType
import telethon
import typer
from telethon.tl.custom import Dialog
from telethon.tl.types import Message

from tele_cli import utils
from tele_cli.app import TeleCLI
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
cli.add_typer(auth_cli, name="auth")
cli.add_typer(dialog_cli, name="dialog")
cli.add_typer(message_cli, name="message")


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
        earliest_message: telethon.types.Message | None = None
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
        await app.send_message(entity, content)

        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)
