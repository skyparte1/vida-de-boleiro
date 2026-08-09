"""Armazenamento efêmero de carreiras: memória do processo, nunca banco de dados."""

import time
import uuid


CAREER_TTL_SECONDS = 60 * 60 * 4
_careers = {}


def create(career):
    cleanup()
    career_id = uuid.uuid4().hex
    _careers[career_id] = {"career": career, "last_seen": time.monotonic()}
    return career_id


def get(career_id):
    cleanup()
    record = _careers.get(career_id)
    if not record:
        return None
    record["last_seen"] = time.monotonic()
    return record["career"]


def discard(career_id):
    _careers.pop(career_id, None)


def cleanup():
    now = time.monotonic()
    expired = [key for key, value in _careers.items() if now - value["last_seen"] > CAREER_TTL_SECONDS]
    for key in expired:
        del _careers[key]
