"""Motor de carreira em memória para os modos Realista e Acelerado.

O módulo mantém o estado explícito: ``pending_event`` é o único evento que a
interface pode exibir, ``event_queue`` guarda os próximos acontecimentos e
``match_state`` existe apenas durante uma partida.  Assim, Flask só delega
ações e nunca decide resultados da simulação.
"""

from __future__ import annotations

from datetime import date, timedelta
import random
from xml.sax.saxutils import escape

from transfer_engine import (
    build_accelerated_transfer_event,
    league_opponent,
    maybe_create_realistic_transfer_event,
    resolve_transfer_decision,
)


TITLE_NAMES = ["Campeonato nacional", "Copa nacional", "Competição continental", "Supercopa"]
VALID_MODES = {"realistic", "accelerated"}
REALISTIC_ACTIVITIES = ("training", "recovery", "match")


def _bounded(value, low=0, high=100):
    return max(low, min(high, value))


def _rng(career):
    """Gera uma fonte pseudoaleatória reprodutível para um estado de carreira."""
    career["random_step"] += 1
    return random.Random(career["random_seed"] + career["random_step"] * 7919)


def _empty_stats():
    return {"matches": 0, "goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0}


def club_stats():
    return {"seasons": 0, **_empty_stats(), "titles": []}


def market_value(player):
    age = player["age"]
    age_factor = 1.20 if age <= 21 else 1.12 if age <= 25 else 1.0 if age <= 29 else .76 if age <= 33 else .45
    performance = player["matches"] * 12_000 + player["goals"] * 85_000 + player["assists"] * 55_000
    technical = max(0, player["overall"] - 40) ** 2 * 14_000
    foot_bonus = 1.12 if player["ambidextrous"] else 1 + player["weak_foot"] / 1000
    return int((150_000 + performance + technical) * age_factor * foot_bonus / 10_000) * 10_000


def update_market_value(player):
    player["market_value"] = market_value(player)
    player["max_overall"] = max(player["max_overall"], player["overall"])
    player["max_market_value"] = max(player["max_market_value"], player["market_value"])


def create_career(name, country, position, dominant_foot, starting_club, mode="realistic", seed=None, club_id=None):
    if mode not in VALID_MODES:
        raise ValueError("Modo de jogo inválido.")
    rng = random.Random(seed)
    today = date.today()
    player = {
        "name": name.strip(), "country": country, "position": position, "dominant_foot": dominant_foot,
        "age": 16, "overall": rng.randint(52, 68), "weak_foot": rng.randint(30, 50),
        "ambidextrous": False, "money": 0, "form": 65, "morale": 68, "fatigue": 18,
        "market_value": 0, "max_overall": 0, "max_market_value": 0, **_empty_stats(),
    }
    update_market_value(player)
    return {
        "status": "active", "mode": mode, "started_year": today.year,
        "calendar": {"year": today.year, "week": 1, "season": 1, "date": today.isoformat()},
        "player": player, "club": starting_club, "club_id": club_id, "clubs": {starting_club: club_stats()}, "titles": [],
        "history": [{"kind": "início", "text": f"Aos 16 anos, você assinou com {starting_club}."}],
        "pending_event": None, "event_queue": [], "match_state": None, "season_stats": _empty_stats(),
        "season_match_count": 0, "season_started": {"age": 16, "overall": player["overall"], "club": starting_club},
        "season_closed": False, "retirement_reason": None,
        "random_seed": seed if seed is not None else rng.randrange(1, 2**31), "random_step": 0, "next_event_id": 1,
    }


def ensure_career_state(career):
    """Completa carreiras em memória criadas antes de uma atualização do motor."""
    career.setdefault("mode", "realistic")
    career.setdefault("event_queue", [])
    career.setdefault("match_state", None)
    career.setdefault("season_stats", _empty_stats())
    career.setdefault("season_match_count", 0)
    career.setdefault("season_closed", False)
    career.setdefault("random_seed", random.randrange(1, 2**31))
    career.setdefault("random_step", 0)
    career.setdefault("next_event_id", 1)
    calendar = career["calendar"]
    if "date" not in calendar:
        calendar["date"] = date.fromisocalendar(calendar["year"], max(1, min(calendar.get("week", 1), 52)), 1).isoformat()
    player = career["player"]
    career.setdefault("season_started", {"age": player["age"], "overall": player["overall"], "club": career["club"]})
    for stats in (career["season_stats"], *career["clubs"].values()):
        for key, value in _empty_stats().items():
            stats.setdefault(key, value)
    for event in [career.get("pending_event"), *career["event_queue"]]:
        if event is not None:
            _assign_event_id(career, event)
    return career


def add_history(career, kind, text):
    career["history"].insert(0, {"kind": kind, "text": text})
    del career["history"][24:]


def _event(event_type, title, text, choices=None, **extra):
    return {"id": None, "type": event_type, "title": title, "text": text,
            "choices": choices or [{"id": "continue", "label": "Continuar"}], **extra}


def _queue_event(career, event):
    _assign_event_id(career, event)
    career["event_queue"].append(event)


def _assign_event_id(career, event):
    if event.get("id") is None:
        event["id"] = f"event-{career['next_event_id']}"
        career["next_event_id"] += 1


def _set_pending_event(career, event):
    _assign_event_id(career, event)
    career["pending_event"] = event


def _promote_next_event(career):
    if career["pending_event"] is None and career["event_queue"]:
        _set_pending_event(career, career["event_queue"].pop(0))


def _advance_calendar(career, days):
    current = date.fromisoformat(career["calendar"]["date"])
    current += timedelta(days=days)
    career["calendar"].update({"date": current.isoformat(), "year": current.year, "week": current.isocalendar().week})


def _player_influence(player):
    return player["overall"] * .50 + player["form"] * .28 + player["morale"] * .12 - player["fatigue"] * .18


def _simulate_match_result(career, is_final=False):
    """Calcula uma partida, mas não toca em estatísticas: aplicação é idempotente."""
    player, rng = career["player"], _rng(career)
    influence = _player_influence(player)
    started = influence + rng.randint(-16, 16) >= 62
    substitute = not started and influence + rng.randint(-10, 20) >= 66
    played = started or substitute
    minutes = 90 if started else (rng.choice((18, 27, 35, 43)) if substitute else 0)
    attacking = 0 if player["position"] == "Goleiro" else .45 if player["position"] in {"Zagueiro", "Lateral esquerdo", "Lateral direito", "Volante"} else 1.0
    involvement = (influence / 100) * (minutes / 90) * attacking
    goals = int(rng.random() < min(.52, .04 + involvement * .20)) if played else 0
    assists = int(rng.random() < min(.42, .03 + involvement * .16)) if played else 0
    yellow = int(played and rng.random() < .12)
    red = int(played and rng.random() < .018)
    own_score = max(0, min(5, int(1.0 + influence / 85 + rng.gauss(0, .85))))
    opponent_score = max(0, min(5, int(1.6 - influence / 190 + rng.gauss(0, .85))))
    if goals and own_score == 0:
        own_score = 1
    competition, opponent = league_opponent(career, rng)
    return {"id": f"match-{career['calendar']['season']}-{career['season_match_count'] + 1}-{career['random_step']}",
            "opponent_id": opponent["id"] if opponent else None,
            "opponent": opponent["name"] if opponent else f"Adversário {career['season_match_count'] + 1}",
            "competition": competition["name"] if competition else "Campeonato nacional",
            "is_final": is_final, "started": started, "substitute": substitute, "played": played,
            "minutes": minutes, "goals": goals, "assists": assists, "yellow_cards": yellow, "red_cards": red,
            "score": [own_score, opponent_score], "applied": False}


def _match_event(match, stage):
    if stage == "pre_match":
        role = "titular" if match["started"] else "no banco"
        return _event("match", "Escalação confirmada", f"{career_club_placeholder(match)} enfrenta {match['opponent']} pelo {match['competition']}. Você começa {role}.", stage=stage)
    if stage == "first_half":
        return _event("match", "A bola rolou", "O primeiro tempo está em andamento. A equipe busca impor o ritmo da partida.", stage=stage)
    if stage == "player_moment":
        if not match["played"]:
            text = "O treinador decidiu não utilizá-lo nesta partida. Continue acompanhando a equipe do banco."
        elif match["goals"]:
            text = "Você apareceu na área e marcou um gol importante para a equipe."
        elif match["assists"]:
            text = "Você encontrou espaço e deu uma assistência decisiva."
        elif match["substitute"]:
            text = f"Você entrou aos {90 - match['minutes']} minutos para ajudar a equipe."
        else:
            text = "Você participou das ações do jogo e ajudou a equipe a manter o controle."
        return _event("match", "Momento de jogo", text, stage=stage)
    if stage == "halftime":
        return _event("match", "Intervalo", "O vestiário ajusta a estratégia para a etapa final.", stage=stage)
    if stage == "second_half":
        card_text = "Você recebeu cartão amarelo e precisará ter cuidado." if match["yellow_cards"] else "A equipe administra os minutos finais com intensidade."
        if match["red_cards"]:
            card_text = "Você recebeu cartão vermelho e deixou a equipe com um jogador a menos."
        return _event("match", "Segundo tempo", card_text, stage=stage)
    score = match["score"]
    return _event("match", "Apito final", f"{career_club_placeholder(match)} {score[0]} × {score[1]} {match['opponent']}. Clique para registrar a partida.", stage="final")


def career_club_placeholder(match):
    return match.get("club", "Seu clube")


def _start_realistic_match(career):
    match = _simulate_match_result(career, is_final=career["season_match_count"] >= 11)
    match["club"] = career["club"]
    career["match_state"] = match
    _set_pending_event(career, _match_event(match, "pre_match"))


def _apply_match(career, match):
    if match["applied"]:
        return False
    match["applied"] = True
    player, stats, season = career["player"], career["clubs"][career["club"]], career["season_stats"]
    if match["played"]:
        for key in _empty_stats():
            value = 1 if key == "matches" else match.get(key, 0)
            player[key] += value
            stats[key] += value
            season[key] += value
        player["form"] = _bounded(player["form"] + match["goals"] * 5 + match["assists"] * 3 - match["red_cards"] * 8 + _rng(career).randint(-3, 3), 30)
        player["fatigue"] = _bounded(player["fatigue"] + 7 + match["minutes"] // 18)
    else:
        player["morale"] = _bounded(player["morale"] - 2, 25)
    career["season_match_count"] += 1
    update_market_value(player)
    return True


def _finish_realistic_match(career):
    match = career["match_state"]
    if not match:
        return
    applied = _apply_match(career, match)
    if applied:
        contribution = []
        if match["goals"]: contribution.append(f"{match['goals']} gol")
        if match["assists"]: contribution.append(f"{match['assists']} assistência")
        suffix = f" ({', '.join(contribution)})" if contribution else ""
        add_history(career, "partida", f"{career['club']} {match['score'][0]} × {match['score'][1]} {match['opponent']}{suffix}.")
        if match["is_final"]:
            _award_final_title(career, match)
    career["match_state"] = None
    return match["is_final"]


def _training_event(periods=1):
    return _event("training", "Plano de treino" if periods == 1 else "Treinos da temporada",
                  "Defina o foco da semana." if periods == 1 else f"Durante a temporada, você teve {periods} períodos de treinamento. Escolha o foco geral do trabalho.",
                  [{"id": "weak_foot", "label": "Treinar a perna fraca"}, {"id": "balanced", "label": "Treino equilibrado"}, {"id": "rest", "label": "Priorizar recuperação"}], periods=periods)


def _recovery_event():
    return _event("recovery", "Recuperação necessária", "A comissão técnica percebe fadiga acumulada antes da próxima sequência.",
                  [{"id": "rest", "label": "Descansar e recuperar"}, {"id": "push", "label": "Manter treino intenso"}])


def _apply_training(career, choice, periods):
    player = career["player"]
    multiplier = max(1, periods // 3)
    if choice == "weak_foot":
        player["weak_foot"] = _bounded(player["weak_foot"] + 2 * multiplier)
        player["fatigue"] = _bounded(player["fatigue"] + 3 * multiplier)
    elif choice == "balanced":
        player["overall"] = _bounded(player["overall"] + multiplier, 38, 99)
        player["form"] = _bounded(player["form"] + 2)
    else:
        player["fatigue"] = _bounded(player["fatigue"] - 10 * multiplier)
        player["morale"] = _bounded(player["morale"] + 2)
    player["ambidextrous"] = player["ambidextrous"] or player["weak_foot"] >= 85
    add_history(career, "treinamento", "Você definiu o foco dos treinamentos." if periods == 1 else f"Você definiu o foco de {periods} períodos de treinamento.")


def _apply_recovery(career, choice):
    player = career["player"]
    if choice == "rest":
        player["fatigue"] = _bounded(player["fatigue"] - 25)
        player["form"] = _bounded(player["form"] + 2)
    else:
        player["overall"] = _bounded(player["overall"] + 1, 38, 99)
        player["fatigue"] = _bounded(player["fatigue"] + 16)
    add_history(career, "decisão", "Você decidiu como lidar com a carga física.")


def _end_season(career):
    if career["season_closed"]:
        return
    career["season_closed"] = True
    player, calendar = career["player"], career["calendar"]
    career["clubs"][career["club"]]["seasons"] += 1
    growth_rng = _rng(career)
    growth = growth_rng.choice([0, 1, 1, 2, 2, 3]) if player["age"] < 29 else growth_rng.choice([-2, -1, 0, 0, 1])
    player["overall"] = _bounded(player["overall"] + growth, 38, 99)
    player["age"] += 1
    next_date = date.fromisoformat(calendar["date"]) + timedelta(days=7)
    calendar.update({"year": next_date.year, "week": 1, "season": calendar["season"] + 1, "date": next_date.isoformat()})
    player["fatigue"] = 18
    player["form"] = max(55, player["form"])
    update_market_value(player)
    add_history(career, "temporada", f"Temporada encerrada. Você agora tem {player['age']} anos.")
    career["season_stats"] = _empty_stats()
    career["season_match_count"] = 0
    career["season_started"] = {"age": player["age"], "overall": player["overall"], "club": career["club"]}
    career["season_closed"] = False
    if player["age"] >= 40:
        retire(career, "O tempo chegou: você se aposentou aos 40 anos.")


def _season_summary_event(career):
    player, start, stats = career["player"], career["season_started"], career["season_stats"]
    summary = {"season": career["calendar"]["season"], "age_start": start["age"], "age_end": player["age"] + 1,
               "overall_start": start["overall"], "overall_end": player["overall"], "club": career["club"],
               "matches": stats["matches"], "goals": stats["goals"], "assists": stats["assists"],
               "titles": [title for title in career["titles"] if title["season"] == career["calendar"]["season"]]}
    titles = ", ".join(item["competition"] for item in summary["titles"]) or "nenhum título"
    text = f"{summary['matches']} jogos, {summary['goals']} gols e {summary['assists']} assistências. Títulos: {titles}."
    return _event("season_summary", f"Resumo da temporada {summary['season']}", text,
                  [{"id": "next_season", "label": "Começar a próxima temporada"}], summary=summary)


def _award_final_title(career, match):
    if match["score"][0] <= match["score"][1]:
        return
    title = {"competition": match["competition"], "season": career["calendar"]["season"], "club": career["club"]}
    career["titles"].append(title)
    career["clubs"][career["club"]]["titles"].append(title["competition"])
    add_history(career, "título", f"Você conquistou {title['competition']} pelo {career['club']}.")


def _simulate_accelerated_season(career):
    """Processa partidas comuns sem cards e deixa só marcos relevantes na fila."""
    for _ in range(18):
        _advance_calendar(career, 5 + _rng(career).randint(1, 3))
        career["player"]["fatigue"] = _bounded(career["player"]["fatigue"] - 4)
        match = _simulate_match_result(career)
        _apply_match(career, match)
    _advance_calendar(career, 7)
    final_match = _simulate_match_result(career, is_final=True)
    final_match["club"] = career["club"]
    _queue_event(career, _training_event(periods=9))
    _queue_event(career, _event("season_final", "Final de campeonato", f"{career['club']} enfrenta {final_match['opponent']} na decisão do {final_match['competition']}.", final_match=final_match))
    transfer_event = build_accelerated_transfer_event(career, _rng(career))
    if transfer_event:
        _queue_event(career, transfer_event)
    _queue_event(career, _season_summary_event(career))
    _promote_next_event(career)


def advance_career(career):
    """Avança uma única ação válida. Nunca pula evento pendente nem duplica estado."""
    if career["status"] != "active" or career["pending_event"]:
        return
    if career["mode"] == "accelerated":
        _simulate_accelerated_season(career)
        return
    activity_index = career.get("realistic_activity_index", 0)
    activity = REALISTIC_ACTIVITIES[activity_index % len(REALISTIC_ACTIVITIES)]
    career["realistic_activity_index"] = activity_index + 1
    _advance_calendar(career, {"training": 3, "recovery": 4, "match": 6}[activity])
    career["player"]["fatigue"] = _bounded(career["player"]["fatigue"] - _rng(career).randint(2, 6))
    if activity != "match":
        transfer_event = maybe_create_realistic_transfer_event(career, _rng(career))
        if transfer_event:
            _set_pending_event(career, transfer_event)
            return
    if activity == "training":
        _set_pending_event(career, _training_event())
    elif activity == "recovery" and career["player"]["fatigue"] >= 52:
        _set_pending_event(career, _recovery_event())
    elif activity == "match":
        _start_realistic_match(career)
    else:
        _set_pending_event(career, _event("recovery", "Dia de recuperação", "A equipe trabalhou a recuperação e se prepara para o próximo compromisso."))


def advance_week(career):
    """Compatibilidade com a rota antiga; o novo motor não avança semanas fixas."""
    advance_career(career)


def resolve_decision(career, choice, event_id=None):
    event = career["pending_event"]
    if not event or (event_id is not None and event_id != event["id"]) or choice not in {item["id"] for item in event["choices"]}:
        return False
    event_type = event["type"]
    if event_type == "match":
        stages = ["pre_match", "first_half", "player_moment", "halftime", "second_half", "final"]
        stage = event["stage"]
        if stage == "final":
            season_finished = _finish_realistic_match(career)
            if season_finished:
                _set_pending_event(career, _season_summary_event(career))
            else:
                career["pending_event"] = None
        else:
            _set_pending_event(career, _match_event(career["match_state"], stages[stages.index(stage) + 1]))
        return True
    if event_type == "season_final":
        match = event["final_match"]
        if _apply_match(career, match):
            _award_final_title(career, match)
            add_history(career, "final", f"Final: {career['club']} {match['score'][0]} × {match['score'][1]} {match['opponent']}.")
    elif event_type == "training":
        _apply_training(career, choice, event.get("periods", 1))
    elif event_type == "recovery":
        _apply_recovery(career, choice)
    elif event_type in {"transfer_market", "transfer_interest"}:
        if not resolve_transfer_decision(career, event, choice):
            return False
    elif event_type == "season_summary":
        career["pending_event"] = None
        _end_season(career)
        return True
    career["pending_event"] = None
    update_market_value(career["player"])
    _promote_next_event(career)
    return True


def retire(career, reason):
    if career["status"] == "finished":
        return
    career["status"] = "finished"
    career["retirement_reason"] = reason
    career["pending_event"] = None
    career["event_queue"] = []
    career["match_state"] = None
    add_history(career, "aposentadoria", reason)


def final_card_svg(career):
    player = career["player"]
    club_lines = [f"{name}: {stats['matches']} J · {stats['goals']} G · {stats['assists']} A · {len(stats['titles'])} títulos" for name, stats in career["clubs"].items()]
    rows = "".join(f'<text x="80" y="{390 + index * 42}" class="row">{escape(line)}</text>' for index, line in enumerate(club_lines[:7]))
    title, country, position = escape(player["name"]), escape(player["country"]), escape(player["position"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760"><style>.bg{{fill:#07150e}}.card{{fill:#123324;stroke:#28523b;stroke-width:2}}.brand{{fill:#b7ef52;font:700 24px Arial}}.name{{fill:#fff;font:800 58px Arial}}.sub{{fill:#b6c8ba;font:24px Arial}}.label{{fill:#a8b9ad;font:700 17px Arial}}.value{{fill:#fff;font:800 32px Arial}}.row{{fill:#eef8f0;font:21px Arial}}</style><rect class="bg" width="1200" height="760"/><rect class="card" x="45" y="40" width="1110" height="680" rx="28"/><text x="80" y="95" class="brand">VIDA DE BOLEIRO · CARD DE CARREIRA</text><text x="80" y="170" class="name">{title}</text><text x="80" y="210" class="sub">{country} · {position} · aposentadoria aos {player['age']} anos</text><text x="80" y="285" class="label">JOGOS</text><text x="80" y="325" class="value">{player['matches']}</text><text x="300" y="285" class="label">GOLS</text><text x="300" y="325" class="value">{player['goals']}</text><text x="500" y="285" class="label">ASSISTÊNCIAS</text><text x="500" y="325" class="value">{player['assists']}</text><text x="760" y="285" class="label">OVR MÁX.</text><text x="760" y="325" class="value">{player['max_overall']}</text><text x="980" y="285" class="label">TÍTULOS</text><text x="980" y="325" class="value">{len(career['titles'])}</text><text x="80" y="365" class="brand">CLUBES</text>{rows}</svg>'''
