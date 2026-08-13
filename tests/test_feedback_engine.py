import unittest

from career_engine import PLAYER_ACTIONS, create_career, perform_player_action, resolve_decision
from database import get_club_by_name
from feedback_engine import consume_pending_feedback, contextual_text, feedback_snapshot, set_pending_feedback
from narrative_engine import NARRATIVE_EVENTS, build_narrative_event, resolve_narrative_event


class FeedbackEngineTests(unittest.TestCase):
    def career(self):
        club = get_club_by_name("Juventude", "BRA")
        return create_career("Feedback", "Brazil", "Centroavante", "Direita", club["name"], club_id=club["id"], seed=71)

    def test_snapshot_feedback_only_lists_visible_changes(self):
        career = self.career()
        before = feedback_snapshot(career)
        career["player"]["morale"] += 4
        career["player"]["fatigue"] -= 5
        career["flags"]["internal_only"] = True
        feedback = set_pending_feedback(career, "training", "Teste", "Resultado", before)
        self.assertEqual({item["key"] for item in feedback["changes"]}, {"morale", "fatigue"})
        morale = next(item for item in feedback["changes"] if item["key"] == "morale")
        self.assertEqual((morale["before"], morale["after"], morale["delta"]), (68, 72, 4))

    def test_actions_and_outcomes_create_consumable_feedback_once(self):
        career = self.career()
        self.assertTrue(perform_player_action(career, "training", "finishing"))
        feedback = career["pending_feedback"]
        self.assertEqual(feedback["kind"], "training")
        self.assertTrue(feedback["changes"])
        outcome = career["pending_event"]
        self.assertTrue(consume_pending_feedback(career))
        self.assertIsNone(career["pending_feedback"])
        self.assertTrue(resolve_decision(career, "continue", outcome["id"]))
        self.assertFalse(consume_pending_feedback(career))

    def test_neutral_narrative_choice_has_feedback(self):
        career = self.career()
        event = build_narrative_event(career, "hair_change")
        career["pending_event"] = event
        self.assertTrue(resolve_decision(career, "keep_style"))
        self.assertEqual(career["pending_feedback"]["changes"], [])
        self.assertIn("cabelo", career["pending_feedback"]["text"].lower())

    def test_catalogue_and_actions_provide_contextual_result_copy(self):
        for actions in PLAYER_ACTIONS.values():
            for action in actions.values():
                self.assertTrue(action.get("result_text") or action.get("outcomes"))
        for event in NARRATIVE_EVENTS.values():
            for choice in event.get("choices", []):
                self.assertTrue(choice.get("result_text"))
                for outcome in choice.get("outcomes", []):
                    self.assertTrue(outcome.get("result_text"))

    def test_hair_feedback_uses_the_selected_outcome_copy(self):
        hair = NARRATIVE_EVENTS["hair_change"]
        change = next(choice for choice in hair["choices"] if choice["id"] == "change_style")
        self.assertEqual([outcome["result_title"] for outcome in change["outcomes"]], [
            "Novo visual", "Autoestima renovada", "Mudança desastrosa",
        ])
        keep = next(choice for choice in hair["choices"] if choice["id"] == "keep_style")
        self.assertEqual(keep["outcomes"][0]["result_title"], "Visual mantido")
        self.assertEqual(
            keep["outcomes"][0]["result_text"],
            "Você pensa melhor e decide deixar o cabelo como está. Nada muda na sua rotina.",
        )

    def test_selected_narrative_outcome_uses_its_contextual_copy(self):
        career = self.career()
        event = build_narrative_event(career, "hair_change")

        class LowestRoll:
            @staticmethod
            def random():
                return 0

        result = resolve_narrative_event(career, event, "change_style", LowestRoll())
        self.assertEqual(result["title"], "Novo visual")
        self.assertEqual(
            result["text"],
            "Você muda o visual e gosta do resultado. A novidade chama alguma atenção, mas sua rotina segue normalmente.",
        )

    def test_contextual_placeholders_are_safe_for_legacy_or_partial_data(self):
        career = self.career()
        self.assertEqual(
            contextual_text("{player_name} deixa o {old_club}.", career, old_club="Juventude"),
            "Feedback deixa o Juventude.",
        )
        self.assertEqual(contextual_text("Texto {campo_ausente}", career), "Texto {campo_ausente}")
