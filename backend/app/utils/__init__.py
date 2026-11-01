import uuid
import datetime

def uid(length: int = 12) -> str:
    return str(uuid.uuid4())[:length]

def now_iso() -> str:
    return datetime.datetime.now().isoformat()
