"""Interesse e transferências baseados nos clubes permanentes do SQLite."""

from __future__ import annotations

from datetime import date, timedelta

from database import (
    get_club,
    get_clubs_by_competition,
    get_clubs_with_competition,
    get_current_competition_for_club,
)
from github_logo_urls import club_logo_url


INTERNATIONAL_WINDOW_MONTHS = {1, 7, 8, 12}
REALISTIC_TRANSFER_COOLDOWN_DAYS = 42


def _career_date(career):
    return date.fromisoformat(career["calendar"]["date"])


def _database_season(career):
    return career["calendar"]["year"]


def current_competition(career):
    club_id = career.get("club_id")
    if not club_id:
        return None
    return (
        get_current_competition_for_club(club_id, _database_season(career))
        or get_current_competition_for_club(club_id, 2026)
    )


def league_opponent(career, rng):
    """Seleciona um adversário real da competição atual, sem incluir o próprio clube."""
    competition = current_competition(career)
    if not competition:
        return None, None
    participants = get_clubs_by_competition(competition["id"], 2026)
    options = [club for club in participants if club["id"] != career.get("club_id")]
    return competition, (rng.choice(options) if options else None)


def is_international_window(career):
    """Abstração simples para futuras janelas específicas por federação."""
    return _career_date(career).month in INTERNATIONAL_WINDOW_MONTHS


def can_complete_transfer(career, candidate):
    current = get_club(career.get("club_id")) if career.get("club_id") else None
    if not current:
        return False
    return current["country_code"] == candidate["country_code"] or is_international_window(career)


def score_transfer_destination(career, current_club, candidate_club, context=None):
    """Pontua a plausibilidade de um destino sem sorteio uniforme.

    O score combina nível atual, momento, idade e distância esportiva/financeira
    entre os clubes. Resultados menores ou iguais a zero são descartados.
    """
    context = context or {}
    player = career["player"]
    current_competition = context.get("current_competition")
    candidate_competition = context.get("candidate_competition")
    if candidate_club["id"] == current_club["id"] or not candidate_competition:
        return 0

    recent_output = career["season_stats"]["goals"] * 2 + career["season_stats"]["assists"]
    player_level = player["overall"] + (player["form"] - 60) * .18 + min(8, recent_output * .25)
    destination_level = candidate_club["strength"] * .62 + candidate_club["reputation"] * .38
    fit = 66 - abs(destination_level - player_level) * 1.35

    progression = candidate_club["reputation"] - current_club["reputation"]
    desired_progression = 13 if player["age"] <= 23 else 6 if player["age"] <= 30 else -5
    trajectory = 26 - abs(progression - desired_progression) * .9

    tier_bonus = 0
    if current_competition and current_competition["tier"] and candidate_competition["tier"]:
        tier_bonus = (current_competition["tier"] - candidate_competition["tier"]) * 7
    finance = (candidate_club["financial_power"] - current_club["financial_power"]) * .18
    form_bonus = max(-5, min(9, (player["form"] - 60) * .22))
    veteran_adjustment = (candidate_club["financial_power"] * .10) if player["age"] >= 31 else 0
    giant_penalty = 48 if candidate_club["reputation"] >= 78 and player["overall"] < 76 else 0
    poor_fit_penalty = 20 if candidate_club["strength"] - player_level > 24 else 0
    international_bonus = 3 if candidate_club["country_code"] != current_club["country_code"] else 5

    return max(0, round(fit + trajectory + tier_bonus + finance + form_bonus + veteran_adjustment + international_bonus - giant_penalty - poor_fit_penalty, 2))


def _candidate_payload(club, competition, score, can_complete):
    return {
        "club_id": club["id"], "name": club["name"], "country": club["country"],
        "country_code": club["country_code"], "competition": competition["name"],
        "competition_id": competition["id"], "tier": competition["tier"], "logo": club["logo"],
        "logo_url": club_logo_url(club["logo"]),
        "score": score, "can_complete": can_complete,
    }


def ranked_transfer_candidates(career, rng, limit=None, completable_only=False):
    """Forma uma lista ponderada de clubes reais com competição válida."""
    current = get_club(career.get("club_id")) if career.get("club_id") else None
    competition = current_competition(career)
    if not current:
        return []

    ranked = []
    candidates = get_clubs_with_competition(_database_season(career)) or get_clubs_with_competition(2026)
    for candidate in candidates:
        if candidate["id"] == current["id"]:
            continue
        candidate_competition = {
            "id": candidate["competition_id"], "name": candidate["competition_name"],
            "type": candidate["competition_type"], "tier": candidate["competition_tier"],
        }
        complete = current["country_code"] == candidate["country_code"] or is_international_window(career)
        if completable_only and not complete:
            continue
        score = score_transfer_destination(career, current, candidate, {
            "current_competition": competition, "candidate_competition": candidate_competition,
        })
        if score >= 16:
            ranked.append(_candidate_payload(candidate, candidate_competition, score, complete))

    ranked.sort(key=lambda item: item["score"], reverse=True)
    if not ranked:
        return []
    selected = []
    pool = ranked[:80]
    wanted = limit if limit is not None else 1
    while pool and len(selected) < wanted:
        candidate = rng.choices(pool, weights=[item["score"] ** 1.6 for item in pool], k=1)[0]
        selected.append(candidate)
        pool.remove(candidate)
    return selected


def _event(event_type, title, text, choices, **extra):
    return {"id": None, "type": event_type, "title": title, "text": text, "choices": choices, **extra}


def build_accelerated_transfer_event(career, rng):
    season = career["calendar"]["season"]
    if career.get("transfer_event_season") == season:
        return None
    career["transfer_event_season"] = season
    candidates = ranked_transfer_candidates(career, rng, limit=rng.randint(2, 6), completable_only=True)
    if len(candidates) < 2:
        return None
    choices = [{"id": f"accept:{item['club_id']}", "label": f"Assinar com {item['name']}"} for item in candidates]
    choices.append({"id": "stay", "label": "Continuar no clube atual"})
    return _event(
        "transfer_market", "Mercado de transferências", "Ao fim da temporada, estes clubes demonstraram interesse concreto em você.",
        choices, transfer_candidates=candidates, transfer_stage="proposal", season=season,
    )


def maybe_create_realistic_transfer_event(career, rng):
    """Gera uma abordagem rara fora de partidas, respeitando cooldown."""
    today = _career_date(career)
    cooldown = career.get("transfer_cooldown_until")
    if cooldown and today < date.fromisoformat(cooldown):
        return None
    player = career["player"]
    recent_output = career["season_stats"]["goals"] + career["season_stats"]["assists"]
    chance = min(.12, .012 + max(0, player["form"] - 64) * .0017 + min(.03, recent_output * .002) + max(0, player["overall"] - 65) * .001)
    if rng.random() >= chance:
        return None
    candidates = ranked_transfer_candidates(career, rng, limit=1, completable_only=False)
    if not candidates:
        return None
    candidate = candidates[0]
    career["transfer_cooldown_until"] = (today + timedelta(days=REALISTIC_TRANSFER_COOLDOWN_DAYS)).isoformat()
    if candidate["can_complete"] and candidate["score"] >= 72:
        stage = "proposal"
        choices = [{"id": f"accept:{candidate['club_id']}", "label": f"Aceitar proposta de {candidate['name']}"}, {"id": "reject", "label": "Recusar a proposta"}]
        title = "Proposta de transferência"
        text = f"{candidate['name']} apresentou uma proposta para contratá-lo."
    elif candidate["can_complete"]:
        stage = "inquiry"
        choices = [{"id": "acknowledge", "label": "Ouvir a sondagem"}, {"id": "reject", "label": "Encerrar o contato"}]
        title = "Sondagem no mercado"
        text = f"{candidate['name']} procurou seu entorno para entender sua situação."
    else:
        stage = "watching"
        choices = [{"id": "acknowledge", "label": "Manter o foco"}, {"id": "reject", "label": "Ignorar o interesse"}]
        title = "Clube observando você"
        text = f"{candidate['name']} acompanha suas atuações, mas uma transferência internacional só poderá ocorrer na próxima janela."
    return _event("transfer_interest", title, text, choices, transfer_candidates=[candidate], transfer_stage=stage)


def _history(career, kind, text):
    career["history"].insert(0, {"kind": kind, "text": text})
    del career["history"][24:]


def resolve_transfer_decision(career, event, choice):
    """Aplica uma escolha de transferência já validada pelo motor de eventos."""
    candidates = {item["club_id"]: item for item in event.get("transfer_candidates", [])}
    if choice == "stay":
        _history(career, "transferência", f"Você decidiu permanecer no {career['club']}.")
        return True
    if choice in {"acknowledge", "reject"}:
        action = "manteve o foco" if choice == "acknowledge" else "recusou o contato"
        _history(career, "transferência", f"Você {action} após o interesse de {event['transfer_candidates'][0]['name']}.")
        return True
    if not choice.startswith("accept:"):
        return False
    try:
        club_id = int(choice.split(":", 1)[1])
    except ValueError:
        return False
    candidate = candidates.get(club_id)
    if not candidate or not candidate["can_complete"]:
        return False
    club = get_club(club_id)
    if not club or club["id"] == career.get("club_id"):
        return False
    old_club = career["club"]
    career["club_id"] = club["id"]
    career["club"] = club["name"]
    career["clubs"].setdefault(club["name"], {"seasons": 0, "matches": 0, "goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0, "titles": []})
    career["player"]["morale"] = min(100, career["player"]["morale"] + 6)
    _history(career, "transferência", f"Você deixou {old_club} para atuar no {club['name']}.")
    return True
