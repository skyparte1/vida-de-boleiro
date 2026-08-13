import unittest
from datetime import date, timedelta

from career_engine import _queue_event, advance_career, create_career, ensure_career_state, resolve_decision
from career_lifecycle import die
from database import get_club_by_name, get_clubs_by_country
from narrative_engine import (
    NARRATIVE_EVENTS,
    RARITY_WEIGHTS,
    apply_event_effects,
    build_narrative_event,
    due_follow_up_events,
    evaluate_nicknames,
    event_is_eligible,
    maybe_create_narrative_event,
    schedule_follow_up,
)
from transfer_engine import resolve_transfer_decision


class NarrativeEngineTests(unittest.TestCase):
    def career(self, mode="realistic"):
        club = get_club_by_name("Juventude", "BRA")
        return create_career("Narrativo", "Brazil", "Centroavante", "Direita", club["name"], club_id=club["id"], mode=mode, seed=17)

    def resolve_event(self, career, event, choice):
        career["pending_event"] = event
        self.assertTrue(resolve_decision(career, choice))

    def test_new_and_legacy_careers_have_narrative_defaults(self):
        career = self.career()
        self.assertEqual(career["reputation"], {
            "locker_room": 0, "fans": 0, "media": 0, "discipline": 0,
            "controversy": 0, "leadership": 0,
        })
        self.assertEqual(career["flags"], {})
        self.assertEqual(career["nicknames"], [])
        for key in ("reputation", "flags", "nicknames", "behavior", "event_cooldowns"):
            career.pop(key)
        ensure_career_state(career)
        self.assertEqual(career["reputation"]["media"], 0)
        self.assertEqual(career["behavior"]["authoritarian_choices"], 0)

    def test_conditions_gate_events_until_state_qualifies(self):
        career = self.career()
        authority = NARRATIVE_EVENTS["locker_room_authority"]
        self.assertFalse(event_is_eligible(career, authority))
        career["player"]["age"] = 17
        career["reputation"]["leadership"] = 8
        self.assertTrue(event_is_eligible(career, authority))
        self.assertIsNotNone(build_narrative_event(career, "locker_room_authority"))

    def test_declarative_event_is_filtered_and_resolved_without_special_case(self):
        career = self.career()
        event = {
            "id": "custom_authority", "type": "dressing_room", "title": "Quem manda aqui?", "text": "...",
            "conditions": {"min_reputation": {"leadership": 2}},
            "choices": [{"id": "impose", "label": "Impor autoridade", "effects": {"reputation": {"leadership": 5, "locker_room": -6}, "behavior": {"authoritarian_choices": 1}, "set_flags": ["tested_declarative_event"]}}],
        }
        self.assertFalse(_queue_event(career, event))
        career["reputation"]["leadership"] = 2
        self.assertTrue(_queue_event(career, event))
        career["pending_event"] = career["event_queue"].pop()
        self.assertTrue(resolve_decision(career, "impose", career["pending_event"]["id"]))
        self.assertEqual(career["reputation"]["leadership"], 7)
        self.assertEqual(career["behavior"]["authoritarian_choices"], 1)
        self.assertTrue(career["flags"]["tested_declarative_event"])

    def test_decision_applies_reputation_flags_behavior_and_cooldown(self):
        career = self.career()
        event = build_narrative_event(career, "locker_room_fight")
        self.resolve_event(career, event, "blame_teammate")
        self.assertEqual(career["reputation"]["locker_room"], -10)
        self.assertEqual(career["reputation"]["controversy"], 8)
        self.assertTrue(career["flags"]["public_locker_room_conflict"])
        self.assertEqual(career["behavior"]["locker_room_conflicts"], 1)
        self.assertIn("locker_room_fight", career["event_cooldowns"])
        self.assertFalse(event_is_eligible(career, NARRATIVE_EVENTS["locker_room_fight"]))

    def test_unique_event_and_follow_up_queue(self):
        career = self.career()
        fight = build_narrative_event(career, "locker_room_fight")
        self.resolve_event(career, fight, "blame_teammate")
        self.assertEqual(career["scheduled_follow_ups"][0]["event_key"], "locker_room_backlash")
        career["calendar"]["date"] = (date.fromisoformat(career["calendar"]["date"]) + timedelta(weeks=3)).isoformat()
        follow_ups = due_follow_up_events(career)
        self.assertEqual(follow_ups[0]["event_key"], "locker_room_backlash")
        self.resolve_event(career, follow_ups[0], "reconcile")
        self.assertIn("locker_room_backlash", career["event_seen"])
        self.assertFalse(event_is_eligible(career, NARRATIVE_EVENTS["locker_room_backlash"]))

    def test_overdue_ineligible_follow_up_is_retried_until_it_can_be_emitted(self):
        career = self.career()
        schedule_follow_up(career, {"event_key": "locker_room_backlash"})

        self.assertEqual(due_follow_up_events(career), [])
        self.assertEqual(len(career["scheduled_follow_ups"]), 1)

        career["flags"]["public_locker_room_conflict"] = True
        events = due_follow_up_events(career)

        self.assertEqual(events[0]["event_key"], "locker_room_backlash")
        self.assertEqual(career["scheduled_follow_ups"], [])

    def test_club_size_conditions_follow_the_current_database_club_after_transfer(self):
        clubs = get_clubs_by_country("BRA")
        small = next(club for club in clubs if (club["reputation"] + club["strength"]) / 2 < 56)
        big = next(club for club in clubs if (club["reputation"] + club["strength"]) / 2 >= 73)
        career = self.career()
        career["club_id"] = small["id"]
        career["club"] = small["name"]

        small_club_event = {"id": "small_club_event", "conditions": {"club_size": "small"}}
        big_club_event = {"id": "big_club_event", "conditions": {"club_size": "big"}}
        self.assertTrue(event_is_eligible(career, small_club_event))
        self.assertFalse(event_is_eligible(career, big_club_event))

        transfer_event = {"transfer_candidates": [{"club_id": big["id"], "can_complete": True}]}
        self.assertTrue(resolve_transfer_decision(career, transfer_event, f"accept:{big['id']}"))
        self.assertEqual(career["club_id"], big["id"])
        self.assertTrue(event_is_eligible(career, big_club_event))

    def test_dictator_is_granted_once_after_behavior_threshold(self):
        career = self.career()
        career["behavior"]["authoritarian_choices"] = 3
        career["reputation"].update({"leadership": 12, "locker_room": -12})
        evaluate_nicknames(career)
        evaluate_nicknames(career)
        self.assertEqual(career["nicknames"], ["Ditador"])
        self.assertEqual(sum(item["kind"] == "apelido" for item in career["history"]), 1)

    def test_follow_up_supports_months_and_next_season(self):
        career = self.career()
        schedule_follow_up(career, {"event_key": "hair_change", "after_months": 1})
        career["calendar"]["date"] = (date.fromisoformat(career["calendar"]["date"]) + timedelta(weeks=4)).isoformat()
        self.assertEqual(due_follow_up_events(career)[0]["event_key"], "hair_change")

        career["player"]["age"] = 17
        schedule_follow_up(career, {"event_key": "reporter_argument", "next_season": True})
        self.assertEqual(due_follow_up_events(career), [])
        career["calendar"]["season"] += 1
        self.assertEqual(due_follow_up_events(career)[0]["event_key"], "reporter_argument")

    def test_both_modes_and_match_flow_continue_after_narrative_state(self):
        realistic = self.career("realistic")
        accelerated = self.career("accelerated")
        advance_career(realistic)
        self.assertIsNotNone(realistic["pending_event"])
        advance_career(accelerated)
        self.assertIsNotNone(accelerated["pending_event"])

    def test_catalogue_uses_unique_keys_supported_shapes_and_existing_follow_ups(self):
        supported_conditions = {
            "min_age", "max_age", "min_overall", "max_overall", "min_morale", "max_morale", "min_form", "max_form",
            "min_fatigue", "max_fatigue", "min_matches", "max_matches", "min_games", "max_games", "min_goals", "max_goals",
            "min_titles", "max_titles", "country", "excluded_countries", "club", "club_size", "mode", "status",
            "without_club", "international_travel", "min_reputation", "max_reputation", "min_behavior", "max_behavior",
            "required_flags", "absent_flags", "has_nicknames", "without_nicknames",
        }
        supported_effects = {"player", "morale", "form", "fatigue", "overall", "weak_foot", "reputation", "behavior",
                             "set_flags", "clear_flags", "nicknames", "history", "follow_ups", "terminal"}
        self.assertEqual(len(NARRATIVE_EVENTS), len({event["key"] for event in NARRATIVE_EVENTS.values()}))
        for key, event in NARRATIVE_EVENTS.items():
            self.assertEqual(event["key"], key)
            self.assertIn(event["rarity"], RARITY_WEIGHTS)
            self.assertTrue(event.get("disabled") or event["choices"])
            self.assertTrue(set(event.get("conditions", {})).issubset(supported_conditions))
            for choice in event["choices"]:
                self.assertTrue(choice["id"])
                effects = choice.get("effects", {})
                self.assertTrue(set(effects).issubset(supported_effects))
                for follow_up in effects.get("follow_ups", []):
                    self.assertIn(follow_up["event_key"], NARRATIVE_EVENTS)
                if "terminal" in effects:
                    self.assertIn(effects["terminal"]["type"], {"retirement", "death"})

    def test_rarity_is_weighted_and_contextual_events_stay_blocked(self):
        career = self.career()
        self.assertGreater(RARITY_WEIGHTS["common"], RARITY_WEIGHTS["legendary"] * 50)
        self.assertIsNone(build_narrative_event(career, "fake_passport"))
        self.assertIsNone(build_narrative_event(career, "plane_crash"))
        career["player"].update({"country": "Argentina", "overall": 80, "matches": 30})
        self.assertFalse(event_is_eligible(career, NARRATIVE_EVENTS["ishowspeed_video"]))
        self.assertFalse(event_is_eligible(career, NARRATIVE_EVENTS["reporter_aftermath"]))
        self.assertFalse(event_is_eligible(career, NARRATIVE_EVENTS["gambling_all_salary"]))

    def test_terminal_death_is_idempotent_and_stops_every_career_flow(self):
        career = self.career()
        legacy = self.career()
        legacy.pop("death")
        ensure_career_state(legacy)
        self.assertIsNone(legacy["death"])
        schedule_follow_up(career, {"event_key": "hair_change"})
        apply_event_effects(career, {"terminal": {"type": "death", "reason": "Acidente de teste."}, "event_id": "fatal-test"})
        self.assertEqual(career["status"], "deceased")
        self.assertEqual(career["death"], {"reason": "Acidente de teste.", "date": career["calendar"]["date"], "age": 16, "event_id": "fatal-test"})
        self.assertEqual(career["scheduled_follow_ups"], [])
        self.assertEqual(career["history"][0]["kind"], "falecimento")
        previous_date, previous_matches, death = career["calendar"]["date"], career["player"]["matches"], dict(career["death"])
        advance_career(career)
        self.assertEqual(career["calendar"]["date"], previous_date)
        self.assertEqual(career["player"]["matches"], previous_matches)
        self.assertEqual(due_follow_up_events(career), [])
        self.assertFalse(event_is_eligible(career, NARRATIVE_EVENTS["hair_change"]))
        self.assertIsNone(maybe_create_narrative_event(career, type("Rng", (), {"random": lambda self: 0})(), chance=1))
        self.assertFalse(resolve_transfer_decision(career, {"transfer_candidates": []}, "stay"))
        self.assertFalse(die(career, "Outra causa."))
        self.assertEqual(career["death"], death)

    def test_death_terminal_is_applied_from_a_declarative_event_choice(self):
        career = self.career()
        career["player"]["age"] = 18
        event = build_narrative_event(career, "fatal_off_field_accident")
        career["pending_event"] = event
        self.assertTrue(resolve_decision(career, "fatal_outcome"))
        self.assertEqual(career["status"], "deceased")
        self.assertEqual(career["death"]["event_id"], "fatal_off_field_accident")

    def test_outcome_is_applied_once_and_keeps_a_result_card(self):
        career = self.career()
        event = {
            "id": "outcome-test", "event_key": "outcome-test", "narrative_event": True,
            "type": "media", "title": "Teste", "text": "...",
            "choices": [{"id": "choose", "label": "Escolher", "outcomes": [
                {"weight": 1, "text": "Resultado único", "summary": ["Moral +4"],
                 "effects": {"player": {"morale": 4}, "development_points": 3, "status_momentum": 2,
                             "set_flags": ["outcome_flag"], "behavior": {"media_conflicts": 1}}}
            ]}],
        }
        career["pending_event"] = event
        before = career["player"]["morale"]
        self.assertTrue(resolve_decision(career, "choose"))
        result = career["pending_event"]
        self.assertTrue(result["outcome_result"])
        self.assertEqual(career["player"]["morale"], before + 4)
        self.assertEqual(career["development_points"], 3)
        self.assertEqual(career["status_momentum"], 2)
        self.assertTrue(career["flags"]["outcome_flag"])
        self.assertFalse(resolve_decision(career, "choose", event["id"]))
        self.assertTrue(resolve_decision(career, "continue", result["id"]))
        self.assertEqual(career["player"]["morale"], before + 4)

    def test_hair_outcomes_include_safe_choice_and_three_weighted_results(self):
        career = self.career()
        hair = NARRATIVE_EVENTS["hair_change"]
        change = next(choice for choice in hair["choices"] if choice["id"] == "change_style")
        keep = next(choice for choice in hair["choices"] if choice["id"] == "keep_style")
        self.assertEqual([outcome["weight"] for outcome in change["outcomes"]], [70, 20, 10])
        self.assertEqual(keep["outcomes"][0]["effects"], {})
        before = (dict(career["player"]), dict(career["reputation"]))
        event = build_narrative_event(career, "hair_change")
        career["pending_event"] = event
        self.assertTrue(resolve_decision(career, "keep_style"))
        self.assertEqual(career["player"], before[0])
        self.assertEqual(career["reputation"], before[1])
