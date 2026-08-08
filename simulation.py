import random
from datetime import date


def create_player(name, age, country, position, dominant_foot, club):
    technical = random.randint(52, 68)
    return {
        "name": name.strip(), "age": age, "country": country, "position": position,
        "club": club, "dominant_foot": dominant_foot, "weak_foot": random.randint(30, 50),
        "overall": technical, "season": date.today().year, "matches": 0, "goals": 0,
        "assists": 0, "money": 15000, "ambidextrous": False,
        "last_event": "Sua carreira profissional começou. O treinador quer observar você nos próximos jogos.",
    }


def advance_season(player):
    player = player.copy()
    player["season"] += 1
    player["age"] += 1
    appearances = random.randint(12, 34)
    player["matches"] += appearances
    player["goals"] += random.randint(0, 14) if player["position"] != "Goleiro" else 0
    player["assists"] += random.randint(0, 10)
    player["money"] += random.randint(35000, 140000)
    growth = random.choice([0, 1, 1, 2, 2, 3]) if player["age"] < 29 else random.choice([-2, -1, 0, 0, 1])
    player["overall"] = max(35, min(99, player["overall"] + growth))
    foot_growth = random.choice([0, 1, 1, 2, 3])
    player["weak_foot"] = min(99, player["weak_foot"] + foot_growth)
    if player["weak_foot"] >= 85:
        player["ambidextrous"] = True
        player["last_event"] = "Após anos de treino específico, você passou a ser reconhecido como um jogador ambidestro."
    else:
        events = [
            "Você ganhou espaço no elenco após uma boa sequência de atuações.",
            "O clube renovou sua confiança: a comissão técnica elogiou seu profissionalismo.",
            "Você dedicou parte da pré-temporada a treinar a perna não dominante.",
            "Uma atuação decisiva chamou a atenção da imprensa local.",
        ]
        player["last_event"] = random.choice(events)
    return player
