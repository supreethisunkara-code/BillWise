"""
Identical logic to the cloud version's session_store.py -- only the boto3
resource creation changed, to point at LocalStack via config.boto3_kwargs().
"""
import json
from dataclasses import asdict, dataclass

import boto3

from src.config import SESSIONS_TABLE, boto3_kwargs

_table = boto3.resource("dynamodb", **boto3_kwargs()).Table(SESSIONS_TABLE)


@dataclass
class Session:
    stage: str = "AWAITING_BILL"
    bill_data: dict | None = None
    has_insurance: bool | None = None
    annual_income: float | None = None
    state_name: str | None = None
    employment_type: str | None = None


def get_session(user_id: str) -> Session:
    resp = _table.get_item(Key={"user_id": user_id})
    item = resp.get("Item")
    if not item:
        return Session()
    return Session(**json.loads(item["session_json"]))


def save_session(user_id: str, session: Session) -> None:
    _table.put_item(Item={"user_id": user_id, "session_json": json.dumps(asdict(session))})


def reset_session(user_id: str) -> None:
    _table.delete_item(Key={"user_id": user_id})