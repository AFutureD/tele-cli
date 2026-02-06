from .types import SharedArgs
import asyncio
from typing import Annotated

import typer
from rich import print

from tele_cli import utils
from tele_cli.app import TeleCLI
from tele_cli.config import load_config
from tele_cli.session import list_session_list, session_switch, TGSession
from tele_cli.utils.fmt import format_session_info_list

auth_cli = typer.Typer(
    no_args_is_help=True,
    rich_markup_mode="rich",
    help="""
[bold]Authentication commands[/bold]
Manage Telegram login sessions.
""",
)


@auth_cli.command(
    name="login",
    help="Login with phone/code/password and create a local session.",
)
def auth_login(
    ctx: typer.Context,
    switch_as_current: Annotated[
        bool,
        typer.Option("--switch", "-s", help="Automatic set the login session as current."),
    ] = False,
):
    cli_args: SharedArgs = ctx.obj

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
            session_name=cli_args.session,
            config=load_config(config_file=cli_args.config_file),
            with_current=False,
        )

        me = await app.login(phone=get_phone, code=get_code, password=get_password)
        if not me:
            return False

        session = app.client().session
        if switch_as_current and isinstance(session, TGSession):
            session_switch(session=session)

        print(f"Hi {utils.fmt.format_me(me, cli_args.fmt)}")
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@auth_cli.command(name="logout", help="Logout from the selected session.")
def auth_logout(ctx: typer.Context):
    cli_args: SharedArgs = ctx.obj

    async def _run() -> bool:
        app = await TeleCLI.create(session_name=cli_args.session, config=load_config(config_file=cli_args.config_file))

        me = await app.logout()
        if me:
            print(f"Bye {utils.fmt.format_me(me, cli_args.fmt)}")
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@auth_cli.command(name="list", help="List all local Telegram sessions.")
def auth_list(ctx: typer.Context):
    cli_args: SharedArgs = ctx.obj

    async def _run() -> bool:
        session_list = await list_session_list()

        session_info_list = await asyncio.gather(*(session.get_info() for session in session_list))
        session_info_list = [session_info for session_info in session_info_list if session_info is not None]

        print(format_session_info_list(session_info_list, fmt=cli_args.fmt))
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@auth_cli.command(name="switch", help="Switch [green]Current.session[/green] to a matching local session.")
def auth_switch(
    ctx: typer.Context,
    user_id: Annotated[
        int | None,
        typer.Option("--uid", help="Telegram user peer id to switch to (e.g. 7820000665)."),
    ] = None,
    username: Annotated[
        str | None,
        typer.Option(help="Telegram username to switch to (e.g. @alice)."),
    ] = None,
    session_name: Annotated[
        str | None,
        typer.Option("--session", help="Session name to use (as shown in `tele auth list`)."),
    ] = None,
):
    if username and username.startswith("@"):
        username = username.removeprefix("@")

    async def _run() -> bool:
        if not user_id and not username and not session_name:
            raise typer.BadParameter("Provide at least one of: user_id, username, or session.")

        session_list = await list_session_list()

        async def predicator(session: TGSession) -> bool:
            session_info = await session.get_info()
            if session_info is None:
                return False

            cond_1 = True if session_name and session_name == session_info.session_name else False
            cond_2 = True if username and username == session_info.user_name else False
            cond_3 = True if user_id and user_id == session_info.user_id else False

            return cond_1 or cond_2 or cond_3

        session_list = [s for s in session_list if await predicator(s)]

        if len(session_list) == 0:
            raise typer.BadParameter("No Session Matched")

        if len(session_list) > 1:
            raise typer.BadParameter("Multiple Sessions Matched")

        session = session_list[0]
        session_switch(session=session)

        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)
