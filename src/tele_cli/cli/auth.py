import asyncio
from pathlib import Path

import typer
from rich import print

from tele_cli import utils
from tele_cli.app import TeleCLI
from tele_cli.config import load_config
from tele_cli.session import session_ensure_current_valid
from tele_cli.types import OutputFormat

auth_cli = typer.Typer(
    no_args_is_help=True,
)


@auth_cli.command(name="login")
def auth_login(ctx: typer.Context):
    output_format: utils.fmt.OutputFormat = ctx.obj["fmt"] or OutputFormat.json
    config_file: Path | None = ctx.obj["config_file"]
    session: str = ctx.obj["session"]

    # TODO: custom login process
    async def _run() -> bool:
        app = await TeleCLI.create(
            session=session,
            config=load_config(config_file=config_file),
            with_current=False,
        )

        try:
            me = await app.get_me()
        except KeyboardInterrupt:
            session_ensure_current_valid(session=None)
            return False

        if not me:
            return False

        session_ensure_current_valid(session=app.client().session)

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

        session_ensure_current_valid(session=None)

        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)
