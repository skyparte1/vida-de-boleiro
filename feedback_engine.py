"""Feedback transitório e apresentável para a área principal da carreira."""

from __future__ import annotations


_PLAYER_LABELS = {
    "overall": "OVR atual", "current_overall": "OVR atual", "morale": "Moral",
    "form": "Forma", "fatigue": "Fadiga", "weak_foot": "Perna fraca",
}
_REPUTATION_LABELS = {
    "locker_room": "Vestiário", "fans": "Torcida", "media": "Mídia",
    "discipline": "Disciplina", "controversy": "Controvérsia", "leadership": "Liderança",
}


def contextual_text(text, career, **values):
    """Resolve somente placeholders conhecidos sem falhar em textos legados."""
    context = {"player_name": career["player"]["name"], "club": career.get("club", "clube"), **values}
    try:
        return (text or "").format_map(context)
    except (KeyError, ValueError, IndexError):
        return text or ""


def feedback_snapshot(career):
    """Captura somente valores compreensíveis para comparação posterior."""
    player = career["player"]
    return {
        "player": {key: player.get(key) for key in _PLAYER_LABELS},
        "reputation": {key: career.get("reputation", {}).get(key, 0) for key in _REPUTATION_LABELS},
        "development_points": career.get("development_points", 0),
        "squad_status": career.get("squad_status"),
        "club": career.get("club"),
    }


def _changes(before, career):
    after = feedback_snapshot(career)
    changes = []
    for group, labels in (("player", _PLAYER_LABELS), ("reputation", _REPUTATION_LABELS)):
        for key, label in labels.items():
            old, new = before[group].get(key), after[group].get(key)
            if old != new:
                changes.append({"key": key, "label": label, "before": old, "after": new, "delta": new - old})
    old, new = before["development_points"], after["development_points"]
    if old != new:
        changes.append({"key": "development_points", "label": "Desenvolvimento", "before": old, "after": new, "delta": new - old})
    if before["squad_status"] != after["squad_status"]:
        changes.append({"key": "squad_status", "label": "Status no elenco", "before": before["squad_status"], "after": after["squad_status"], "delta": None})
    return changes


def set_pending_feedback(career, kind, title, text, before, *, terminal=False, extra=None):
    """Sobrescreve apenas o feedback que acabou de ser produzido pela ação atual."""
    feedback = {
        "kind": kind, "title": title, "text": text, "changes": _changes(before, career),
        "terminal": terminal,
    }
    if extra:
        feedback.update(extra)
    career["pending_feedback"] = feedback
    return feedback


def consume_pending_feedback(career):
    feedback = career.get("pending_feedback")
    if not feedback:
        return False
    career["pending_feedback"] = None
    return True
