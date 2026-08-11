import unittest
from datetime import date

from career_engine import advance_career, create_career, final_card_svg, resolve_decision, retire
from database import get_club, get_club_by_name, get_clubs_by_competition, get_current_competition_for_club
from github_logo_urls import club_logo_url
from transfer_engine import (
    build_accelerated_transfer_event,
    can_complete_transfer,
    maybe_create_realistic_transfer_event,
    ranked_transfer_candidates,
    score_transfer_destination,
)


class AlwaysInterestedRng:
    def random(self):
        return 0

    def choices(self, population, weights=None, k=1):
        return [population[0] for _ in range(k)]

    def randint(self, low, high):
        return low


class CareerEngineTests(unittest.TestCase):
    def career(self, mode="realistic"):
        club = get_club_by_name("Juventude", "BRA")
        return create_career("Teste", "Brazil", "Centroavante", "Direita", club["name"], club_id=club["id"], mode=mode, seed=7)

    def resolve_current(self, career, choice=None):
        event = career["pending_event"]
        self.assertIsNotNone(event)
        resolve_decision(career, choice or event["choices"][0]["id"])

    def advance_to_realistic_match(self, career):
        for _ in range(3):
            advance_career(career)
            if career["pending_event"]["type"] == "match":
                return
            self.resolve_current(career)
        self.fail("Partida realista não foi iniciada")

    def test_realistic_creation_and_match_flow_is_idempotent(self):
        career = self.career()
        self.assertEqual(career["mode"], "realistic")
        self.advance_to_realistic_match(career)
        expected_matches = 1 if career["match_state"]["played"] else 0
        while career["pending_event"]:
            self.resolve_current(career)
        matches = career["player"]["matches"]
        self.assertEqual(matches, expected_matches)
        self.assertEqual(career["clubs"][career["club"]]["matches"], expected_matches)
        self.assertIsNone(career["match_state"])
        self.assertFalse(resolve_decision(career, "continue"))
        self.assertEqual(career["player"]["matches"], matches)
        advance_career(career)
        self.assertIsNotNone(career["pending_event"])

    def test_league_opponent_uses_current_competition(self):
        career = self.career()
        self.advance_to_realistic_match(career)
        match = career["match_state"]
        competition = get_current_competition_for_club(career["club_id"], 2026)
        participant_ids = {club["id"] for club in get_clubs_by_competition(competition["id"], 2026)}
        self.assertEqual(match["competition"], competition["name"])
        self.assertNotEqual(match["opponent_id"], career["club_id"])
        self.assertIn(match["opponent_id"], participant_ids)

    def test_accelerated_transfer_event_uses_multiple_database_clubs_once(self):
        career = self.career("accelerated")
        career["player"]["overall"] = 82
        event = build_accelerated_transfer_event(career, AlwaysInterestedRng())
        self.assertIsNotNone(event)
        self.assertGreaterEqual(len(event["transfer_candidates"]), 2)
        self.assertLessEqual(len(event["transfer_candidates"]), 6)
        self.assertNotIn(career["club_id"], {item["club_id"] for item in event["transfer_candidates"]})
        self.assertEqual(build_accelerated_transfer_event(career, AlwaysInterestedRng()), None)
        target = event["transfer_candidates"][0]
        self.assertEqual(get_club(target["club_id"])["name"], target["name"])
        self.assertTrue(target["logo"])
        self.assertEqual(target["logo_url"], club_logo_url(target["logo"]))
        self.assertTrue(target["logo_url"].startswith("https://raw.githubusercontent.com/"))
        self.assertTrue(target["competition"])
        career["pending_event"] = event
        resolve_decision(career, f"accept:{target['club_id']}")
        self.assertEqual(career["club_id"], target["club_id"])
        self.assertEqual(career["club"], target["name"])
        self.assertEqual(career["history"][0]["kind"], "transferência")

    def test_stay_and_realistic_cooldown(self):
        career = self.career("accelerated")
        event = build_accelerated_transfer_event(career, AlwaysInterestedRng())
        original = career["club_id"]
        career["pending_event"] = event
        resolve_decision(career, "stay")
        self.assertEqual(career["club_id"], original)

        career = self.career()
        event = maybe_create_realistic_transfer_event(career, AlwaysInterestedRng())
        self.assertIsNotNone(event)
        self.assertIn(event["transfer_stage"], {"watching", "inquiry", "proposal"})
        self.assertIsNone(maybe_create_realistic_transfer_event(career, AlwaysInterestedRng()))

    def test_score_and_windows_prevent_absurd_or_illegal_transfer(self):
        career = self.career()
        current = get_club(career["club_id"])
        giant = get_club_by_name("Flamengo", "BRA")
        career["player"]["overall"] = 55
        low_score = score_transfer_destination(career, current, giant, {"candidate_competition": get_current_competition_for_club(giant["id"], 2026)})
        career["player"]["overall"] = 89
        high_score = score_transfer_destination(career, current, giant, {"candidate_competition": get_current_competition_for_club(giant["id"], 2026)})
        self.assertGreater(high_score, low_score)
        career["calendar"]["date"] = date(2026, 3, 10).isoformat()
        foreign = get_club_by_name("Boca Juniors", "ARG")
        self.assertFalse(can_complete_transfer(career, foreign))
        self.assertTrue(can_complete_transfer(career, giant))

    def test_realistic_season_ends_once_after_final(self):
        career = self.career()
        career["season_match_count"] = 11
        career["realistic_activity_index"] = 2
        advance_career(career)
        while career["pending_event"] and career["pending_event"]["type"] == "match":
            self.resolve_current(career)
        self.assertEqual(career["pending_event"]["type"], "season_summary")
        season = career["calendar"]["season"]
        self.resolve_current(career, "next_season")
        self.assertEqual(career["calendar"]["season"], season + 1)

    def test_accelerated_season_queues_only_important_events(self):
        career = self.career("accelerated")
        advance_career(career)
        self.assertGreaterEqual(career["player"]["matches"], 1)
        events = [career["pending_event"], *career["event_queue"]]
        self.assertEqual(sum(item["type"] == "training" for item in events), 1)
        self.assertEqual(sum(item["type"] == "season_final" for item in events), 1)
        self.assertEqual(events[-1]["type"], "season_summary")
        while career["pending_event"] and career["pending_event"]["type"] != "season_summary":
            self.resolve_current(career)
        self.assertEqual(career["pending_event"]["type"], "season_summary")
        old_season = career["calendar"]["season"]
        self.resolve_current(career, "next_season")
        self.assertEqual(career["calendar"]["season"], old_season + 1)
        advance_career(career)
        self.assertIsNotNone(career["pending_event"])

    def test_multiple_accelerated_seasons_retirement_and_card(self):
        career = self.career("accelerated")
        for _ in range(3):
            advance_career(career)
            while career["pending_event"]:
                self.resolve_current(career)
        self.assertEqual(career["player"]["age"], 19)
        career["player"]["age"] = 30
        retire(career, "Teste de aposentadoria.")
        self.assertEqual(career["status"], "finished")
        self.assertIn("Teste", final_card_svg(career))
