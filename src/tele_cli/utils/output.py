from typing import Literal
import rich
import builtins

from ..types import OutputFormat


def print(
    *values: object,
    sep: str = " ",
    end: str = "\n",
    flush: Literal[False] = False,
    fmt: OutputFormat = OutputFormat.text,
) -> None:
    match fmt:
        case OutputFormat.json:
            builtins.print(*values, sep=sep, end=end, flush=flush)
        case _:
            rich.print(*values, sep=sep, end=end, flush=flush)
