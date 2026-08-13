"""Encerramentos oficiais e idempotentes da carreira."""

from datetime import date


def _add_history(career, kind, text):
    career["history"].insert(0, {"kind": kind, "text": text})
    del career["history"][24:]


def _close_active_career(career):
    if career.get("status") != "active":
        return False
    career["pending_event"] = None
    career["event_queue"] = []
    career["match_state"] = None
    career["scheduled_follow_ups"] = []
    return True


def retire_career(career, reason):
    """Encerra a carreira por aposentadoria, sem confundi-la com falecimento."""
    if not _close_active_career(career):
        return False
    career["status"] = "finished"
    career["retirement_reason"] = reason
    _add_history(career, "aposentadoria", reason)
    return True


def die(career, reason, event_id=None):
    """Encerra definitivamente a carreira por falecimento, uma única vez."""
    if not _close_active_career(career):
        return False
    player = career["player"]
    career["status"] = "deceased"
    career["death"] = {
        "reason": reason,
        "date": career.get("calendar", {}).get("date", date.today().isoformat()),
        "age": player["age"],
        "event_id": event_id,
    }
    _add_history(career, "falecimento", f"Falecimento aos {player['age']} anos: {reason}")
    return True


def apply_terminal_effect(career, terminal, event_id=None):
    """Aplica o encerramento declarativo suportado por eventos narrativos."""
    if not isinstance(terminal, dict):
        return False
    reason = terminal.get("reason") or "A carreira foi encerrada."
    if terminal.get("type") == "retirement":
        return retire_career(career, reason)
    if terminal.get("type") == "death":
        return die(career, reason, event_id)
    return False
