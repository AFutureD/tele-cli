from datetime import datetime
import json

import telethon
import toon_format
from telethon.tl.tlobject import _json_default

from tele_cli.types import OutputFormat
from tele_cli.types.session import SessionInfo
import arrow


def format_me(me: telethon.types.User, fmt: None | OutputFormat = None) -> str:
    output_fmt = fmt or OutputFormat.text
    match output_fmt:
        case OutputFormat.text:
            return telethon.utils.get_display_name(me)
        case OutputFormat.json:
            return json.dumps(me.to_json(), ensure_ascii=False)
        case OutputFormat.toon:
            return toon_format.encode(me.to_dict())


def _format_dialog_to_str(x: telethon.custom.Dialog) -> str:
    """
    format: "[<Dialog Type>.<UI State>.<Dialog State>] <Unread Count> <Name> [entity id]"
    """

    have_unread: bool = x.unread_count > 0
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

    mute_until = x.dialog.notify_settings.mute_until
    is_mute = mute_until is not None and mute_until > datetime.now().astimezone()
    mute = "M" if is_mute else "-"

    unread = f"[{unread_color}]{(str(x.unread_count) if have_unread else ' '):<3}[/{unread_color}]"

    message_line = ""
    message_prefix_space_count = 12
    if x.message.message and not x.message.out and have_unread and not is_mute:
        unread_message = "".join([f"{' ' * message_prefix_space_count}| " + m for m in x.message.message.splitlines(keepends=True)])
        message_line = "\n" + f"{' ' * message_prefix_space_count}* id: {x.message.id} at {x.message.date} \n" + unread_message

    return f"[{_color}]" + f"[{dialog_type}.{state}.{mute}] {unread} [{x.id:<10}] {x.name} " + message_line + f"[/{_color}]"


def format_dialog_list(dialog_list: list[telethon.custom.Dialog], fmt: None | OutputFormat = None) -> str:
    output_fmt = fmt or OutputFormat.text
    match output_fmt:
        case OutputFormat.text:
            return "\n".join([_format_dialog_to_str(x) for x in sorted(dialog_list, key=lambda x: x.archived)])

        case OutputFormat.json:

            def f(x: telethon.custom.Dialog) -> dict:
                return {
                    "_": "Dialog",
                    "pin": x.pinned,
                    "folder_id": x.folder_id,
                    "name": x.name,
                    "date": x.date,
                    "message": x.message.to_dict(),
                    "entity": x.entity.to_dict(),
                    "unread_count": x.unread_count,
                }

            obj_list = [f(item) for item in dialog_list]
            return json.dumps(obj_list, default=_json_default, ensure_ascii=False)

        case OutputFormat.toon:
            raise NotImplementedError("Not Supported Format For Dialog")


def _format_message_to_str(msg: telethon.types.Message, relative_time: bool = True) -> str:
    sender_name = "unknown"
    if msg.out:
        sender_name = "me"
    elif msg.sender:
        sender_name = f"{telethon.utils.get_display_name(msg.sender)} (id: {msg.sender.id})"

    if relative_time:
        date_str = arrow.get(msg.date).humanize() if msg.date else "?"
    else:
        date_str = msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "?"

    text = msg.message or ""
    message = "".join(["  " + x for x in text.splitlines(keepends=True)])

    return f"* {msg.id} ({date_str}) - {sender_name}\n" + "\n" + message + "\n"


def format_message_list(messages: list[telethon.types.Message], fmt: None | OutputFormat = None) -> str:
    output_fmt = fmt or OutputFormat.text
    match output_fmt:
        case OutputFormat.text:
            return "\n".join([_format_message_to_str(msg) for msg in messages])
        case OutputFormat.json:
            obj_list = [msg.to_dict() for msg in messages]
            return json.dumps(obj_list, default=_json_default, ensure_ascii=False)
        case OutputFormat.toon:
            raise NotImplementedError("Not Supported Format For Message List")


def _format_session_info_to_str(x: SessionInfo) -> str:
    username = f"@{x.user_name}" if x.user_name else "unknown"
    return f"{x.user_id: <12} {x.user_display_name or 'unknown'} ({username}) {x.session_name}"


def format_session_info_list(session_info_list: list[SessionInfo], fmt: None | OutputFormat = None) -> str:
    output_fmt = fmt or OutputFormat.text

    match output_fmt:
        case OutputFormat.text:
            return "\n".join([_format_session_info_to_str(obj) for obj in session_info_list])
        case OutputFormat.json:
            obj_list = [item.model_dump(mode="json") for item in session_info_list]
            return json.dumps(obj_list, ensure_ascii=False)
        case OutputFormat.toon:
            raise NotImplementedError("Not Supported Format For SessionInfo List")
