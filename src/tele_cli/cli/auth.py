import asyncio
from pathlib import Path

import typer

from tele_cli import utils
from tele_cli.app import TeleCLI
from tele_cli.config import load_config
from tele_cli.types import OutputFormat

auth_cli = typer.Typer()


@auth_cli.command()
def auth_login(ctx: typer.Context):
    output_format: utils.fmt.OutputFormat = ctx.obj["fmt"] or OutputFormat.json
    config_file: Path | None = ctx.obj["config_file"]

    # TODO: custom login process
    async def _run() -> bool:
        app = await TeleCLI.create(
            session=None, config=load_config(config_file=config_file)
        )
        me = await app.get_me()
        if not me:
            return False

        print("Hi {}", utils.fmt.format_me(me, OutputFormat.text))
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@auth_cli.command()
def auth_logout(ctx: typer.Context):
    output_format: utils.fmt.OutputFormat = ctx.obj["fmt"] or OutputFormat.json
    config_file: Path | None = ctx.obj["config_file"]

    async def _run() -> bool:
        app = await TeleCLI.create(
            session=None, config=load_config(config_file=config_file)
        )
        async with app.client() as client:
            me = await client.get_me()

        await client.log_out()

        print("Bye: {}", utils.fmt.format_me(me, OutputFormat.text))
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)
