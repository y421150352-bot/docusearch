import bcrypt


MAX_PASSWORD_BYTES = 72


def _password_bytes(password: str) -> bytes:
    if not isinstance(password, str) or not password:
        raise ValueError("password must be a non-empty string")
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError("password must be at most 72 UTF-8 bytes")
    return encoded


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        _password_bytes(password),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            _password_bytes(password),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError, UnicodeError):
        return False
