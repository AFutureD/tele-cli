import json

import rich
from rich.text import Text
import telethon
import toon_format
from telethon.tl.tlobject import _json_default

from tele_cli.types import OutputFormat
from tele_cli.types.session import SessionInfo


def format_me(me: telethon.types.User, fmt: None | OutputFormat = None) -> str:
    fmt: OutputFormat = fmt or OutputFormat.text
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

def _format_dialog_to_str(x: telethon.custom.Dialog) -> str:
    have_unread: bool = x.unread_count > 0
    unread = str(x.unread_count) if have_unread else ""
    unread_color = "red" if have_unread else "not"
    _color = "white" if x.archived else "not"

    state = "-"
    if x.pinned:
        state = "P"
    if x.archived:
        state = "A"

    dialog_type = "?"
    if x.is_user:
        dialog_type = "U"
    if x.is_group:
        dialog_type = "G"
    if x.is_channel:
        dialog_type = "C"

    message_line = ""
    if x.message.message and not x.message.out and have_unread:
        unread_message = "".join([f"{' '*6}| "+m for m in x.message.message.splitlines(keepends=True)])
        message_line = "\n" + f"{' '*6}* id: {x.message.id} at {x.message.date} " "\n" + unread_message

    return (f"[{_color}]{state} [{unread_color}]{unread:<3}[/{unread_color}] [{dialog_type}] {x.name}<{x.entity.id}> [/{_color}]"
            +message_line)


def format_dialog_list(
    dialog_list: list[telethon.custom.Dialog], fmt: None | OutputFormat = None
) -> str:

    fmt: OutputFormat = fmt or OutputFormat.text
    match fmt:
        case OutputFormat.text:
            return "\n".join([
                _format_dialog_to_str(x)
                for x in sorted(dialog_list, key=lambda x: x.archived)
            ])

        case OutputFormat.json:
            def f(x: telethon.custom.Dialog) -> dict:
                return {
                    '_': 'Dialog',
                    "pin": x.pinned,
                    "folder_id": x.folder_id,
                    'name': x.name,
                    'date': x.date,
                    'message': x.message.to_dict(),
                    'entity': x.entity.to_dict(),
                    'unread_count': x.unread_count,
                }

            obj_list = [f(item) for item in dialog_list]
            return json.dumps(obj_list, default=_json_default, ensure_ascii=False)

        case OutputFormat.toon:
            raise NotImplementedError("Not Supported Format For Dialog")


def format_session_info_list(
    session_info_list: list[SessionInfo], fmt: None | OutputFormat = None
) -> str:
    fmt: OutputFormat = fmt or OutputFormat.text

    match fmt:
        case OutputFormat.text:
            return "\n".join(
                [
                    f"{obj.user_id: <12} \
{obj.user_display_name or 'unknown'} \
({'@' + obj.user_name if obj.user_name else 'unknown'}) \
{obj.session_name}"
                    for obj in session_info_list
                ]
            )
        case OutputFormat.json:
            obj_list = [item.model_dump(mode="json") for item in session_info_list]
            return json.dumps(obj_list, ensure_ascii=False)
        case OutputFormat.toon:
            raise NotImplementedError("Not Supported Format For SessionInfo List")
