import random


# A base cresce sem mudar a regra: cada clube informa seu porte e sua liga.
LEAGUES = {
    "Brasil": {"continent": "América do Sul", "clubs": [("Juventude", "small"), ("Mirassol", "small"), ("Criciúma", "small"), ("Athletico Paranaense", "medium"), ("Bahia", "medium"), ("Flamengo", "big"), ("Palmeiras", "big")]},
    "Argentina": {"continent": "América do Sul", "clubs": [("Godoy Cruz", "small"), ("Tigre", "small"), ("Sarmiento", "small"), ("Lanús", "medium"), ("Vélez", "medium"), ("River Plate", "big"), ("Boca Juniors", "big")]},
    "Uruguai": {"continent": "América do Sul", "clubs": [("Cerro Largo", "small"), ("Plaza Colonia", "small"), ("Progreso", "small"), ("Defensor Sporting", "medium"), ("Nacional", "big")]},
    "Colômbia": {"continent": "América do Sul", "clubs": [("Envigado", "small"), ("Patriotas", "small"), ("Boyacá Chicó", "small"), ("Deportivo Cali", "medium"), ("Atlético Nacional", "big")]},
    "Inglaterra": {"continent": "Europa", "clubs": [("Plymouth Argyle", "small"), ("Oxford United", "small"), ("Preston North End", "small"), ("Brentford", "medium"), ("Brighton", "medium"), ("Arsenal", "big"), ("Manchester City", "big")]},
    "Espanha": {"continent": "Europa", "clubs": [("Mirandés", "small"), ("Eibar", "small"), ("Albacete", "small"), ("Rayo Vallecano", "medium"), ("Real Betis", "medium"), ("Real Madrid", "big"), ("Barcelona", "big")]},
    "Portugal": {"continent": "Europa", "clubs": [("Casa Pia", "small"), ("Estrela da Amadora", "small"), ("Farense", "small"), ("Vitória SC", "medium"), ("Braga", "medium"), ("Benfica", "big"), ("Porto", "big")]},
    "França": {"continent": "Europa", "clubs": [("Pau FC", "small"), ("Annecy", "small"), ("Rodez", "small"), ("Lens", "medium"), ("Lille", "medium"), ("PSG", "big")]},
    "Alemanha": {"continent": "Europa", "clubs": [("Ulm", "small"), ("Elversberg", "small"), ("Paderborn", "small"), ("Freiburg", "medium"), ("Eintracht Frankfurt", "medium"), ("Bayern de Munique", "big")]},
    "Itália": {"continent": "Europa", "clubs": [("Cittadella", "small"), ("Südtirol", "small"), ("Reggiana", "small"), ("Torino", "medium"), ("Bologna", "medium"), ("Inter de Milão", "big")]},
    "México": {"continent": "América do Norte", "clubs": [("Mazatlán", "small"), ("Puebla", "small"), ("Querétaro", "small"), ("Toluca", "medium"), ("Pachuca", "medium"), ("Club América", "big")]},
    "Estados Unidos": {"continent": "América do Norte", "clubs": [("Colorado Rapids", "small"), ("Austin FC", "small"), ("Nashville SC", "small"), ("Seattle Sounders", "medium"), ("LA Galaxy", "big")]},
    "Japão": {"continent": "Ásia", "clubs": [("Shonan Bellmare", "small"), ("Sagan Tosu", "small"), ("Albirex Niigata", "small"), ("Cerezo Osaka", "medium"), ("Kawasaki Frontale", "big")]},
    "Coreia do Sul": {"continent": "Ásia", "clubs": [("Gwangju FC", "small"), ("Gangwon FC", "small"), ("Daejeon Hana Citizen", "small"), ("FC Seoul", "medium"), ("Ulsan HD", "big")]},
}

COUNTRY_CONTEXT = {
    "Brasil": ("América do Sul", "Brasil"), "Argentina": ("América do Sul", "Argentina"), "Uruguai": ("América do Sul", "Argentina"), "Colômbia": ("América do Sul", "Colômbia"), "Chile": ("América do Sul", "Argentina"), "Peru": ("América do Sul", "Colômbia"),
    "Portugal": ("Europa", "Portugal"), "Espanha": ("Europa", "Espanha"), "França": ("Europa", "França"), "Inglaterra": ("Europa", "Inglaterra"), "Itália": ("Europa", "Itália"), "Alemanha": ("Europa", "Alemanha"), "Bélgica": ("Europa", "França"), "Holanda": ("Europa", "Alemanha"),
    "México": ("América do Norte", "México"), "Estados Unidos": ("América do Norte", "Estados Unidos"), "Canadá": ("América do Norte", "Estados Unidos"),
    "Japão": ("Ásia", "Japão"), "Coreia do Sul": ("Ásia", "Coreia do Sul"), "China": ("Ásia", "Japão"),
}


def countries():
    return sorted(COUNTRY_CONTEXT)


def build_starting_clubs(country):
    continent, closest_league = COUNTRY_CONTEXT[country]
    league_country = country if country in LEAGUES else closest_league
    if league_country not in LEAGUES:
        league_country = next(name for name, league in LEAGUES.items() if league["continent"] == continent)
    clubs = LEAGUES[league_country]["clubs"]
    weighted = {"small": 85, "medium": 14, "big": 1}
    chosen = []
    while len(chosen) < 3:
        club = random.choices(clubs, weights=[weighted[size] for _, size in clubs], k=1)[0]
        if club[0] not in {item["name"] for item in chosen}:
            chosen.append({"name": club[0], "size": club[1], "league_country": league_country})
    return chosen
