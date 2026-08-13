import random
import unittest

from competition_engine import (
    calculate_match_importance,
    create_cup_state,
    create_league_state,
    current_league_state,
    finalize_country_season,
    generate_league_schedule,
    play_cup_round,
    record_league_result,
    simulate_fixture,
    standings_rows,
)
from career_engine import advance_career, create_career, resolve_decision
from database import get_club_by_name, get_clubs_by_competition, get_current_competition_for_club


class CompetitionEngineTests(unittest.TestCase):
    def test_round_robin_has_each_pair_twice_without_self_fixture(self):
        rounds = generate_league_schedule([1, 2, 3, 4], 10)
        fixtures = [fixture for group in rounds for fixture in group]
        self.assertEqual(len(fixtures), 12)
        self.assertTrue(all(item["home"] != item["away"] for item in fixtures))
        pairs = {frozenset((item["home"], item["away"])) for item in fixtures}
        self.assertEqual(len(pairs), 6)
        self.assertTrue(all(sum(frozenset((item["home"], item["away"])) == pair for item in fixtures) == 2 for pair in pairs))

    def test_table_records_points_goals_and_tiebreakers(self):
        state = create_league_state({"id": 1, "name": "Teste", "country_code": "BRA", "tier": 1}, [{"id": i} for i in (1, 2, 3, 4)])
        first = state["fixtures"][0][0]
        self.assertTrue(record_league_result(state, first, 2, 1))
        self.assertFalse(record_league_result(state, first, 2, 1))
        home = state["standings"][str(first["home"])]
        away = state["standings"][str(first["away"])]
        self.assertEqual((home["points"], home["played"], home["wins"], home["goals_for"], home["goals_against"]), (3, 1, 1, 2, 1))
        self.assertEqual((away["points"], away["losses"], away["goals_for"]), (0, 1, 1))
        self.assertEqual(standings_rows(state)[0]["club_id"], first["home"])

    def test_strength_and_seed_make_results_deterministic_without_guarantees(self):
        strong, weak = get_club_by_name("Flamengo", "BRA")["id"], get_club_by_name("Juventude", "BRA")["id"]
        self.assertEqual(simulate_fixture(strong, weak, random.Random(9)), simulate_fixture(strong, weak, random.Random(9)))
        results = [simulate_fixture(strong, weak, random.Random(seed)) for seed in range(80)]
        self.assertGreater(sum(home > away for home, away in results), sum(home < away for home, away in results))
        self.assertTrue(any(home < away for home, away in results))

    def test_cup_eliminates_loser_and_finishes_with_a_champion(self):
        cup = create_cup_state("cup", "Copa", "BRA", [1, 2, 3, 4, 5])
        while cup["status"] == "active":
            play_cup_round(cup, random.Random(len(cup["fixtures"]) + 2))
        self.assertEqual(len(cup["active"]), 1)
        self.assertIn(cup["champion"], {1, 2, 3, 4, 5})
        self.assertEqual(len(cup["eliminated"]), 4)

    def test_accelerated_career_uses_real_league_and_next_season_keeps_division(self):
        club = get_club_by_name("Juventude", "BRA")
        career = create_career("B1", "Brazil", "Centroavante", "Direita", club["name"], club_id=club["id"], mode="accelerated", seed=17)
        advance_career(career)
        league = career["season_competitions"]["league"]
        self.assertEqual(league["played"], len(get_clubs_by_competition(league["id"], 2026)) * 2 - 2)
        self.assertEqual(league["status"], "finished")
        while career["pending_event"]:
            resolve_decision(career, career["pending_event"]["choices"][0]["id"])
        next_league = current_league_state(career)
        self.assertIsNotNone(next_league)
        self.assertEqual(next_league["completed_rounds"], 0)

    def test_final_and_last_round_are_important(self):
        cup = create_cup_state("cup", "Copa", "BRA", [1, 2])
        self.assertEqual(calculate_match_importance(cup, {"stage": "Final"}, 1)["reason"], "final")
        state = create_league_state({"id": 1, "name": "Teste", "country_code": "BRA", "tier": 1}, [{"id": i} for i in (1, 2, 3, 4)])
        state["completed_rounds"] = len(state["fixtures"]) - 1
        self.assertTrue(calculate_match_importance(state, state["fixtures"][-1][0], 1)["important"])

    def test_promotion_and_relegation_change_the_next_season_division(self):
        club = get_club_by_name("Juventude", "BRA")
        career = create_career("Acesso", "Brazil", "Centroavante", "Direita", club["name"], club_id=club["id"], mode="accelerated", seed=23)
        country = career["competition_world"]["countries"]["BRA"]
        for state in country["leagues"].values():
            state["status"] = "finished"
        series_b = current_league_state(career)
        series_b["standings"][str(club["id"])]["points"] = 999
        self.assertTrue(finalize_country_season(career))
        self.assertEqual(career["competition_world"]["club_divisions"][str(club["id"])], 1)
