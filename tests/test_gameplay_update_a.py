import unittest

from career_engine import (
    _simulate_match_result,
    _end_season,
    available_player_actions,
    create_career,
    ensure_career_state,
    perform_player_action,
    recalculate_squad_status,
    advance_career,
    resolve_decision,
)
from database import get_club_by_name
from transfer_engine import resolve_transfer_decision


class GameplayUpdateATests(unittest.TestCase):
    def career(self, club_name="Juventude", country_code="BRA", seed=23):
        club = get_club_by_name(club_name, country_code)
        return create_career("Ação", "Brazil", "Centroavante", "Direita", club["name"], club_id=club["id"], seed=seed)

    def test_actions_are_limited_by_category_and_not_by_date(self):
        career = self.career()
        fatigue, points = career["player"]["fatigue"], career["development_points"]
        self.assertIn("finishing", available_player_actions(career)["training"])
        self.assertTrue(perform_player_action(career, "training", "finishing"))
        self.assertGreater(career["player"]["fatigue"], fatigue)
        self.assertGreater(career["development_points"], points)
        self.assertEqual(career["player"]["overall"], career["season_started"]["overall"])
        self.assertTrue(resolve_decision(career, "continue", career["pending_event"]["id"]))
        self.assertTrue(perform_player_action(career, "rest", "rest"))
        self.assertTrue(resolve_decision(career, "continue", career["pending_event"]["id"]))
        self.assertFalse(perform_player_action(career, "training", "passing"))
        self.assertTrue(career["season_actions_used"]["training"])
        self.assertTrue(career["season_actions_used"]["rest"])

    def test_rest_recovers_and_conditions_block_unavailable_actions(self):
        career = self.career()
        career["player"]["fatigue"] = 65
        self.assertTrue(perform_player_action(career, "rest", "rest"))
        self.assertLess(career["player"]["fatigue"], 65)
        other = self.career(seed=24)
        self.assertNotIn("tattoo", available_player_actions(other)["personal"])
        self.assertFalse(perform_player_action(other, "personal", "tattoo"))

    def test_each_action_category_is_available_once_and_resets_next_season(self):
        career = self.career(seed=53)
        actions = [("training", "general"), ("rest", "rest"), ("career", "review"),
                   ("locker_room", "talk"), ("media", "interview"), ("personal", "hair")]
        for category, action in actions:
            self.assertTrue(perform_player_action(career, category, action))
            if career["pending_event"]:
                self.assertTrue(resolve_decision(career, "continue", career["pending_event"]["id"]))
        self.assertTrue(all(career["season_actions_used"].values()))
        self.assertFalse(perform_player_action(career, "media", "fans"))
        _end_season(career)
        self.assertTrue(all(not used for used in career["season_actions_used"].values()))

    def test_legacy_defaults_and_season_event_target(self):
        career = self.career()
        for key in ("squad_status", "development_points", "season_actions_used", "season_random_events_target"):
            career.pop(key)
        ensure_career_state(career)
        self.assertIn(career["squad_status"], {"out_of_plans", "reserve", "rotation", "starter", "key_player", "star"})
        self.assertIn(career["season_random_events_target"], {2, 3})
        self.assertEqual(career["season_random_events_count"], 0)
        self.assertEqual(career["season_actions_used"], {category: False for category in available_player_actions(career)})

    def test_club_strength_changes_squad_status_after_transfer(self):
        career = self.career()
        career["player"].update({"overall": 68, "form": 65, "morale": 65})
        recalculate_squad_status(career, force=True)
        before = career["squad_status"]
        giant = get_club_by_name("Flamengo", "BRA")
        event = {"transfer_candidates": [{"club_id": giant["id"], "can_complete": True}]}
        self.assertTrue(resolve_transfer_decision(career, event, f"accept:{giant['id']}"))
        self.assertLessEqual(("out_of_plans", "reserve", "rotation", "starter", "key_player", "star").index(career["squad_status"]),
                             ("out_of_plans", "reserve", "rotation", "starter", "key_player", "star").index(before))

    def test_status_changes_participation_and_development_opportunity(self):
        career = self.career(seed=31)
        career["squad_status"] = "reserve"
        reserve_matches = sum(_simulate_match_result(career)["played"] for _ in range(40))
        career["squad_status"] = "starter"
        starter_matches = sum(_simulate_match_result(career)["played"] for _ in range(40))
        self.assertGreater(starter_matches, reserve_matches)

    def test_high_fatigue_reduces_training_efficiency(self):
        fresh = self.career(seed=37)
        tired = self.career(seed=37)
        tired["player"]["fatigue"] = 75
        self.assertTrue(perform_player_action(fresh, "training", "general"))
        self.assertTrue(perform_player_action(tired, "training", "general"))
        self.assertGreater(fresh["development_points"], tired["development_points"])

    def test_accelerated_season_uses_only_normal_random_events_up_to_target(self):
        career = self.career(seed=41)
        career["mode"] = "accelerated"
        target = career["season_random_events_target"]
        advance_career(career)
        random_events = [event for event in [career["pending_event"], *career["event_queue"]] if event.get("random_event")]
        self.assertLessEqual(len(random_events), target)
        self.assertEqual(career["season_random_events_count"], len(random_events))
        self.assertTrue(all(event["rarity"] in {"common", "uncommon", "rare"} for event in random_events))
        self.assertTrue(all(not any("terminal" in choice.get("effects", {}) for choice in event["choices"]) for event in random_events))
        while career["pending_event"]:
            event = career["pending_event"]
            resolve_decision(career, event["choices"][0]["id"])
        self.assertIn(career["season_random_events_target"], {2, 3})
        self.assertEqual(career["season_random_events_count"], 0)
