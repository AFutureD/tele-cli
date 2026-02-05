from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich import print
from telethon.tl.custom import Dialog

from tele_cli import utils
from tele_cli.app import TeleCLI
from tele_cli.config import load_config
from tele_cli.types import OutputFormat

from .auth import auth_cli
from .types import SharedArgs

cli = typer.Typer(
    epilog="Telegram CLI",
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="",
)
dialog_cli = typer.Typer()
cli.add_typer(auth_cli, name="auth")
cli.add_typer(dialog_cli, name="dialog")


@cli.callback()
def main(
    ctx: typer.Context,
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Configuration File Path",
            file_okay=True,
            writable=True,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
    session: Annotated[str | None, typer.Option()] = None,
    fmt: Annotated[OutputFormat, typer.Option("--format", "-f", help="Output format")] = OutputFormat.text,
) -> None:
    ctx.obj = SharedArgs(fmt=fmt, config_file=config_file, session=session)


@cli.command(name="me")
def me_get(ctx: typer.Context) -> None:
    cli_args: SharedArgs = ctx.obj

    async def _run() -> bool:
        app = await TeleCLI.create(session_name=cli_args.session, config=load_config(config_file=cli_args.config_file))

        me = await app.get_me()
        if not me:
            return False

        print(utils.fmt.format_me(me, cli_args.fmt))
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@dialog_cli.command(name="list")
def conversation_list(ctx: typer.Context):
    cli_args: SharedArgs = ctx.obj

    async def _run() -> bool:
        app = await TeleCLI.create(session_name=cli_args.session, config=load_config(config_file=cli_args.config_file))
        async with app.client() as client:
            dialog_list: list[Dialog] = [item async for item in client.iter_dialogs()]

            print(utils.fmt.format_dialog_list(dialog_list, cli_args.fmt))

        return False

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)
