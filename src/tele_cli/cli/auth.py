import asyncio
from pathlib import Path

import typer
from rich import print

from tele_cli import utils
from tele_cli.app import TeleCLI
from tele_cli.config import load_config
from tele_cli.session import list_session_info
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
