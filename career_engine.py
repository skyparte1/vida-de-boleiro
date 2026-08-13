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

from career_lifecycle import retire_career
from competition_engine import (
    competition_context,
    competition_summary,
    current_league_state,
    finalize_country_season,
    initialize_competition_world,
    simulate_league_round,
    simulate_remaining_competitions,
    start_new_competition_season,
)
from database import get_club
from feedback_engine import feedback_snapshot, set_pending_feedback
from transfer_engine import (
    build_accelerated_transfer_event,
    league_opponent,
    maybe_create_realistic_transfer_event,
    resolve_transfer_decision,
)
from narrative_engine import (
    due_follow_up_events,
    event_is_eligible,
    maybe_create_narrative_event,
    normalize_narrative_state,
    resolve_narrative_event,
)


TITLE_NAMES = ["Campeonato nacional", "Copa nacional", "Competição continental", "Supercopa"]
VALID_MODES = {"realistic", "accelerated"}
REALISTIC_ACTIVITIES = ("training", "recovery", "match")
SQUAD_STATUSES = ("out_of_plans", "reserve", "rotation", "starter", "key_player", "star")
SQUAD_STATUS_LABELS = {
    "out_of_plans": "Fora dos planos", "reserve": "Reserva", "rotation": "Rotação",
    "starter": "Titular", "key_player": "Destaque", "star": "Estrela",
}
PLAYER_ACTIONS = {
    "training": {
        "finishing": {"label": "Finalização", "outcomes": [{"weight": 70, "result_title": "Sessão produtiva", "result_text": "Você trabalha bastante a finalização e termina a sessão cansado, mas satisfeito com o rendimento.", "effects": {"development_points": 3, "player": {"fatigue": 10}}}, {"weight": 20, "result_title": "Treino excelente", "result_text": "Tudo parece encaixar durante a sessão, e você termina o treino se sentindo muito mais confiante.", "summary": ["Desenvolvimento +5", "Moral +2"], "effects": {"development_points": 5, "player": {"fatigue": 10, "morale": 2}}}, {"weight": 10, "result_title": "Dia difícil", "result_text": "O treino não rende como esperado e o esforço físico parece maior do que o benefício obtido.", "summary": ["Desenvolvimento +1", "Fadiga +14"], "effects": {"development_points": 1, "player": {"fatigue": 14}}}]},
        "passing": {"label": "Passe", "result_title": "Trabalho de passe", "result_text": "Você repete movimentos e leituras de jogo até deixar a bola circular com mais naturalidade.", "development": 3, "fatigue": 9},
        "physical": {"label": "Físico", "result_title": "Carga física", "result_text": "A sessão exige bastante do corpo, mas ajuda a construir uma base para a sequência da temporada.", "development": 3, "fatigue": 12},
        "defending": {"label": "Defesa", "result_title": "Ajustes defensivos", "result_text": "Você trabalha posicionamento e tempo de bote para responder melhor aos próximos desafios.", "development": 3, "fatigue": 10},
        "general": {"label": "Treino geral", "result_title": "Treino completo", "result_text": "Você divide a atenção entre vários fundamentos e mantém o ritmo de evolução.", "development": 2, "fatigue": 8},
    },
    "rest": {"rest": {"label": "Descansar", "outcomes": [{"weight": 80, "result_title": "Dia de recuperação", "result_text": "Você aproveita o tempo livre para recuperar o corpo e aliviar o desgaste acumulado.", "effects": {"player": {"fatigue": -18, "morale": 2}}}, {"weight": 20, "result_title": "Energias renovadas", "result_text": "O período de descanso faz muito bem, e você retorna à rotina se sentindo recuperado.", "summary": ["Fadiga -24", "Moral +4"], "effects": {"player": {"fatigue": -24, "morale": 4}}}]}},
    "career": {"review": {"label": "Revisar sua situação no clube", "result_title": "Panorama da carreira", "result_text": "Você observa seu espaço no elenco e entende melhor o momento que vive no clube.", "effects": {}}},
    "locker_room": {
        "talk": {"label": "Conversar com o elenco", "result_title": "Boa conversa", "result_text": "Sua postura é bem recebida e o ambiente do grupo fica um pouco mais leve.", "effects": {"reputation": {"locker_room": 3}}},
        "help": {"label": "Ajudar um companheiro", "result_title": "Gesto valorizado", "result_text": "Você dá apoio a um companheiro em um momento necessário e fortalece a relação dentro do elenco.", "effects": {"reputation": {"locker_room": 4, "leadership": 1}}},
        "lead": {"label": "Tentar assumir liderança", "result_title": "Voz ativa", "result_text": "Você se posiciona mais no grupo e deixa clara sua intenção de participar das decisões do vestiário.", "effects": {"reputation": {"leadership": 3, "locker_room": -1}, "behavior": {"authoritarian_choices": 1}}},
    },
    "media": {
        "interview": {"label": "Dar entrevista", "result_title": "Boa repercussão", "result_text": "Sua entrevista é recebida com atenção e mantém seu nome em circulação fora de campo.", "effects": {"reputation": {"media": 3, "fans": 1}}},
        "avoid": {"label": "Evitar a imprensa", "result_title": "Discrição calculada", "result_text": "Você prefere não alimentar manchetes e deixa que o futebol fale por você desta vez.", "effects": {"reputation": {"media": -1, "discipline": 1}}},
        "fans": {"label": "Interagir com torcedores", "result_title": "Perto da torcida", "result_text": "Você tira um tempo para retribuir o carinho de quem acompanha sua trajetória.", "effects": {"reputation": {"fans": 3, "media": 1}}},
    },
    "personal": {
        "hair": {"label": "Mudar visual", "result_title": "Novo visual", "result_text": "Você muda o visual e chega aos próximos compromissos sentindo que renovou a rotina.", "effects": {"reputation": {"fans": 2, "media": 1}}},
        "tattoo": {"label": "Fazer tatuagem", "min_age": 18, "result_title": "Marca pessoal", "result_text": "Você escolhe uma tatuagem para registrar uma fase importante fora dos gramados.", "effects": {"reputation": {"fans": 1}}},
        "study": {"label": "Estudar", "result_title": "Tempo para aprender", "result_text": "Você separa um período para os estudos e volta à rotina com a cabeça mais organizada.", "effects": {"reputation": {"discipline": 3}, "morale": 1}},
        "socialize": {"label": "Sair / socializar", "result_title": "Tempo fora do campo", "result_text": "Você encontra amigos e dá uma pausa na pressão do futebol antes de retomar a rotina.", "effects": {"reputation": {"fans": 1}, "morale": 3, "fatigue": 4}},
    },
}


def _bounded(value, low=0, high=100):
    return max(low, min(high, value))


def _rng(career):
    """Gera uma fonte pseudoaleatória reprodutível para um estado de carreira."""
    career["random_step"] += 1
    return random.Random(career["random_seed"] + career["random_step"] * 7919)


def _empty_stats():
    return {"matches": 0, "goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0}


def _club_strength(career):
    club = get_club(career.get("club_id")) if career.get("club_id") else None
    return club["strength"] if club else 62


def _desired_squad_status(career):
    player = career["player"]
    performance = career["season_stats"]["goals"] * 1.3 + career["season_stats"]["assists"]
    edge = player["overall"] + (player["form"] - 65) * .12 + (player["morale"] - 65) * .06 + performance + career["status_momentum"] - _club_strength(career)
    if edge < -18: return "out_of_plans"
    if edge < -10: return "reserve"
    if edge < -3: return "rotation"
    if edge < 5: return "starter"
    if edge < 12: return "key_player"
    return "star"


def recalculate_squad_status(career, force=False):
    """Atualiza gradualmente a hierarquia do jogador usando a força do clube atual."""
    desired = _desired_squad_status(career)
    current = career.get("squad_status", "rotation")
    if force:
        career["squad_status"] = desired
    else:
        current_index, desired_index = SQUAD_STATUSES.index(current), SQUAD_STATUSES.index(desired)
        if desired_index != current_index and (career["season_match_count"] % 3 == 0 or abs(desired_index - current_index) >= 2):
            career["squad_status"] = SQUAD_STATUSES[current_index + (1 if desired_index > current_index else -1)]
    career["squad_status_reason"] = f"{SQUAD_STATUS_LABELS[career['squad_status']]} no {career['club']}"
    return career["squad_status"]


def _season_event_target(career):
    return _rng(career).randint(2, 3)


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
    career = {
        "status": "active", "mode": mode, "started_year": today.year,
        "calendar": {"year": today.year, "week": 1, "season": 1, "date": today.isoformat()},
        "player": player, "club": starting_club, "club_id": club_id, "clubs": {starting_club: club_stats()}, "titles": [],
        "history": [{"kind": "início", "text": f"Aos 16 anos, você assinou com {starting_club}."}],
        "pending_event": None, "event_queue": [], "match_state": None, "season_stats": _empty_stats(),
        "season_match_count": 0, "season_started": {"age": 16, "overall": player["overall"], "club": starting_club},
        "season_closed": False, "retirement_reason": None, "death": None,
        "random_seed": seed if seed is not None else rng.randrange(1, 2**31), "random_step": 0, "next_event_id": 1,
        "squad_status": "rotation", "squad_status_reason": "", "status_momentum": 0,
        "development_points": 0, "potential": min(92, player["overall"] + rng.randint(8, 24)),
        "season_actions_used": {category: False for category in PLAYER_ACTIONS}, "action_cooldowns": {}, "season_random_events_count": 0,
    }
    career["season_random_events_target"] = _season_event_target(career)
    recalculate_squad_status(career, force=True)
    normalize_narrative_state(career)
    initialize_competition_world(career)
    return career


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
    career.setdefault("death", None)
    career.setdefault("squad_status", "rotation")
    career.setdefault("squad_status_reason", "")
    career.setdefault("status_momentum", 0)
    career.setdefault("development_points", 0)
    career.setdefault("potential", max(career["player"].get("max_overall", 0), career["player"]["overall"] + 8))
    season_actions = career.setdefault("season_actions_used", {})
    for category in PLAYER_ACTIONS:
        season_actions.setdefault(category, False)
    career.setdefault("action_cooldowns", {})
    career.setdefault("pending_feedback", None)
    career.setdefault("season_random_events_count", 0)
    if "season_random_events_target" not in career:
        career["season_random_events_target"] = _season_event_target(career)
    normalize_narrative_state(career)
    initialize_competition_world(career)
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
    recalculate_squad_status(career)
    return career


def add_history(career, kind, text):
    career["history"].insert(0, {"kind": kind, "text": text})
    del career["history"][24:]


def _event(event_type, title, text, choices=None, **extra):
    return {"id": None, "type": event_type, "title": title, "text": text,
            "choices": choices or [{"id": "continue", "label": "Continuar"}], **extra}


def _queue_event(career, event):
    if event.get("conditions") and not event_is_eligible(career, event):
        return False
    _assign_event_id(career, event)
    career["event_queue"].append(event)
    return True


def _assign_event_id(career, event):
    if event.get("conditions") and event.get("id") and not event.get("event_key"):
        event["event_key"] = event["id"]
    if event.get("id") is None:
        event["id"] = f"event-{career['next_event_id']}"
        career["next_event_id"] += 1


def _set_pending_event(career, event):
    if event.get("conditions") and not event_is_eligible(career, event):
        return False
    _assign_event_id(career, event)
    career["pending_event"] = event
    return True


def _promote_next_event(career):
    if career["status"] == "active" and career["pending_event"] is None and career["event_queue"]:
        _set_pending_event(career, career["event_queue"].pop(0))


def _advance_calendar(career, days):
    current = date.fromisoformat(career["calendar"]["date"])
    current += timedelta(days=days)
    career["calendar"].update({"date": current.isoformat(), "year": current.year, "week": current.isocalendar().week})


def _player_influence(player):
    return player["overall"] * .50 + player["form"] * .28 + player["morale"] * .12 - player["fatigue"] * .18


def available_player_actions(career, category=None):
    """Retorna ações voluntárias válidas; não são eventos aleatórios."""
    if career.get("status") != "active" or career.get("pending_event"):
        return {}
    groups = {category: PLAYER_ACTIONS.get(category, {})} if category else PLAYER_ACTIONS
    result = {}
    for group, actions in groups.items():
        allowed = {}
        for key, action in actions.items():
            if career["player"]["age"] >= action.get("min_age", 0):
                allowed[key] = {"id": key, "label": action["label"]}
        if allowed:
            result[group] = allowed
    return result


def perform_player_action(career, category, action_id):
    """Aplica uma ação voluntária, uma vez por categoria na temporada."""
    if career.get("status") != "active" or career.get("pending_event"):
        return False
    if category not in PLAYER_ACTIONS or career["season_actions_used"].get(category):
        return False
    action = PLAYER_ACTIONS.get(category, {}).get(action_id)
    if not action or career["player"]["age"] < action.get("min_age", 0):
        return False
    before = feedback_snapshot(career)
    from narrative_engine import apply_action_outcome, apply_event_effects
    result_event = apply_action_outcome(career, action, f"action:{category}:{action_id}", _rng(career))
    if result_event is None:
        apply_event_effects(career, action.get("effects", {}))
        if "development" in action:
            efficiency = .45 if career["player"]["fatigue"] >= 70 else .72 if career["player"]["fatigue"] >= 50 else 1
            career["development_points"] += max(1, int(action["development"] * efficiency))
        if action.get("fatigue") or action.get("morale"):
            apply_event_effects(career, {"player": {"fatigue": action.get("fatigue", 0), "morale": action.get("morale", 0)}})
    career["season_actions_used"][category] = True
    add_history(career, "ação", f"Você escolheu: {action['label']}.")
    update_market_value(career["player"])
    if result_event:
        _set_pending_event(career, result_event)
        set_pending_feedback(career, category, result_event["title"], result_event["text"], before,
                             extra={"summary": result_event.get("outcome_summary", [])})
    else:
        set_pending_feedback(career, category, action.get("result_title", action["label"]),
                             action.get("result_text", f"Você concluiu: {action['label']}."), before)
    return True


def _simulate_match_result(career, is_final=False, fixture=None, competition_name=None):
    """Calcula uma partida, mas não toca em estatísticas: aplicação é idempotente."""
    player, rng = career["player"], _rng(career)
    influence = _player_influence(player)
    status = career.get("squad_status", "rotation")
    start_chance = {"out_of_plans": .03, "reserve": .12, "rotation": .42, "starter": .75, "key_player": .87, "star": .94}[status]
    sub_chance = {"out_of_plans": .04, "reserve": .30, "rotation": .34, "starter": .18, "key_player": .09, "star": .04}[status]
    adjustment = max(-.12, min(.12, (influence - 48) / 180))
    started = rng.random() < max(.01, min(.97, start_chance + adjustment))
    substitute = not started and rng.random() < max(.01, min(.55, sub_chance + adjustment / 2))
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
    if fixture:
        opponent_id = fixture["away"] if fixture["home"] == career.get("club_id") else fixture["home"]
        opponent = get_club(opponent_id)
    return {"id": f"match-{career['calendar']['season']}-{career['season_match_count'] + 1}-{career['random_step']}",
            "opponent_id": opponent["id"] if opponent else None,
            "opponent": opponent["name"] if opponent else f"Adversário {career['season_match_count'] + 1}",
            "competition": competition_name or (competition["name"] if competition else "Campeonato nacional"),
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
        performance_delta = match["goals"] * 5 + match["assists"] * 3 - match["red_cards"] * 8 + _rng(career).randint(-3, 3)
        player["form"] = _bounded(player["form"] + performance_delta, 30)
        player["fatigue"] = _bounded(player["fatigue"] + 7 + match["minutes"] // 18)
        career["development_points"] += max(0, match["minutes"] // 30) + match["goals"] + match["assists"]
        career["status_momentum"] = max(-12, min(12, career["status_momentum"] + performance_delta / 4))
    else:
        player["morale"] = _bounded(player["morale"] - 2, 25)
        career["status_momentum"] = max(-12, career["status_momentum"] - 1)
    career["season_match_count"] += 1
    recalculate_squad_status(career)
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
        efficiency = .45 if player["fatigue"] >= 70 else .72 if player["fatigue"] >= 50 else 1
        career["development_points"] += max(1, int(2 * multiplier * efficiency))
        player["form"] = _bounded(player["form"] + 2)
        player["fatigue"] = _bounded(player["fatigue"] + 4 * multiplier)
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
        career["development_points"] += 1
        player["fatigue"] = _bounded(player["fatigue"] + 16)
    add_history(career, "decisão", "Você decidiu como lidar com a carga física.")


def _end_season(career):
    if career["season_closed"]:
        return
    career["season_closed"] = True
    finalize_country_season(career)
    player, calendar = career["player"], career["calendar"]
    career["clubs"][career["club"]]["seasons"] += 1
    growth_rng = _rng(career)
    age_factor = 1.0 if player["age"] <= 21 else .65 if player["age"] <= 27 else .25 if player["age"] <= 31 else -.45
    opportunity = min(1.25, career["season_stats"]["matches"] / 12)
    training = career["development_points"] / 12
    wellbeing = ((player["morale"] - 50) - max(0, player["fatigue"] - 45)) / 100
    ceiling = max(0, career["potential"] - player["overall"])
    growth_score = age_factor * opportunity * (0.45 + training) + wellbeing + growth_rng.uniform(-.55, .55)
    growth = 1 if growth_score >= 1.45 and ceiling > 0 else 0
    if growth_score >= 2.5 and ceiling > 1:
        growth = 2
    if age_factor < 0 and growth_score < -.15:
        growth = -1
    player["overall"] = _bounded(player["overall"] + growth, 38, career["potential"])
    player["age"] += 1
    next_date = date.fromisoformat(calendar["date"]) + timedelta(days=7)
    calendar.update({"year": next_date.year, "week": 1, "season": calendar["season"] + 1, "date": next_date.isoformat()})
    player["fatigue"] = 18
    player["form"] = max(55, player["form"])
    update_market_value(player)
    add_history(career, "temporada", f"Temporada encerrada. Você agora tem {player['age']} anos.")
    career["season_stats"] = _empty_stats()
    career["season_match_count"] = 0
    career["development_points"] = 0
    career["status_momentum"] *= .5
    career["season_actions_used"] = {category: False for category in PLAYER_ACTIONS}
    career["season_random_events_count"] = 0
    career["season_random_events_target"] = _season_event_target(career)
    career["season_started"] = {"age": player["age"], "overall": player["overall"], "club": career["club"]}
    career["season_closed"] = False
    start_new_competition_season(career)
    recalculate_squad_status(career, force=True)
    if player["age"] >= 40:
        retire(career, "O tempo chegou: você se aposentou aos 40 anos.")


def _season_summary_event(career):
    player, start, stats = career["player"], career["season_started"], career["season_stats"]
    summary = {"season": career["calendar"]["season"], "age_start": start["age"], "age_end": player["age"] + 1,
               "overall_start": start["overall"], "overall_end": player["overall"], "club": career["club"],
               "matches": stats["matches"], "goals": stats["goals"], "assists": stats["assists"],
               "titles": [title for title in career["titles"] if title["season"] == career["calendar"]["season"]],
               "competitions": career.get("season_competitions", {})}
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


def _award_competition_title(career, competition):
    """Registra um título real do motor sem duplicar o mesmo torneio na temporada."""
    if any(item["competition"] == competition and item["season"] == career["calendar"]["season"] for item in career["titles"]):
        return
    title = {"competition": competition, "season": career["calendar"]["season"], "club": career["club"]}
    career["titles"].append(title)
    career["clubs"][career["club"]]["titles"].append(competition)
    add_history(career, "título", f"Você conquistou {competition} pelo {career['club']}.")


def _simulate_accelerated_season(career):
    """Processa a liga real do clube e fecha os demais torneios em silêncio."""
    league = current_league_state(career)
    if league:
        for number in range(league["completed_rounds"] + 1, len(league["fixtures"]) + 1):
            fixture = next(item for item in league["fixtures"][number - 1] if career["club_id"] in (item["home"], item["away"]))
            _advance_calendar(career, 5 + _rng(career).randint(1, 3))
            career["player"]["fatigue"] = _bounded(career["player"]["fatigue"] - 4)
            match = _simulate_match_result(career, fixture=fixture, competition_name=league["name"])
            simulate_league_round(league, number, _rng(career), career["club_id"], tuple(match["score"]))
            _apply_match(career, match)
        cups = simulate_remaining_competitions(career, _rng(career))
        for cup in cups:
            if cup.get("champion") == career["club_id"]:
                _award_competition_title(career, cup["name"])
        finalize_country_season(career)
        career["season_competitions"] = {
            "league": competition_summary(league, career["club_id"]),
            "cups": [{"id": cup["id"], "name": cup["name"], "status": "champion" if cup.get("champion") == career["club_id"] else "eliminated", "stage_reached": cup.get("stage_reached", {}).get(str(career["club_id"]), "Não disputou")} for cup in cups],
            "continental": [], "context": competition_context(career),
            "qualified_for_next_season": career["competition_world"]["qualified_for_next_season"].get(str(career["club_id"]), []),
        }
    else:
        # Clube sem competição configurada: preserva o fluxo legado como fallback.
        for _ in range(18):
            _advance_calendar(career, 7)
            _apply_match(career, _simulate_match_result(career))
    for follow_up in due_follow_up_events(career):
        _queue_event(career, follow_up)
    _queue_event(career, _training_event(periods=9))
    remaining_events = career["season_random_events_target"] - career["season_random_events_count"]
    for _ in range(max(0, remaining_events)):
        narrative_event = maybe_create_narrative_event(career, _rng(career), chance=.85, accelerated=True, normal_only=True)
        if not narrative_event:
            break
        narrative_event["random_event"] = True
        _queue_event(career, narrative_event)
        career["season_random_events_count"] += 1
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
        follow_ups = due_follow_up_events(career)
        if follow_ups:
            _set_pending_event(career, follow_ups[0])
            for event in follow_ups[1:]:
                _queue_event(career, event)
            return
        transfer_event = maybe_create_realistic_transfer_event(career, _rng(career))
        if transfer_event:
            _set_pending_event(career, transfer_event)
            return
        target_remaining = career["season_random_events_count"] < career["season_random_events_target"]
        narrative_event = maybe_create_narrative_event(career, _rng(career), chance=.22 if target_remaining else .025, normal_only=target_remaining)
        if narrative_event:
            narrative_event["random_event"] = True
            career["season_random_events_count"] += 1
            _set_pending_event(career, narrative_event)
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
    if career.get("status") != "active":
        return False
    event = career["pending_event"]
    if not event or (event_id is not None and event_id != event["id"]) or choice not in {item["id"] for item in event["choices"]}:
        return False
    event_type = event["type"]
    before = feedback_snapshot(career)
    if event_type == "outcome" and choice == "continue":
        career["pending_event"] = None
        career["pending_feedback"] = None
        _promote_next_event(career)
        return True
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
        career["pending_event"] = None
        set_pending_feedback(career, "training", "Treinamento concluído", "Você definiu o foco do trabalho e completou a sessão.", before)
        _promote_next_event(career)
        return True
    elif event_type == "recovery":
        _apply_recovery(career, choice)
        career["pending_event"] = None
        set_pending_feedback(career, "rest", "Recuperação concluída", "Você administrou a carga física antes do próximo compromisso.", before)
        _promote_next_event(career)
        return True
    elif event_type in {"transfer_market", "transfer_interest"}:
        if not resolve_transfer_decision(career, event, choice):
            return False
        transfer = career.pop("transfer_feedback", None)
        title = transfer["title"] if transfer else "Decisão de mercado"
        text = transfer["text"] if transfer else "Sua decisão no mercado foi registrada."
        career["pending_event"] = None
        set_pending_feedback(career, "transfer", title, text, before, extra=transfer or {})
        _promote_next_event(career)
        return True
    elif event.get("narrative_event") or any("effects" in item or "outcomes" in item for item in event.get("choices", [])):
        narrative_result = resolve_narrative_event(career, event, choice, _rng(career))
        if not narrative_result:
            return False
        if isinstance(narrative_result, dict):
            if career["status"] != "active":
                reason = career.get("retirement_reason") or career.get("death", {}).get("reason") or narrative_result["text"]
                career["pending_event"] = None
                set_pending_feedback(career, "terminal", "Fim da carreira", reason, before, terminal=True)
                return True
            _set_pending_event(career, narrative_result)
            set_pending_feedback(career, "event", narrative_result["title"], narrative_result["text"], before,
                                 extra={"summary": narrative_result.get("outcome_summary", [])})
            return True
        career["pending_event"] = None
        set_pending_feedback(career, "event", event["title"], "Sua decisão foi registrada.", before)
        _promote_next_event(career)
        return True
    elif event_type == "season_summary":
        career["pending_event"] = None
        _end_season(career)
        return True
    if career["status"] != "active":
        reason = career.get("retirement_reason") or career.get("death", {}).get("reason") or "A carreira foi encerrada."
        set_pending_feedback(career, "terminal", "Fim da carreira", reason, before, terminal=True)
        return True
    career["pending_event"] = None
    update_market_value(career["player"])
    _promote_next_event(career)
    return True


def retire(career, reason):
    return retire_career(career, reason)


def final_card_svg(career):
    player = career["player"]
    club_lines = [f"{name}: {stats['matches']} J · {stats['goals']} G · {stats['assists']} A · {len(stats['titles'])} títulos" for name, stats in career["clubs"].items()]
    rows = "".join(f'<text x="80" y="{390 + index * 42}" class="row">{escape(line)}</text>' for index, line in enumerate(club_lines[:7]))
    title, country, position = escape(player["name"]), escape(player["country"]), escape(player["position"])
    ending = f"falecimento aos {career['death']['age']} anos" if career.get("status") == "deceased" else f"aposentadoria aos {player['age']} anos"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760"><style>.bg{{fill:#07150e}}.card{{fill:#123324;stroke:#28523b;stroke-width:2}}.brand{{fill:#b7ef52;font:700 24px Arial}}.name{{fill:#fff;font:800 58px Arial}}.sub{{fill:#b6c8ba;font:24px Arial}}.label{{fill:#a8b9ad;font:700 17px Arial}}.value{{fill:#fff;font:800 32px Arial}}.row{{fill:#eef8f0;font:21px Arial}}</style><rect class="bg" width="1200" height="760"/><rect class="card" x="45" y="40" width="1110" height="680" rx="28"/><text x="80" y="95" class="brand">VIDA DE BOLEIRO · CARD DE CARREIRA</text><text x="80" y="170" class="name">{title}</text><text x="80" y="210" class="sub">{country} · {position} · {escape(ending)}</text><text x="80" y="285" class="label">JOGOS</text><text x="80" y="325" class="value">{player['matches']}</text><text x="300" y="285" class="label">GOLS</text><text x="300" y="325" class="value">{player['goals']}</text><text x="500" y="285" class="label">ASSISTÊNCIAS</text><text x="500" y="325" class="value">{player['assists']}</text><text x="760" y="285" class="label">OVR MÁX.</text><text x="760" y="325" class="value">{player['max_overall']}</text><text x="980" y="285" class="label">TÍTULOS</text><text x="980" y="325" class="value">{len(career['titles'])}</text><text x="80" y="365" class="brand">CLUBES</text>{rows}</svg>'''
