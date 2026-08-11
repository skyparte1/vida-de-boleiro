import unittest

from database import (
    get_club,
    get_club_by_name,
    get_current_competition_for_club,
    get_clubs_by_competition,
    get_clubs_by_country,
    get_clubs_with_competition,
    get_competition,
    get_competitions_by_country,
)


class DatabaseQueryTests(unittest.TestCase):
    def test_club_queries_include_permanent_data(self):
        club = get_club_by_name("Flamengo", "BRA")
        self.assertIsNotNone(club)
        self.assertEqual(club["country"], "Brasil")
        self.assertTrue(club["logo"].startswith("BRA/"))
        self.assertEqual(get_club(club["id"])["name"], "Flamengo")

    def test_country_and_competition_queries(self):
        clubs = get_clubs_by_country("BRA")
        self.assertEqual(len(clubs), 156)
        competitions = get_competitions_by_country("BRA")
        league = next(item for item in competitions if item["name"] == "Campeonato Brasileiro Série A")
        self.assertEqual(get_competition(league["id"])["tier"], 1)
        participants = get_clubs_by_competition(league["id"], season=2026)
        self.assertEqual(len(participants), 20)
        self.assertTrue(all(item["country_code"] == "BRA" for item in participants))
        flamengo = get_club_by_name("Flamengo", "BRA")
        self.assertEqual(get_current_competition_for_club(flamengo["id"], 2026)["id"], league["id"])

    def test_clubs_with_competition_is_database_backed(self):
        clubs = get_clubs_with_competition(2026)
        self.assertEqual(len(clubs), 527)
        self.assertTrue(all(item["competition_id"] and item["competition_name"] for item in clubs))
        self.assertTrue(all(item["logo"] for item in clubs))
