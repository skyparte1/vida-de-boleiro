"""Motor determinístico do universo de competições.

As configurações são estáticas; somente o estado de uma temporada vive na
carreira em sessão. O módulo não conhece Flask nem toma decisões narrativas.
"""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

from database import get_club, get_clubs_by_competition, get_competitions_by_country


# Regras deliberadamente simples e versionadas. Países fora desta lista usam
# o formato genérico, sem impedir que seus clubes disputem a própria liga.
COUNTRY_RULES = {
    "BRA": {"relegation": {1: 4, 2: 4, 3: 4}, "promotion": {2: 4, 3: 4, 4: 4}, "continental": (4, 2)},
    "ENG": {"relegation": {1: 3, 2: 3}, "promotion": {2: 3}, "continental": (4, 2)},
    "ESP": {"relegation": {1: 3, 2: 4}, "promotion": {2: 3}, "continental": (4, 2)},
    "GER": {"relegation": {1: 3, 2: 3}, "promotion": {2: 3}, "continental": (4, 2)},
    "ITA": {"relegation": {1: 3, 2: 3}, "promotion": {2: 3}, "continental": (4, 2)},
    "FRA": {"relegation": {1: 3, 2: 2}, "promotion": {2: 2}, "continental": (3, 2)},
    "POR": {"relegation": {1: 3, 2: 2}, "promotion": {2: 2}, "continental": (3, 1)},
    "NED": {"relegation": {1: 2, 2: 2}, "promotion": {2: 2}, "continental": (2, 1)},
    "BEL": {"relegation": {1: 2, 2: 2}, "promotion": {2: 2}, "continental": (2, 1)},
    "ARG": {"relegation": {1: 2, 2: 2}, "promotion": {2: 2}, "continental": (4, 2)},
}


def _rule(country, key, tier, default=0):
    return COUNTRY_RULES.get(country, {}).get(key, {}).get(tier, default)


def _entry():
    return {"points": 0, "played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0}


def _fixture(home, away, round_number, competition_id):
    return {"home": home, "away": away, "round": round_number, "competition_id": competition_id, "played": False, "score": None}


def generate_league_schedule(team_ids, competition_id, double_round_robin=True):
    """Calendário circular: cada par se enfrenta uma vez por turno."""
    teams = list(team_ids)
    if len(teams) % 2:
        teams.append(None)
    rounds, rotation = [], teams[:]
    for round_number in range(len(rotation) - 1):
        fixtures = []
        for index in range(len(rotation) // 2):
            home, away = rotation[index], rotation[-index - 1]
            if home is not None and away is not None:
                if round_number % 2:
                    home, away = away, home
                fixtures.append(_fixture(home, away, round_number + 1, competition_id))
        rounds.append(fixtures)
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    if double_round_robin:
        offset = len(rounds)
        rounds.extend([[_fixture(item["away"], item["home"], offset + number + 1, competition_id) for item in group] for number, group in enumerate(rounds[:])])
    return rounds


def create_league_state(competition, clubs):
    ids = [club["id"] for club in clubs]
    return {
        "id": competition["id"], "name": competition["name"], "kind": "league", "country": competition["country_code"],
        "tier": competition["tier"], "participants": ids, "fixtures": generate_league_schedule(ids, competition["id"]),
        "standings": {str(club_id): _entry() for club_id in ids}, "completed_rounds": 0, "status": "active",
        "points_for_win": 3, "points_for_draw": 1, "points_for_loss": 0,
        "tiebreakers": ["points", "goal_difference", "goals_for"], "results": [],
    }


def _standings_key(state, club_id):
    entry = state["standings"][str(club_id)]
    return (-entry["points"], -(entry["goals_for"] - entry["goals_against"]), -entry["goals_for"], str(club_id))


def ordered_standings(state):
    return [club_id for club_id in state["participants"] if str(club_id) in state["standings"] and True] if not state["participants"] else sorted(state["participants"], key=lambda club_id: _standings_key(state, club_id))


def standings_rows(state):
    rows = []
    for position, club_id in enumerate(ordered_standings(state), 1):
        entry = state["standings"][str(club_id)]
        rows.append({"position": position, "club_id": club_id, "points": entry["points"], "played": entry["played"], "wins": entry["wins"], "draws": entry["draws"], "losses": entry["losses"], "goals_for": entry["goals_for"], "goals_against": entry["goals_against"], "goal_difference": entry["goals_for"] - entry["goals_against"]})
    return rows


def record_league_result(state, fixture, home_goals, away_goals):
    """Aplica uma partida uma única vez e mantém invariantes da classificação."""
    if fixture.get("played"):
        return False
    fixture.update({"played": True, "score": [int(home_goals), int(away_goals)]})
    home, away = state["standings"][str(fixture["home"])], state["standings"][str(fixture["away"])]
    for entry, scored, conceded in ((home, home_goals, away_goals), (away, away_goals, home_goals)):
        entry["played"] += 1
        entry["goals_for"] += scored
        entry["goals_against"] += conceded
    if home_goals > away_goals:
        home["wins"] += 1; away["losses"] += 1; home["points"] += state["points_for_win"]
    elif away_goals > home_goals:
        away["wins"] += 1; home["losses"] += 1; away["points"] += state["points_for_win"]
    else:
        home["draws"] += 1; away["draws"] += 1
        home["points"] += state["points_for_draw"]; away["points"] += state["points_for_draw"]
    state["results"].append({"home": fixture["home"], "away": fixture["away"], "score": fixture["score"]})
    return True


@lru_cache(maxsize=1024)
def _club_strength(club_id):
    club = get_club(club_id)
    return club["strength"] if club else 50


def simulate_fixture(home_id, away_id, rng, home_advantage=2.2, home_form=0, away_form=0):
    """Placar compacto, influenciado por força, forma e mando, sem RNG global."""
    edge = (_club_strength(home_id) + home_advantage + home_form) - (_club_strength(away_id) + away_form)
    home_expectation = max(.25, min(2.5, 1.22 + edge / 24))
    away_expectation = max(.20, min(2.3, 1.02 - edge / 28))
    def goals(expectation):
        # distribuição discreta suficiente para placares plausíveis; placares 5+ são raros.
        value = int(max(0, rng.gauss(expectation, .82)))
        return min(5, value)
    return goals(home_expectation), goals(away_expectation)


def simulate_league_round(state, round_number, rng, player_club_id=None, player_result=None):
    """Simula uma rodada. player_result pode substituir o placar do clube do jogador."""
    fixtures = state["fixtures"][round_number - 1]
    for fixture in fixtures:
        if fixture["played"]:
            continue
        if player_result and player_club_id in (fixture["home"], fixture["away"]):
            own, opponent = player_result
            score = (own, opponent) if fixture["home"] == player_club_id else (opponent, own)
        else:
            score = simulate_fixture(fixture["home"], fixture["away"], rng)
        record_league_result(state, fixture, *score)
    state["completed_rounds"] = max(state["completed_rounds"], round_number)
    if state["completed_rounds"] >= len(state["fixtures"]):
        state["status"] = "finished"


def create_cup_state(competition_id, name, country, participant_ids):
    """Copa nacional em jogo único. A primeira fase acomoda byes automaticamente."""
    participants = list(dict.fromkeys(participant_ids))
    return {"id": competition_id, "name": name, "kind": "cup", "country": country, "participants": participants,
            "active": participants[:], "eliminated": [], "current_stage": "Primeira fase", "stage_reached": {},
            "fixtures": [], "status": "active", "champion": None, "single_leg": True}


def _cup_stage_name(team_count):
    return {2: "Final", 4: "Semifinal", 8: "Quartas de final", 16: "Oitavas de final"}.get(team_count, "Primeira fase")


def play_cup_round(state, rng):
    if state["status"] != "active":
        return []
    active = state["active"][:]
    next_power = 1
    while next_power * 2 <= len(active): next_power *= 2
    byes = len(active) - next_power
    advancing, matches = active[:byes], []
    remaining = active[byes:]
    state["current_stage"] = _cup_stage_name(len(active))
    for index in range(0, len(remaining), 2):
        home, away = remaining[index], remaining[index + 1]
        score = simulate_fixture(home, away, rng)
        if score[0] == score[1]:
            # pênaltis: vencedor é decidido uma vez, sem simulação minuto a minuto.
            winner = home if rng.random() < .5 else away
            decided_by = "penalties"
        else:
            winner, decided_by = (home if score[0] > score[1] else away), "normal_time"
        loser = away if winner == home else home
        matches.append({"home": home, "away": away, "score": list(score), "winner": winner, "loser": loser, "stage": state["current_stage"], "decided_by": decided_by})
        advancing.append(winner); state["eliminated"].append(loser); state["stage_reached"][str(loser)] = state["current_stage"]
    state["fixtures"].extend(matches); state["active"] = advancing
    if len(advancing) == 1:
        state["champion"] = advancing[0]; state["status"] = "finished"; state["stage_reached"][str(advancing[0])] = "Campeão"
    return matches


def _country_leagues(country):
    return [competition for competition in get_competitions_by_country(country) if competition["type"] == "league"]


def _database_season(career):
    return 2026


def _league_for_club(world, club_id):
    return world.get("club_divisions", {}).get(str(club_id))


def initialize_competition_world(career):
    """Normaliza carreiras novas/legadas sem alterar registros permanentes do SQLite."""
    world = career.setdefault("competition_world", {"season": career["calendar"]["season"], "countries": {}, "club_divisions": {}, "qualified_for_next_season": {}, "history": [], "finalized_seasons": []})
    club = get_club(career.get("club_id")) if career.get("club_id") else None
    if not club:
        career.setdefault("season_competitions", {"league": None, "cups": [], "continental": []})
        return world
    country = club["country_code"]
    if country not in world["countries"]:
        leagues = {}
        for competition in _country_leagues(country):
            clubs = get_clubs_by_competition(competition["id"], _database_season(career))
            if clubs:
                state = create_league_state(competition, clubs)
                leagues[str(competition["id"])] = state
                for item in clubs: world["club_divisions"][str(item["id"])] = competition["id"]
        cups = [item for item in get_competitions_by_country(country) if item["type"] == "cup"]
        participant_ids = [club_id for state in leagues.values() for club_id in state["participants"]]
        cup_states = {str(item["id"]): create_cup_state(item["id"], item["name"], country, participant_ids) for item in cups}
        world["countries"][country] = {"leagues": leagues, "cups": cup_states, "configured_cups": cups}
    league_id = _league_for_club(world, career["club_id"])
    state = world["countries"][country]["leagues"].get(str(league_id)) if league_id else None
    career.setdefault("season_competitions", {
        "league": competition_summary(state, career["club_id"]) if state else None,
        "cups": [], "continental": [], "qualified_for_next_season": world["qualified_for_next_season"].get(str(career["club_id"]), []),
    })
    return world


def current_league_state(career, club_id=None):
    world = initialize_competition_world(career)
    club_id = club_id or career.get("club_id")
    league_id = _league_for_club(world, club_id)
    club = get_club(club_id) if club_id else None
    return world.get("countries", {}).get(club["country_code"] if club else "", {}).get("leagues", {}).get(str(league_id))


def competition_summary(state, club_id):
    if not state or club_id not in state["participants"]:
        return None
    row = next(item for item in standings_rows(state) if item["club_id"] == club_id)
    return {"id": state["id"], "name": state["name"], "kind": state["kind"], "tier": state["tier"], "position": row["position"], "points": row["points"], "played": row["played"], "status": state["status"]}


def competition_context(career):
    state = current_league_state(career)
    if not state:
        return {}
    summary = competition_summary(state, career["club_id"])
    if not summary:
        return {}
    rows = standings_rows(state); position = summary["position"]; total = len(rows)
    relegated = _rule(state["country"], "relegation", state["tier"], 0)
    leader = rows[0]
    return {"league_position": position, "in_relegation_zone": bool(relegated and position > total - relegated),
            "points_to_safety": max(0, rows[total - relegated - 1]["points"] - summary["points"] + 1) if relegated and position > total - relegated else 0,
            "in_title_race": summary["points"] >= leader["points"] - 6, "points_from_leader": leader["points"] - summary["points"],
            "league_status": state["status"]}


def calculate_match_importance(state, fixture, club_id):
    """Expõe reason/stakes para B2; a decisão usa pontos máximos restantes."""
    if state.get("kind") in {"cup", "continental"}:
        stage = fixture.get("stage") or state.get("current_stage")
        return {"important": stage in {"Semifinal", "Final"}, "reason": "final" if stage == "Final" else "semifinal" if stage == "Semifinal" else None, "stakes": stage}
    total_rounds = len(state["fixtures"]); remaining = total_rounds - state["completed_rounds"]
    summary = competition_summary(state, club_id); rows = standings_rows(state)
    if remaining <= 1: return {"important": True, "reason": "last_round", "stakes": "rodada decisiva"}
    second = rows[1] if len(rows) > 1 else None
    if summary["position"] == 1 and second and summary["points"] > second["points"] + (remaining - 1) * state["points_for_win"]:
        return {"important": True, "reason": "title_clinch", "stakes": "pode garantir o título"}
    relegated = _rule(state["country"], "relegation", state["tier"], 0)
    if relegated and summary["position"] >= len(rows) - relegated:
        return {"important": True, "reason": "relegation_decider", "stakes": "luta contra o rebaixamento"}
    return {"important": False, "reason": None, "stakes": None}


def simulate_remaining_competitions(career, rng):
    """Fecha os torneios domésticos do país sem gerar cards para jogos comuns."""
    world = initialize_competition_world(career)
    club = get_club(career.get("club_id")) if career.get("club_id") else None
    if not club:
        return []
    country_state = world["countries"][club["country_code"]]
    for state in country_state["leagues"].values():
        for number in range(state["completed_rounds"] + 1, len(state["fixtures"]) + 1):
            simulate_league_round(state, number, rng)
    completed_cups = []
    for cup in country_state["cups"].values():
        while cup["status"] == "active":
            play_cup_round(cup, rng)
        completed_cups.append(cup)
    return completed_cups


def finalize_country_season(career):
    """Aplica acesso, queda e vagas futuras uma única vez ao mundo em sessão."""
    world = initialize_competition_world(career)
    season = career["calendar"]["season"]
    club = get_club(career.get("club_id")) if career.get("club_id") else None
    if not club: return False
    marker = f"{season}:{club['country_code']}"
    if marker in world["finalized_seasons"]:
        return False
    country_state = world["countries"].get(club["country_code"], {})
    leagues = list(country_state.get("leagues", {}).values())
    for state in leagues:
        if state["status"] != "finished": return False
    by_tier = {state["tier"]: state for state in leagues}
    moves = {}
    for tier, state in by_tier.items():
        ordered = ordered_standings(state); relegation = _rule(state["country"], "relegation", tier)
        promotion = _rule(state["country"], "promotion", tier)
        if relegation and tier + 1 in by_tier:
            for club_id in ordered[-relegation:]: moves[club_id] = by_tier[tier + 1]["id"]
        if promotion and tier - 1 in by_tier:
            for club_id in ordered[:promotion]: moves[club_id] = by_tier[tier - 1]["id"]
    for club_id, league_id in moves.items(): world["club_divisions"][str(club_id)] = league_id
    top = by_tier.get(1)
    if top:
        main, secondary = COUNTRY_RULES.get(top["country"], {}).get("continental", (0, 0))
        qualifiers = []
        for index, club_id in enumerate(ordered_standings(top)):
            target = "continental_main" if index < main else "continental_secondary" if index < main + secondary else None
            if target: qualifiers.append((club_id, target))
        for club_id, target in qualifiers:
            world["qualified_for_next_season"].setdefault(str(club_id), [])
            if target not in world["qualified_for_next_season"][str(club_id)]: world["qualified_for_next_season"][str(club_id)].append(target)
    world["history"].append({"season": season, "country": top["country"] if top else club["country_code"], "leagues": {str(state["id"]): standings_rows(state) for state in leagues}})
    world["finalized_seasons"].append(marker)
    return True


def start_new_competition_season(career):
    """Reconstrói calendários usando as divisões já alteradas no mundo da carreira."""
    world = initialize_competition_world(career)
    old_countries = world["countries"]
    world["season"] = career["calendar"]["season"]
    world["countries"] = {}
    for country, country_state in old_countries.items():
        old_leagues = list(country_state["leagues"].values())
        all_ids = [club_id for state in old_leagues for club_id in state["participants"]]
        competitions = {item["id"]: item for item in _country_leagues(country)}
        leagues = {}
        for competition_id, competition in competitions.items():
            ids = [club_id for club_id in all_ids if world["club_divisions"].get(str(club_id), competition_id) == competition_id]
            clubs = [get_club(club_id) for club_id in ids]
            if clubs:
                leagues[str(competition_id)] = create_league_state(competition, clubs)
        participant_ids = [club_id for state in leagues.values() for club_id in state["participants"]]
        cups = [item for item in get_competitions_by_country(country) if item["type"] == "cup"]
        world["countries"][country] = {"leagues": leagues, "cups": {str(item["id"]): create_cup_state(item["id"], item["name"], country, participant_ids) for item in cups}, "configured_cups": cups}
    career.pop("season_competitions", None)
    return initialize_competition_world(career)
