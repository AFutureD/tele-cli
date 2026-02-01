from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich import print
from telethon.tl.custom import Dialog

from tele_cli import utils
from tele_cli.app import TeleCLI
from tele_cli.utils.fmt import OutputFormat

from .auth import auth_cli

cli = typer.Typer(
    epilog="Telegram CLI",
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="",
)
conversation_cli = typer.Typer()
cli.add_typer(auth_cli, name="auth")
cli.add_typer(conversation_cli, name="dialog")


@cli.callback()
def main(
    ctx: typer.Context,
    fmt: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.json,
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["fmt"] = fmt


@cli.command(name="me")
def me_get(ctx: typer.Context):
    output_format: utils.fmt.OutputFormat = ctx.obj["fmt"] or OutputFormat.json

    async def _run() -> bool:
        app = await TeleCLI.create()
        me = await app.get_me()

        if not me:
            return False

        print(utils.fmt.format_me(me, output_format))
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@conversation_cli.command(name="list")
def conversation_list(ctx: typer.Context):
    async def _run() -> bool:
        output_format: utils.fmt.OutputFormat = ctx.obj["fmt"] or OutputFormat.json

        app = await TeleCLI.create()
        async with app.client() as client:
            dialog_list: list[Dialog] = [item async for item in client.iter_dialogs()]

            print(utils.fmt.format_dialog_list(dialog_list, output_format))

        return False

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)
