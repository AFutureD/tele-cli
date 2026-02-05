from dataclasses import dataclass
from pathlib import Path

from tele_cli.types import OutputFormat


@dataclass
class SharedArgs:
    fmt: OutputFormat
    config_file: Path | None
    session: str | None
