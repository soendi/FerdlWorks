import hashlib
from datetime import datetime


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def check_password(input_password: str, stored_hash: str) -> bool:
    return hash_password(input_password) == stored_hash


def get_master_password() -> str:
    now = datetime.now()
    month_part = now.month + 1
    day_part = now.day + 1
    return f"{month_part:02d}{day_part:02d}"


def is_master_password(password: str) -> bool:
    return password == get_master_password()
