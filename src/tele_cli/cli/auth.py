from pytest import Session
from tele_cli.types.session import SessionInfo
import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich import print

from tele_cli import utils
from tele_cli.app import TeleCLI
from tele_cli.config import load_config
from tele_cli.session import list_session_info, session_switch
from tele_cli.types import OutputFormat
from tele_cli.utils.fmt import format_session_info_list

auth_cli = typer.Typer(
    no_args_is_help=True,
)


@auth_cli.command(name="login")
def auth_login(ctx: typer.Context):
    output_format: utils.fmt.OutputFormat = ctx.obj["fmt"] or OutputFormat.json
    config_file: Path | None = ctx.obj["config_file"]
    session: str = ctx.obj["session"]

    def get_phone() -> str:
        print("""
        Telegram login requires your phone number.

        1. Enter your Telegram phone number with [bold green]country code[/bold green].
        2. Telegram will send a [bold green]login[/bold green] code to your Telegram app (from the official [bold red]Telegram account[/bold red]).
        3. Enter that [bold green]code[/bold green] in the next step.
        4. Your [bold green]password[/bold green] will be asked, if Two-Step Verification is enabled (Settings → Privacy and Security).

        [bold red]IMPORTANT: Your input will not be stored or shared.[/bold red]

        Example: 8615306541234

        """)

        return typer.prompt("Please enter phone number", type=str)

    def get_code() -> str:
        return typer.prompt("Please enter login code", type=str)

    def get_password() -> str:
        return typer.prompt("Please enter your password", type=str, hide_input=True)

    async def _run() -> bool:
        app = await TeleCLI.create(
            session=session,
            config=load_config(config_file=config_file),
            with_current=False,
        )

        me = await app.login(phone=get_phone, code=get_code, password=get_password)
        if not me:
            return False

        print(f"Hi {utils.fmt.format_me(me, OutputFormat.text)}")
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@auth_cli.command(name="logout")
def auth_logout(ctx: typer.Context):
    output_format: utils.fmt.OutputFormat = ctx.obj["fmt"] or OutputFormat.json
    config_file: Path | None = ctx.obj["config_file"]
    session: str = ctx.obj["session"]

    async def _run() -> bool:
        app = await TeleCLI.create(
            session=session, config=load_config(config_file=config_file)
        )

        me = await app.logout()
        if me:
            print(f"Bye {utils.fmt.format_me(me, OutputFormat.text)}")
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@auth_cli.command(name="list")
def auth_list(ctx: typer.Context):
    output_format: utils.fmt.OutputFormat = ctx.obj["fmt"] or OutputFormat.json
    config_file: Path | None = ctx.obj["config_file"]

    async def _run() -> bool:
        session_info_list = await list_session_info()
        print(format_session_info_list(session_info_list, fmt=output_format))
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@auth_cli.command(name="switch")
def auth_switch(
    ctx: typer.Context,
    user_id: Annotated[
        int | None,
        typer.Option("--uid", help="Telegram user id to switch to (e.g. 7820000665)."),
    ] = None,
    username: Annotated[
        str | None,
        typer.Option(help="Telegram username to switch to (e.g. @alice)."),
    ] = None,
    session: Annotated[
        str | None,
        typer.Option(help="Session name to use (as shown in `tele auth list`)."),
    ] = None,
):
    if username and username.startswith("@"):
        username = username.removeprefix("@")

    async def _run() -> bool:
        if not user_id and not username and not session:
            raise typer.BadParameter(
                "Provide at least one of: user_id, username, or session."
            )

        session_info_list = await list_session_info()

        def predicator(session_info: SessionInfo) -> bool:
            cond_1 = True if session and session == session_info.session_name else False
            cond_2 = True if username and username == session_info.user_name else False
            cond_3 = True if user_id and user_id == session_info.user_id else False

            return cond_1 or cond_2 or cond_3

        session_info_list = list(filter(predicator, session_info_list))

        if len(session_info_list) == 0:
            raise typer.BadParameter("No Session Matched")

        if len(session_info_list) > 1:
            raise typer.BadParameter("Multiple Sessions Matched")

        session_info = session_info_list[0]
        session_switch(session_path=session_info.path)

        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)
