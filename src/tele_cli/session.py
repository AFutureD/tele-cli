import uuid
from pathlib import Path

from telethon.sessions import SQLiteSession

from tele_cli.shared import get_app_user_defualt_dir

from .types import CurrentSessionPathNotValidError
from .types.session import SessionInfo


class TGSession(SQLiteSession):
    def get_possible_user_entity(self) -> tuple[int, str, int, str]:
        """
        Treat the earliest entity as a user.
        IDs greater than 0 indicate a user.

        :return: tuple of possible user entity
        """

        return self._execute("select id, username, phone, name from entities where id > 0 ORDER BY date ASC limit 1")

    async def get_info(self) -> SessionInfo | None:
        user_entity = self.get_possible_user_entity()
        if not user_entity:
            return None

        session_path = Path(self.filename)
        id, username, phone, name = user_entity
        return SessionInfo(
            path=session_path,
            session_name=session_path.stem,
            user_id=id,
            user_name=username,
            user_phone=phone,
            user_display_name=name,
        )


def get_app_session_folder() -> Path:
    ret = get_app_user_defualt_dir() / "sessions"
    ret.mkdir(parents=True, exist_ok=True)
    return ret


def get_app_session_current() -> Path:
    return get_app_session_folder() / "Current.session"


def _get_session_path(session_name: str | None, with_current: bool) -> Path:
    if session_name:
        return get_app_session_folder() / session_name

    current = get_app_session_current()
    if with_current and current.exists():
        return current

    return get_app_session_folder() / str(uuid.uuid4())


def load_session(session_name: str | None, with_current: bool = True) -> TGSession:
    session_path = _get_session_path(session_name=session_name, with_current=with_current)
    return TGSession(str(session_path))


def session_ensure_current_valid(session: object = None) -> None:
    """
    check if current session path is symlink, throw error if not.
    check if current session is point to a valid session path, and remove if not valid.
    create a current session path if it does not exist and point to given session path.

    notice: this function will not switch to the give session if current session has pointed to a valid session.
    """

    path = get_app_session_current()
    if path.exists() and not path.is_symlink():
        raise CurrentSessionPathNotValidError()

    # skip, if a current session is exists
    # notice: we do not validate session's state for now.
    if path.exists():
        return

    # force unlink
    path.unlink(missing_ok=True)

    if not isinstance(session, TGSession):
        return

    # before perform create the symlink of current session path,
    # we should check the session path is valid.
    session_path = Path(session.filename)
    if not session_path.exists():
        return

    path.symlink_to(session_path)


async def list_session_list() -> list[TGSession]:
    folder = get_app_session_folder()
    session_path_list = [item for item in folder.glob("*.session") if not item.is_symlink() and item.is_file()]
    session_list = [TGSession(str(session_path)) for session_path in session_path_list]
    return session_list


def session_switch(session: TGSession) -> None:
    session_path = Path(session.filename)

    if not session_path.exists():
        return

    path = get_app_session_current()
    path.unlink(missing_ok=True)

    path.symlink_to(session_path)
