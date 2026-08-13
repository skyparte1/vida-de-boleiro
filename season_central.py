"""Apresentação serializável da Central da Temporada; não simula nem altera o mundo."""

from competition_engine import COUNTRY_RULES, _rule, current_league_state, standings_rows
from database import get_club


def _objective(career, league):
    club = get_club(career.get("club_id")) if career.get("club_id") else None
    if not club or not league:
        return {"label": "Acompanhar a temporada", "status": "Em andamento"}
    strength = (club["strength"] + club["reputation"]) / 2
    promotion = _rule(league["country"], "promotion", league["tier"])
    if league["tier"] > 1 and strength >= 68 and promotion:
        label, target = "Conquistar o acesso", promotion
    elif strength >= 78:
        label, target = "Disputar o título", 1
    elif strength >= 64:
        label, target = "Classificar para competição continental", COUNTRY_RULES.get(league["country"], {}).get("continental", (4, 0))[0]
    elif strength < 55:
        label, target = "Evitar o rebaixamento", len(league["participants"]) - _rule(league["country"], "relegation", league["tier"], 0)
    else:
        label, target = "Terminar na primeira metade", len(league["participants"]) // 2
    row = next(item for item in standings_rows(league) if item["club_id"] == career["club_id"])
    return {"label": label, "status": "No caminho certo" if row["position"] <= target else "Em risco", "target": target}


def build_season_central(career):
    league = current_league_state(career)
    snapshot = career.get("season_competitions", {})
    league_summary = snapshot.get("league")
    competitions = ([{**league_summary, "type": "Liga"}] if league_summary else []) + [{**item, "type": "Copa"} for item in snapshot.get("cups", [])] + [{**item, "type": "Continental"} for item in snapshot.get("continental", [])]
    rows = standings_rows(league) if league else []
    for row in rows:
        club = get_club(row["club_id"])
        row["club_name"] = club["name"] if club else "Clube"
    relegation = _rule(league["country"], "relegation", league["tier"], 0) if league else 0
    promotion = _rule(league["country"], "promotion", league["tier"], 0) if league else 0
    continental = COUNTRY_RULES.get(league["country"], {}).get("continental", (0, 0))[0] if league else 0
    fixtures = []
    if league:
        for group in league["fixtures"]:
            for fixture in group:
                if career["club_id"] in (fixture["home"], fixture["away"]):
                    opponent = get_club(fixture["away"] if fixture["home"] == career["club_id"] else fixture["home"])
                    fixtures.append({"round": fixture["round"], "opponent": opponent["name"] if opponent else "Adversário", "home": fixture["home"] == career["club_id"], "played": fixture["played"], "score": fixture.get("score"), "name": league["name"]})
    objective = _objective(career, league)
    return {"season": career["calendar"]["season"], "competitions": competitions, "league": league_summary, "table": rows,
            "zones": {"relegation": relegation, "promotion": promotion, "continental": continental},
            "schedule": {"recent": [item for item in fixtures if item["played"]][-5:], "upcoming": [item for item in fixtures if not item["played"]][:5]},
            "objective": objective, "stats": career["season_stats"], "history": career.get("history", [])[:12],
            "qualified": snapshot.get("qualified_for_next_season", [])}
