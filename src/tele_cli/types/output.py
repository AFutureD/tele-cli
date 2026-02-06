from enum import Enum


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    toon = "toon"


class OutputOrder(str, Enum):
    asc = "asc"
    desc = "desc"
