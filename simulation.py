import random
from datetime import date
from xml.sax.saxutils import escape

from football_data import random_club


TITLE_NAMES = ["Campeonato nacional", "Copa nacional", "Competição continental", "Supercopa"]


def market_value(player):
    age = player["age"]
    age_factor = 1.20 if age <= 21 else 1.12 if age <= 25 else 1.0 if age <= 29 else .76 if age <= 33 else .45
    performance = player["matches"] * 12_000 + player["goals"] * 85_000 + player["assists"] * 55_000
    technical = max(0, player["overall"] - 40) ** 2 * 14_000
    foot_bonus = 1.12 if player["ambidextrous"] else 1 + player["weak_foot"] / 1000
    return int((150_000 + performance + technical) * age_factor * foot_bonus / 10_000) * 10_000


def club_stats():
    return {"seasons": 0, "matches": 0, "goals": 0, "assists": 0, "titles": []}


def create_career(name, country, position, dominant_foot, starting_club):
    player = {
        "name": name.strip(), "country": country, "position": position, "dominant_foot": dominant_foot,
        "age": 16, "overall": random.randint(52, 68), "weak_foot": random.randint(30, 50),
        "ambidextrous": False, "matches": 0, "goals": 0, "assists": 0, "money": 0,
        "form": 65, "morale": 68, "fatigue": 18, "market_value": 0, "max_overall": 0, "max_market_value": 0,
    }
    player["market_value"] = market_value(player)
    player["max_overall"] = player["overall"]
    player["max_market_value"] = player["market_value"]
    return {
        "status": "active", "started_year": date.today().year, "calendar": {"year": date.today().year, "week": 1, "season": 1},
        "player": player, "club": starting_club, "clubs": {starting_club: club_stats()}, "titles": [],
        "history": [{"kind": "início", "text": f"Aos 16 anos, você assinou com {starting_club}."}],
        "pending_event": None, "retirement_reason": None,
    }


def add_history(career, kind, text):
    career["history"].insert(0, {"kind": kind, "text": text})
    del career["history"][24:]


def update_market_value(player):
    player["market_value"] = market_value(player)
    player["max_overall"] = max(player["max_overall"], player["overall"])
    player["max_market_value"] = max(player["max_market_value"], player["market_value"])


def simulate_match(career):
    player = career["player"]
    stats = career["clubs"][career["club"]]
    played = random.random() < min(.94, .42 + player["form"] / 110)
    if not played:
        player["morale"] = max(25, player["morale"] - 2)
        add_history(career, "elenco", "Você ficou no banco nesta semana.")
        return
    goals_cap = 0 if player["position"] == "Goleiro" else 1 if player["position"] in {"Zagueiro", "Lateral esquerdo", "Lateral direito", "Volante"} else 3
    goals = 1 if random.random() < (player["overall"] / 260) and goals_cap else 0
    assists = 1 if random.random() < (player["overall"] / 320) and player["position"] != "Goleiro" else 0
    player["matches"] += 1; player["goals"] += goals; player["assists"] += assists
    stats["matches"] += 1; stats["goals"] += goals; stats["assists"] += assists
    player["form"] = min(100, max(30, player["form"] + 3 * goals + 2 * assists + random.randint(-5, 4)))
    player["fatigue"] = min(100, player["fatigue"] + random.randint(7, 13))
    summary = "Você participou da partida"
    if goals: summary += " e marcou um gol"
    if assists: summary += " e deu uma assistência"
    add_history(career, "partida", f"{summary} pelo {career['club']}.")


def season_end(career):
    player, calendar = career["player"], career["calendar"]
    stats = career["clubs"][career["club"]]
    stats["seasons"] += 1
    if random.random() < (.08 if player["overall"] < 70 else .18 if player["overall"] < 80 else .30):
        title = random.choice(TITLE_NAMES)
        stats["titles"].append(title); career["titles"].append(title)
        add_history(career, "título", f"Você conquistou {title} pelo {career['club']}.")
    growth = random.choice([0, 1, 1, 2, 2, 3]) if player["age"] < 29 else random.choice([-2, -1, 0, 0, 1])
    player["overall"] = max(38, min(99, player["overall"] + growth))
    player["age"] += 1; calendar["year"] += 1; calendar["week"] = 1; calendar["season"] += 1
    player["fatigue"] = 18; player["form"] = max(55, player["form"])
    add_history(career, "temporada", f"Temporada encerrada. Você agora tem {player['age']} anos.")
    if player["age"] >= 40:
        retire(career, "O tempo chegou: você se aposentou aos 40 anos.")


def choose_event(career):
    player = career["player"]
    if player["overall"] >= 70 and random.random() < .35:
        next_club, _ = random_club("medium" if player["overall"] < 82 else "big", exclude=career["club"])
        return {"type": "transfer", "title": "Proposta de transferência", "text": f"{next_club} quer contratá-lo agora.", "target": next_club,
                "choices": [{"id": "accept", "label": "Aceitar a proposta"}, {"id": "reject", "label": "Recusar e permanecer"}]}
    if player["fatigue"] >= 60:
        return {"type": "recovery", "title": "Corpo no limite", "text": "A comissão nota fadiga elevada antes de uma sequência importante.",
                "choices": [{"id": "rest", "label": "Descansar e recuperar"}, {"id": "push", "label": "Manter treino intenso"}]}
    return {"type": "training", "title": "Plano de treino", "text": "Você recebeu tempo extra para definir o foco da semana.",
            "choices": [{"id": "weak_foot", "label": "Treinar a perna fraca"}, {"id": "balanced", "label": "Treino equilibrado"}, {"id": "rest", "label": "Priorizar recuperação"}]}


def advance_week(career):
    if career["status"] != "active": return
    player, calendar = career["player"], career["calendar"]
    calendar["week"] += 1
    player["fatigue"] = max(0, player["fatigue"] - random.randint(3, 8))
    if calendar["week"] % 2 == 0: simulate_match(career)
    if calendar["week"] > 52:
        season_end(career)
        if career["status"] != "active": return
    update_market_value(player)
    if calendar["week"] % 6 == 0 or random.random() < .08:
        career["pending_event"] = choose_event(career)


def resolve_decision(career, choice):
    event = career["pending_event"]
    if not event or choice not in {item["id"] for item in event["choices"]}: return
    player = career["player"]
    if event["type"] == "transfer":
        if choice == "accept":
            old_club, new_club = career["club"], event["target"]
            career["club"] = new_club; career["clubs"].setdefault(new_club, club_stats())
            player["morale"] = min(100, player["morale"] + 6)
            add_history(career, "transferência", f"Você deixou {old_club} para atuar no {new_club}.")
        else: add_history(career, "transferência", f"Você recusou uma proposta e permaneceu no {career['club']}.")
    elif event["type"] == "recovery":
        if choice == "rest": player["fatigue"] = max(0, player["fatigue"] - 25); player["form"] = min(100, player["form"] + 2)
        else: player["overall"] = min(99, player["overall"] + 1); player["fatigue"] = min(100, player["fatigue"] + 16)
        add_history(career, "decisão", "Você escolheu como lidar com a carga física.")
    else:
        if choice == "weak_foot": player["weak_foot"] = min(99, player["weak_foot"] + 3); player["fatigue"] = min(100, player["fatigue"] + 10)
        elif choice == "balanced": player["overall"] = min(99, player["overall"] + 1)
        else: player["fatigue"] = max(0, player["fatigue"] - 15); player["morale"] = min(100, player["morale"] + 3)
        player["ambidextrous"] = player["ambidextrous"] or player["weak_foot"] >= 85
        add_history(career, "decisão", "Você definiu o foco de treino da semana.")
    career["pending_event"] = None
    update_market_value(player)


def retire(career, reason):
    career["status"] = "finished"; career["retirement_reason"] = reason
    add_history(career, "aposentadoria", reason)


def final_card_svg(career):
    player = career["player"]
    club_lines = [f"{name}: {stats['matches']} J · {stats['goals']} G · {stats['assists']} A · {len(stats['titles'])} títulos" for name, stats in career["clubs"].items()]
    lines = club_lines[:7]
    title = escape(player["name"]); country = escape(player["country"]); position = escape(player["position"])
    rows = "".join(f'<text x="80" y="{390 + index * 42}" class="row">{escape(line)}</text>' for index, line in enumerate(lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760"><style>.bg{{fill:#07150e}}.card{{fill:#123324;stroke:#28523b;stroke-width:2}}.brand{{fill:#b7ef52;font:700 24px Arial}}.name{{fill:#fff;font:800 58px Arial}}.sub{{fill:#b6c8ba;font:24px Arial}}.label{{fill:#a8b9ad;font:700 17px Arial}}.value{{fill:#fff;font:800 32px Arial}}.row{{fill:#eef8f0;font:21px Arial}}</style><rect class="bg" width="1200" height="760"/><rect class="card" x="45" y="40" width="1110" height="680" rx="28"/><text x="80" y="95" class="brand">VIDA DE BOLEIRO · CARD DE CARREIRA</text><text x="80" y="170" class="name">{title}</text><text x="80" y="210" class="sub">{country} · {position} · aposentadoria aos {player['age']} anos</text><text x="80" y="285" class="label">JOGOS</text><text x="80" y="325" class="value">{player['matches']}</text><text x="300" y="285" class="label">GOLS</text><text x="300" y="325" class="value">{player['goals']}</text><text x="500" y="285" class="label">ASSISTÊNCIAS</text><text x="500" y="325" class="value">{player['assists']}</text><text x="760" y="285" class="label">OVR MÁX.</text><text x="760" y="325" class="value">{player['max_overall']}</text><text x="980" y="285" class="label">TÍTULOS</text><text x="980" y="325" class="value">{len(career['titles'])}</text><text x="80" y="365" class="brand">CLUBES</text>{rows}</svg>'''
