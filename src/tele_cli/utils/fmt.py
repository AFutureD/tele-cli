import json

import telethon
import toon_format
from telethon.tl.tlobject import _json_default

from tele_cli.types import OutputFormat


def format_me(me: telethon.types.User, fmt: None | OutputFormat = None) -> str:
    fmt: OutputFormat = fmt or OutputFormat.json
    match fmt:
        case OutputFormat.text:
            return telethon.utils.get_display_name(me)
        case OutputFormat.json:
            return me.to_json()
        case OutputFormat.toon:
            return toon_format.encode(me.to_dict())


def format_dialog(
    dialog: telethon.custom.Dialog, fmt: None | OutputFormat = None
) -> str:
    return ""


def format_dialog_list(
    dialog_list: list[telethon.custom.Dialog], fmt: None | OutputFormat = None
) -> str:
    obj_list = [item.dialog.to_dict() for item in dialog_list]

    fmt: OutputFormat = fmt or OutputFormat.json
    match fmt:
        case OutputFormat.text:
            raise NotImplementedError("Not Supported Format For Dialog")
        case OutputFormat.json:
            return json.dumps(obj_list, default=_json_default)
        case OutputFormat.toon:
            raise NotImplementedError("Not Supported Format For Dialog")
