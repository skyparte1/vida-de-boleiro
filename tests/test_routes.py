import unittest
import re

from app import app
from transfer_engine import build_accelerated_transfer_event


class RouteTests(unittest.TestCase):
    def create_client_career(self, mode):
        client = app.test_client()
        clubs = client.post("/api/starting-clubs", data={"country": "Brazil"}).get_json()["clubs"]
        response = client.post("/career/start", data={"name": "Rota", "country": "Brazil", "club_id": clubs[0]["id"], "position": "Centroavante", "dominant_foot": "Direita", "mode": mode})
        self.assertEqual(response.status_code, 302)
        return client

    def test_realistic_and_accelerated_creation(self):
        for mode in ("realistic", "accelerated"):
            client = self.create_client_career(mode)
            self.assertEqual(client.get("/career").status_code, 200)

    def test_all_database_countries_return_sqlite_clubs(self):
        countries = ("Argentina", "Belgium", "Brazil", "England", "France", "Germany", "Italy", "Netherlands", "Portugal", "Spain")
        client = app.test_client()
        for country in countries:
            payload = client.post("/api/starting-clubs", data={"country": country}).get_json()
            self.assertEqual(len(payload["clubs"]), 3)
            self.assertTrue(all(isinstance(club["id"], int) for club in payload["clubs"]))

    def test_career_keeps_club_id_name_and_logo(self):
        from session_store import get
        client = self.create_client_career("realistic")
        with client.session_transaction() as flask_session:
            career = get(flask_session["career_id"])
            self.assertIsInstance(career["club_id"], int)
            self.assertTrue(career["club"])
        page = client.get("/career").get_data(as_text=True)
        logo_url = re.search(r'src="(https://raw\.githubusercontent\.com/skyparte1/vida-de-boleiro-logos/main/clubs/[^" ]+)"', page)
        self.assertIsNotNone(logo_url)
        self.assertEqual(client.get("/career").status_code, 200)

    def test_refresh_and_repost_do_not_duplicate_decision(self):
        client = self.create_client_career("realistic")
        for _ in range(3):
            client.post("/career/advance-week")
            page = client.get("/career").get_data(as_text=True)
            if "DECISÃO PENDENTE" in page:
                break
            client.post("/career/decision", data={"choice": "continue"})
        self.assertIn("DECISÃO PENDENTE", client.get("/career").get_data(as_text=True))
        from session_store import get
        with client.session_transaction() as flask_session:
            career = get(flask_session["career_id"])
            event_id = career["pending_event"]["id"]
        client.post("/career/decision", data={"choice": "continue", "event_id": event_id})
        self.assertEqual(client.post("/career/decision", data={"choice": "continue", "event_id": event_id}).status_code, 400)

    def test_legacy_pending_event_receives_an_id_and_resolves(self):
        from session_store import get
        client = self.create_client_career("realistic")
        client.post("/career/advance-week")
        with client.session_transaction() as flask_session:
            career = get(flask_session["career_id"])
            career["pending_event"].pop("id")
        self.assertEqual(client.post("/career/decision", data={"choice": "weak_foot"}).status_code, 302)
        self.assertIsNone(career["pending_event"])

    def test_legacy_career_without_club_id_is_resolved_in_memory(self):
        from session_store import get
        client = self.create_client_career("realistic")
        with client.session_transaction() as flask_session:
            career = get(flask_session["career_id"])
            original_id = career.pop("club_id")
        self.assertEqual(client.get("/career").status_code, 200)
        self.assertEqual(career["club_id"], original_id)

    def test_accelerated_route_flow_to_summary_and_final_card(self):
        from session_store import get
        client = self.create_client_career("accelerated")
        self.assertIn("MODO ACELERADO", client.get("/career").get_data(as_text=True))
        self.assertEqual(client.post("/career/advance-week").status_code, 302)
        for _ in range(5):
            with client.session_transaction() as flask_session:
                career = get(flask_session["career_id"])
                event = career["pending_event"]
            if not event:
                break
            choice = event["choices"][0]["id"]
            self.assertEqual(client.post("/career/decision", data={"choice": choice, "event_id": event["id"]}).status_code, 302)
            if event["type"] == "season_summary":
                break
        self.assertGreaterEqual(career["calendar"]["season"], 1)
        career["player"]["age"] = 30
        self.assertEqual(client.post("/career/retire").status_code, 302)
        self.assertEqual(client.get("/career/final-card").status_code, 200)
        self.assertEqual(client.get("/career/final-card.svg").status_code, 200)

    def test_transfer_event_renders_database_logos_and_choices(self):
        from session_store import get
        client = self.create_client_career("accelerated")
        with client.session_transaction() as flask_session:
            career = get(flask_session["career_id"])
            career["player"]["overall"] = 82

            class DeterministicRng:
                def randint(self, low, high): return low
                def choices(self, population, weights=None, k=1): return [population[0]]

            career["pending_event"] = build_accelerated_transfer_event(career, DeterministicRng())
            event = career["pending_event"]
        page = client.get("/career").get_data(as_text=True)
        self.assertIn("Continuar no clube atual", page)
        self.assertIn(event["transfer_candidates"][0]["name"], page)
        self.assertIn("raw.githubusercontent.com/skyparte1/vida-de-boleiro-logos/main/clubs/", page)
        self.assertNotIn("static/club_logos/", page)
