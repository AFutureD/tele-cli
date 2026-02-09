from enum import Enum


class EntityType(str, Enum):
    username = "username"
    phone = "phone"
    peer_id = "peer_id"
