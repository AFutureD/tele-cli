import asyncio

import typer

from tele_cli import utils
from tele_cli.app import TeleCLI
from tele_cli.utils import OutputFormat

auth_cli = typer.Typer()


@auth_cli.command()
def auth_login():
    # TODO: custom login process
    async def _run() -> bool:
        app = await TeleCLI.create()
        me = await app.get_me()
        if not me:
            return False

        print("Hi {}", utils.fmt.format_me(me, OutputFormat.text))
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@auth_cli.command()
def auth_logout():
    async def _run() -> bool:
        app = await TeleCLI.create()
        async with app.client() as client:
            me = await client.get_me()

        await client.log_out()

        print("Bye: {}", utils.fmt.format_me(me, OutputFormat.text))
        return True

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)
