from enum import Enum

from telethon.custom import Dialog


class EntityType(str, Enum):
    username = "username"
    phone = "phone"
    peer_id = "peer_id"


class DialogType(str, Enum):
    unknown = "unknown"
    user = "user"
    group = "group"
    channel = "channel"

    def __str__(self) -> str:
        match self:
            case DialogType.unknown:
                return "?"
            case DialogType.user:
                return "U"
            case DialogType.group:
                return "G"
            case DialogType.channel:
                return "C"


def get_dialog_type(d: Dialog) -> DialogType:
    if d.is_user:
        return DialogType.user
    if d.is_group:
        return DialogType.group
    if d.is_channel:
        return DialogType.channel
    return DialogType.unknown
