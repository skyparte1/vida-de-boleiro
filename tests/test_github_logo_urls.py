import unittest

from github_logo_urls import RAW_BASE_URL, club_logo_url


class GithubLogoUrlTests(unittest.TestCase):
    def test_keeps_database_path_relative_and_builds_raw_url(self):
        self.assertEqual(
            club_logo_url("BRA/flamengo.png"),
            "https://raw.githubusercontent.com/skyparte1/vida-de-boleiro-logos/main/clubs/BRA/flamengo.png",
        )
        self.assertEqual(club_logo_url("clubs/BRA/flamengo.png"), RAW_BASE_URL + "BRA/flamengo.png")
        self.assertIsNone(club_logo_url(None))
        self.assertIsNone(club_logo_url("BRA/../flamengo.png"))
