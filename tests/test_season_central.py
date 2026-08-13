import unittest

from app import app
from career_engine import create_career
from database import get_club_by_name
from season_central import build_season_central
from session_store import create


class SeasonCentralTests(unittest.TestCase):
    def career(self):
        club = get_club_by_name("Juventude", "BRA")
        return create_career("Central", "Brazil", "Centroavante", "Direita", club["name"], club_id=club["id"], mode="accelerated", seed=42)

    def test_central_uses_current_real_league_with_configured_zones(self):
        career = self.career()
        central = build_season_central(career)
        self.assertEqual(central["league"]["name"], "Campeonato Brasileiro Série B")
        self.assertEqual(len(central["table"]), 20)
        self.assertEqual(central["zones"]["promotion"], 4)
        self.assertEqual(central["zones"]["relegation"], 4)
        self.assertIn(career["club"], {row["club_name"] for row in central["table"]})

    def test_central_route_keeps_one_career_url_and_two_clients_are_isolated(self):
        first, second = app.test_client(), app.test_client()
        for client, name in ((first, "A"), (second, "B")):
            with client.session_transaction() as session:
                session["career_id"] = create(self.career() if name == "A" else create_career(name, "Brazil", "Goleiro", "Direita", "Juventude", club_id=get_club_by_name("Juventude", "BRA")["id"], seed=8))
        response = first.post("/career/season-central", data={"view": "standings"}, headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Classificação", response.get_json()["html"])
        self.assertIn("Central", first.get("/career").get_data(as_text=True))
        self.assertIn(">B<", second.get("/career").get_data(as_text=True))

    def test_health_and_import_are_safe_for_deploy(self):
        self.assertEqual(app.test_client().get("/health").get_json(), {"status": "ok"})
