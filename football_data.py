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

FIFA_ASSOCIATIONS = {
    "CAF": "Algeria|Angola|Benin|Botswana|Burkina Faso|Burundi|Cabo Verde|Cameroon|Central African Republic|Chad|Comoros|Congo|Congo DR|Cote d'Ivoire|Djibouti|Egypt|Equatorial Guinea|Eritrea|Eswatini|Ethiopia|Gabon|The Gambia|Ghana|Guinea|Guinea-Bissau|Kenya|Lesotho|Liberia|Libya|Madagascar|Malawi|Mali|Mauritania|Mauritius|Morocco|Mozambique|Namibia|Niger|Nigeria|Rwanda|Sao Tome and Principe|Senegal|Seychelles|Sierra Leone|Somalia|South Africa|South Sudan|Sudan|Tanzania|Togo|Tunisia|Uganda|Zambia|Zimbabwe".split("|"),
    "AFC": "Afghanistan|Australia|Bahrain|Bangladesh|Bhutan|Brunei Darussalam|Cambodia|China PR|Chinese Taipei|Guam|Hong Kong, China|India|Indonesia|IR Iran|Iraq|Japan|Jordan|DPR Korea|Korea Republic|Kuwait|Kyrgyz Republic|Laos|Lebanon|Macau|Malaysia|Maldives|Mongolia|Myanmar|Nepal|Oman|Pakistan|Palestine|Philippines|Qatar|Saudi Arabia|Singapore|Sri Lanka|Syria|Tajikistan|Thailand|Timor-Leste|Turkmenistan|United Arab Emirates|Uzbekistan|Vietnam|Yemen".split("|"),
    "UEFA": "Albania|Andorra|Armenia|Austria|Azerbaijan|Belarus|Belgium|Bosnia and Herzegovina|Bulgaria|Croatia|Cyprus|Czechia|Denmark|England|Estonia|Faroe Islands|Finland|France|Georgia|Germany|Gibraltar|Greece|Hungary|Iceland|Israel|Italy|Kazakhstan|Kosovo|Latvia|Liechtenstein|Lithuania|Luxembourg|Malta|Moldova|Montenegro|Netherlands|North Macedonia|Northern Ireland|Norway|Poland|Portugal|Republic of Ireland|Romania|Russia|San Marino|Scotland|Serbia|Slovakia|Slovenia|Spain|Sweden|Switzerland|Türkiye|Ukraine|Wales".split("|"),
    "CONCACAF": "Anguilla|Antigua and Barbuda|Aruba|Bahamas|Barbados|Belize|Bermuda|British Virgin Islands|Canada|Cayman Islands|Costa Rica|Cuba|Curacao|Dominica|Dominican Republic|El Salvador|Grenada|Guatemala|Guyana|Haiti|Honduras|Jamaica|Mexico|Montserrat|Nicaragua|Panama|Puerto Rico|St Kitts and Nevis|St Lucia|St Vincent and the Grenadines|Suriname|Trinidad and Tobago|Turks and Caicos Islands|US Virgin Islands|USA".split("|"),
    "CONMEBOL": "Argentina|Bolivia|Brazil|Chile|Colombia|Ecuador|Paraguay|Peru|Uruguay|Venezuela".split("|"),
    "OFC": "American Samoa|Cook Islands|Fiji|New Caledonia|New Zealand|Papua New Guinea|Samoa|Solomon Islands|Tahiti|Tonga|Vanuatu".split("|"),
}

FALLBACK_LEAGUE = {"CAF": "Portugal", "AFC": "Japão", "UEFA": "Portugal", "CONCACAF": "México", "CONMEBOL": "Argentina", "OFC": "Japão"}
COUNTRY_CONTEXT = {country: (confederation, FALLBACK_LEAGUE[confederation]) for confederation, members in FIFA_ASSOCIATIONS.items() for country in members}
COUNTRY_CONTEXT.update({"Brazil": ("CONMEBOL", "Brasil"), "Colombia": ("CONMEBOL", "Colômbia"), "France": ("UEFA", "França"), "Spain": ("UEFA", "Espanha"), "Italy": ("UEFA", "Itália"), "Mexico": ("CONCACAF", "México"), "Japan": ("AFC", "Japão"), "South Korea": ("AFC", "Coreia do Sul")})


def countries():
    return {confederation: sorted(members) for confederation, members in FIFA_ASSOCIATIONS.items()}


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


def is_known_club(club_name):
    return any(club_name == name for league in LEAGUES.values() for name, _ in league["clubs"])


def random_club(minimum_size="small", exclude=None):
    order = {"small": 0, "medium": 1, "big": 2}
    options = [(name, size) for league in LEAGUES.values() for name, size in league["clubs"] if name != exclude and order[size] >= order[minimum_size]]
    return random.choice(options)
