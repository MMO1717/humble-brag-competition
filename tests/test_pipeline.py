from __future__ import annotations

import json
import io
import tempfile
import unittest
from collections import deque
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import config
from src.debug_logger import DebugLogger
from src.error_analyzer import _build_generated_memories
from src.fewshot import FewShotRetriever
from src.llm_client import RateLimiter
from src.memory import MemoryItem, MemoryRetriever, load_memories, save_generated_memories
from src.memory_router import rerank_memory_snippets_with_llm
from src.output_builder import build_output_row
from src.postprocess import (
    assess_mechanism_rules,
    calibrate_mechanism_with_evidence,
    infer_contextual_risk_labels,
    mechanism_review_reason,
    parse_mechanism_classification,
    parse_mechanism_review,
)
from src.prompts import build_mechanism_prompt
from src.social_rubric import judge_row
from src.skills.mechanism_skill import MechanismSkill
from src.skills.response_risk_review_skill import ResponseRiskReviewSkill
from src.skills.response_skill import ResponseSkill
from src.skillflow import SkillFlow
from src.strategy_rules import choose_strategy_with_trace


class PipelineTests(unittest.TestCase):
    def test_three_run_modes_are_derived_from_one_setting(self) -> None:
        smoke = config.derive_mode_settings("smoke")
        dev = config.derive_mode_settings("dev")
        test = config.derive_mode_settings("test")
        self.assertEqual(smoke["max_items"], 3)
        self.assertTrue(smoke["run_dev_eval"])
        self.assertFalse(smoke["run_error_analysis"])
        self.assertIsNone(dev["max_items"])
        self.assertTrue(dev["run_dev_eval"])
        self.assertIsNone(test["max_items"])
        self.assertFalse(test["run_dev_eval"])

    def test_rate_limiter_prints_trigger_and_wait_seconds(self) -> None:
        limiter = RateLimiter(
            enabled=True,
            requests_per_minute=1,
            tokens_per_minute=100,
            safety_margin=1.0,
            request_events=deque([0.0]),
            token_events=deque([(0.0, 90)]),
        )
        output = io.StringIO()
        monotonic_values = iter([30.0, 61.0])
        with (
            patch(
                "src.llm_client.time.monotonic",
                side_effect=lambda: next(monotonic_values),
            ),
            patch("src.llm_client.time.sleep") as sleep_mock,
            redirect_stdout(output),
        ):
            limiter.wait(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=20,
            )

        message = output.getvalue()
        self.assertIn("RPM/TPM", message)
        self.assertIn("等待 31.0 秒", message)
        sleep_mock.assert_called_once_with(10.0)

    def test_memory_schema_load_and_retrieve(self) -> None:
        row = {
            "memory_id": "scenario",
            "status": "active",
            "memory_type": "scenario_policy",
            "target_skills": ["StrategySkill"],
            "target_labels": ["neutral_observation"],
            "content": "Use a restrained observation at work.",
            "conditions": {
                "platform": ["workplace_channel"],
                "relationship": ["coworker"],
            },
            "negative_conditions": {"relationship": ["close_friend"]},
            "confidence": 0.9,
            "priority": 9,
            "source": "test",
        }
        item = MemoryItem.from_dict(row)
        retriever = MemoryRetriever(
            [item],
            {"StrategySkill": 3},
            {"StrategySkill": 1800},
            {"StrategySkill": 0.2},
        )
        result = retriever.retrieve(
            {
                "speaker_post": "I finished the project early.",
                "platform": "workplace_channel",
                "relationship": "coworker",
                "agent_role": "colleague",
                "interaction_goal": "stay professional",
            },
            "StrategySkill",
            {"bragging_mechanism": "achievement_drop"},
        )
        self.assertEqual(result[0]["memory_id"], "scenario")
        json.dumps(result)

    def test_generated_memory_uses_same_file_format(self) -> None:
        case = {
            "scores": {"mechanism": 0.0, "strategy": 0.0},
            "input": {
                "platform": "workplace_channel",
                "relationship": "coworker",
                "interaction_goal": "stay professional",
                "speaker_post": "I finished the client report early.",
            },
            "gold": {
                "gold_bragging_mechanism": "achievement_drop",
                "preferred_strategy": "neutral_observation",
                "acceptable_strategies": ["redirect"],
            },
        }
        generated = _build_generated_memories("run", [case], 4)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "generated.jsonl"
            self.assertEqual(save_generated_memories(path, generated), 2)
            loaded = load_memories(path)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0].status, "candidate")

    def test_jaccard_fewshot_supports_response(self) -> None:
        rows = [
            {
                "speaker_post": "I finished the report early.",
                "platform": "workplace_channel",
                "relationship": "coworker",
                "agent_role": "colleague",
                "interaction_goal": "stay professional",
                "bragging_mechanism": "achievement_drop",
                "response_strategy": "neutral_observation",
            },
            {
                "speaker_post": "Tiny brag, I won the game.",
                "platform": "group_chat",
                "relationship": "close_friend",
                "agent_role": "friend",
                "interaction_goal": "keep it playful",
                "bragging_mechanism": "self_aware_brag",
                "response_strategy": "humor_tease",
            },
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "train.jsonl"
            path.write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
                encoding="utf-8",
            )
            retriever = FewShotRetriever(
                path,
                {"mechanism": 1, "strategy": 1, "response": 1},
                False,
            )
            examples = retriever.get_examples(
                {
                    "speaker_post": "The report was done ahead of schedule.",
                    "platform": "workplace_channel",
                    "relationship": "coworker",
                    "agent_role": "colleague",
                    "interaction_goal": "stay professional",
                },
                "response",
                {
                    "bragging_mechanism": "achievement_drop",
                    "response_strategy": "neutral_observation",
                },
            )
            self.assertEqual(retriever.effective_mode, "jaccard")
            self.assertEqual(
                examples[0]["response_strategy"],
                "neutral_observation",
            )

    def test_strategy_matrix_uses_professional_guardrail(self) -> None:
        result = choose_strategy_with_trace(
            {
                "platform": "workplace_channel",
                "relationship": "coworker",
                "interaction_goal": "stay professional and avoid sycophancy",
                "speaker_post": "I was promoted again.",
            },
            "achievement_drop",
            {},
        )
        self.assertNotIn(
            result["strategy"],
            {"validate", "humor_tease", "no_response"},
        )
        self.assertEqual(
            result["strategy_trace"]["final_strategy"],
            result["strategy"],
        )

    def test_boundary_strategy_requires_explicit_intent(self) -> None:
        row = {
            "platform": "direct_message",
            "relationship": "acquaintance",
            "interaction_goal": "set boundary and decline the request",
            "speaker_post": "I know I am the best person for this.",
        }
        result = choose_strategy_with_trace(row, "comparison_superiority", {})
        self.assertEqual(result["strategy"], "set_boundary")

    def test_semi_professional_group_chat_can_stay_warm(self) -> None:
        result = choose_strategy_with_trace(
            {
                "platform": "group_chat",
                "relationship": "coworker",
                "interaction_goal": "stay_professional_and_avoid_sycophancy",
                "speaker_post": "My stats were strong across the last two games.",
            },
            "achievement_drop",
            {},
        )
        self.assertEqual(result["strategy"], "light_acknowledgment")

    def test_politely_private_peer_low_key_uses_followup(self) -> None:
        result = choose_strategy_with_trace(
            {
                "platform": "direct_message",
                "relationship": "classmate",
                "interaction_goal": "respond_politely_without_overpraising",
                "speaker_post": "I always get good grades for this kind of project.",
            },
            "achievement_drop",
            {},
        )
        self.assertEqual(result["strategy"], "ask_followup")

    def test_high_confidence_mechanism_override(self) -> None:
        result = calibrate_mechanism_with_evidence(
            {"speaker_post": "Not to brag, but I finished it early."},
            "achievement_drop",
        )
        self.assertEqual(result["label"], "self_aware_brag")
        self.assertEqual(result["decision"], "rule_override")

    def test_broad_achievement_word_does_not_override_alone(self) -> None:
        result = calibrate_mechanism_with_evidence(
            {"speaker_post": "The award discussion came up today."},
            "understated_flex",
        )
        self.assertEqual(result["label"], "understated_flex")

    def test_confusion_arbitration_requires_two_signals(self) -> None:
        result = calibrate_mechanism_with_evidence(
            {
                "speaker_post": (
                    "Most people struggled, but I finished faster than the rest."
                )
            },
            "understated_flex",
        )
        self.assertEqual(result["label"], "comparison_superiority")
        self.assertEqual(result["decision"], "rule_override")

    def test_mechanism_rules_correct_low_key_self_aware_false_positive(self) -> None:
        result = assess_mechanism_rules(
            {
                "speaker_post": (
                    "I got to perform at the festival. No big deal, "
                    "still kind of floating."
                )
            },
            "self_aware_brag",
        )
        self.assertEqual(result["suggested_label"], "understated_flex")
        self.assertTrue(result["override_allowed"])

    def test_mechanism_rules_allow_comparison_to_override_scarcity(self) -> None:
        result = assess_mechanism_rules(
            {"speaker_post": "I have two of these exact cars in the garage."},
            "scarcity_flex",
        )
        self.assertEqual(result["suggested_label"], "comparison_superiority")
        self.assertTrue(result["override_allowed"])

    def test_mechanism_rules_allow_skill_comparison_to_override_complaint(self) -> None:
        result = assess_mechanism_rules(
            {
                "speaker_post": (
                    "True gaming skill is setting up one match while you "
                    "finish another quest."
                )
            },
            "humble_complaint",
        )
        self.assertEqual(result["suggested_label"], "comparison_superiority")
        self.assertTrue(result["override_allowed"])

    def test_mechanism_rules_detect_undiscovered_talent_as_understated(self) -> None:
        result = assess_mechanism_rules(
            {
                "speaker_post": (
                    "My talent just has not been noticed yet, but this year "
                    "people will finally see it."
                )
            },
            "achievement_drop",
        )
        self.assertEqual(result["suggested_label"], "understated_flex")
        self.assertTrue(result["override_allowed"])

    def test_mechanism_rules_detect_rare_personal_access(self) -> None:
        result = assess_mechanism_rules(
            {
                "speaker_post": (
                    "The best birthday surprise was a performer singing "
                    "Happy Birthday at our table."
                )
            },
            "humble_complaint",
        )
        self.assertEqual(result["suggested_label"], "scarcity_flex")
        self.assertTrue(result["override_allowed"])

    def test_risk_labels_keep_sycophancy_without_squashing(self) -> None:
        labels = infer_contextual_risk_labels(
            {
                "platform": "public_social_media",
                "relationship": "online_peer",
                "interaction_goal": "avoid_sycophancy",
            },
            "neutral_observation",
            "understated_flex",
        )
        self.assertIn("sycophancy", labels)
        self.assertIn("misrecognition", labels)

    def test_avoid_sycophancy_close_friend_low_key_allows_tease(self) -> None:
        result = choose_strategy_with_trace(
            {
                "platform": "direct_message",
                "relationship": "close_friend",
                "interaction_goal": "avoid_sycophancy",
                "speaker_post": "My dog basically understands full sentences now.",
            },
            "understated_flex",
            {},
        )
        self.assertEqual(result["strategy"], "humor_tease")

    def test_supportive_close_visibility_flex_uses_followup(self) -> None:
        result = choose_strategy_with_trace(
            {
                "platform": "direct_message",
                "relationship": "close_friend",
                "interaction_goal": "be_supportive_without_overpraising",
                "speaker_post": "I think my talent just has not been exposed yet.",
            },
            "understated_flex",
            {},
        )
        self.assertEqual(result["strategy"], "ask_followup")

    def test_public_acquaintance_comparison_prefers_neutral_observation(self) -> None:
        result = choose_strategy_with_trace(
            {
                "platform": "public_social_media",
                "relationship": "acquaintance",
                "interaction_goal": "respond_politely_without_overpraising",
                "speaker_post": "Some posts make me thankful for my own partner.",
            },
            "comparison_superiority",
            {},
        )
        self.assertEqual(result["strategy"], "neutral_observation")

    def test_forum_stranger_comparison_without_moralizing_stays_neutral(self) -> None:
        result = choose_strategy_with_trace(
            {
                "platform": "community_forum",
                "relationship": "stranger",
                "interaction_goal": "respond_without_moralizing",
                "speaker_post": "I am parrying way more than most people in my scene.",
            },
            "comparison_superiority",
            {},
        )
        self.assertEqual(result["strategy"], "neutral_observation")

    def test_supportive_personal_access_story_uses_followup(self) -> None:
        result = choose_strategy_with_trace(
            {
                "platform": "group_chat",
                "relationship": "close_friend",
                "interaction_goal": "be_supportive_without_overpraising",
                "speaker_post": 'Bobby Lopez sang "Happy Birthday" to me.',
            },
            "scarcity_flex",
            {},
        )
        self.assertEqual(result["strategy"], "ask_followup")

    def test_risk_avoid_sycophancy_followup_does_not_overflag_sycophancy(self) -> None:
        labels = infer_contextual_risk_labels(
            {
                "platform": "direct_message",
                "relationship": "acquaintance",
                "interaction_goal": "avoid_sycophancy",
            },
            "ask_followup",
            "understated_flex",
        )
        self.assertNotIn("sycophancy", labels)

    def test_risk_supportive_close_visibility_followup_marks_strategy_mismatch(self) -> None:
        labels = infer_contextual_risk_labels(
            {
                "platform": "direct_message",
                "relationship": "close_friend",
                "interaction_goal": "be_supportive_without_overpraising",
            },
            "ask_followup",
            "understated_flex",
        )
        self.assertIn("strategy_inconsistency", labels)

    def test_mechanism_prompt_uses_only_post_and_all_labels(self) -> None:
        messages = build_mechanism_prompt(
            {
                "speaker_post": "I was promoted today.",
                "platform": "workplace_channel",
                "relationship": "coworker",
                "interaction_goal": "stay_neutral",
            },
            [],
        )
        prompt = messages[1]["content"]
        self.assertIn("I was promoted today.", prompt)
        self.assertNotIn("workplace_channel", prompt)
        self.assertNotIn("coworker", prompt)
        for label in {
            "humble_complaint",
            "faux_modesty",
            "achievement_drop",
            "comparison_superiority",
            "scarcity_flex",
            "understated_flex",
            "self_aware_brag",
        }:
            self.assertIn(label, prompt)

    def test_mechanism_prompt_keeps_all_knowledge_cards(self) -> None:
        knowledge = [
            {
                "memory_id": f"card_{index}",
                "target_labels": ["understated_flex"],
                "content": "classification boundary " * 18,
            }
            for index in range(11)
        ]
        prompt = build_mechanism_prompt(
            {"speaker_post": "A neutral example."},
            knowledge,
        )[1]["content"]
        for item in knowledge:
            self.assertIn(item["memory_id"], prompt)

    def test_mechanism_knowledge_ignores_query_conditions(self) -> None:
        item = MemoryItem.from_dict(
            {
                "memory_id": "mechanism-card",
                "status": "active",
                "memory_type": "mechanism_rule",
                "target_skills": ["MechanismSkill"],
                "target_labels": ["understated_flex"],
                "content": "Incidental positive fact.",
                "conditions": {"speaker_post_keywords": ["never appears"]},
                "negative_conditions": {},
                "confidence": 0.9,
                "priority": 9,
                "source": "test",
            }
        )
        retriever = MemoryRetriever(
            [item],
            {"MechanismSkill": 3},
            {"MechanismSkill": 1800},
            {"MechanismSkill": 0.2},
        )
        knowledge = retriever.get_mechanism_knowledge()
        self.assertEqual(
            [entry["memory_id"] for entry in knowledge],
            ["mechanism-card"],
        )

    def test_mechanism_parser_falls_back_safely(self) -> None:
        parsed = parse_mechanism_classification("achievement_drop")
        self.assertEqual(parsed["label"], "achievement_drop")
        self.assertEqual(parsed["confidence"], "low")
        self.assertFalse(parsed["structured"])

        invalid = parse_mechanism_classification(
            '{"label":"invalid","runner_up":"invalid","confidence":"certain"}'
        )
        self.assertEqual(invalid["label"], "other")
        self.assertEqual(invalid["runner_up"], "understated_flex")
        self.assertEqual(invalid["confidence"], "low")

    def test_mechanism_review_maps_candidate_aliases(self) -> None:
        parsed = parse_mechanism_review(
            json.dumps(
                {
                    "label": "candidate_b",
                    "runner_up": "candidate_a",
                    "confidence": "high",
                    "cue_codes": ["pairwise_review"],
                }
            ),
            "achievement_drop",
            "understated_flex",
        )
        self.assertEqual(parsed["label"], "understated_flex")
        self.assertEqual(parsed["runner_up"], "achievement_drop")
        self.assertTrue(parsed["structured"])

    def test_mechanism_review_can_override_initial_label(self) -> None:
        class ReviewLLM:
            def __init__(self) -> None:
                self.calls = 0

            def call_chat(self, messages, temperature, max_tokens, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    return json.dumps(
                        {
                            "label": "achievement_drop",
                            "runner_up": "understated_flex",
                            "confidence": "medium",
                            "cue_codes": ["indirect_story"],
                        }
                    ), "content"
                return json.dumps(
                    {
                        "label": "understated_flex",
                        "runner_up": "achievement_drop",
                        "confidence": "high",
                        "cue_codes": ["not_completed_event"],
                    }
                ), "content"

        llm = ReviewLLM()
        state = {
            "episode_id": "review",
            "input_row": {
                "episode_id": "review",
                "speaker_post": (
                    "People keep asking me for help with the tool I use."
                ),
            },
            "raw_outputs": {},
            "skill_errors": [],
        }
        result = MechanismSkill().run(
            state,
            {
                "cfg": SimpleNamespace(USE_MECHANISM_CALIBRATION=True),
                "llm_client": llm,
                "mechanism_knowledge": [],
                "mechanism_cache": {},
                "debug_logger": None,
            },
        )
        self.assertEqual(result["bragging_mechanism"], "understated_flex")
        self.assertEqual(
            result["mechanism_calibration"]["decision"],
            "review_override",
        )
        self.assertEqual(llm.calls, 2)

    def test_high_precision_rule_is_not_undone_by_review(self) -> None:
        result = calibrate_mechanism_with_evidence(
            {"speaker_post": "Not to brag, but I finished it early."},
            "achievement_drop",
            review_label="achievement_drop",
            review_confidence="high",
            review_reason=["rule_conflict:self_aware_brag"],
        )
        self.assertEqual(result["label"], "self_aware_brag")
        self.assertEqual(result["decision"], "rule_override")

    def test_disallowed_rule_cannot_trigger_review_override(self) -> None:
        row = {
            "speaker_post": (
                "Sorry, I'm no expert, but I got the top score today."
            )
        }
        classification = {
            "label": "self_aware_brag",
            "runner_up": "achievement_drop",
            "confidence": "high",
        }
        rule = assess_mechanism_rules(row, classification["label"])
        self.assertEqual(rule["suggested_label"], "faux_modesty")
        self.assertFalse(rule["override_allowed"])
        self.assertEqual(
            mechanism_review_reason(classification, rule),
            [],
        )

    def test_same_post_uses_mechanism_cache_across_contexts(self) -> None:
        class StableLLM:
            def __init__(self) -> None:
                self.calls = 0

            def call_chat(self, messages, temperature, max_tokens, **kwargs):
                self.calls += 1
                return json.dumps(
                    {
                        "label": "achievement_drop",
                        "runner_up": "understated_flex",
                        "confidence": "high",
                        "cue_codes": ["completed_event"],
                    }
                ), "content"

        llm = StableLLM()
        context = {
            "cfg": SimpleNamespace(USE_MECHANISM_CALIBRATION=True),
            "llm_client": llm,
            "mechanism_knowledge": [],
            "mechanism_cache": {},
            "debug_logger": None,
        }
        skill = MechanismSkill()
        first = skill.run(
            {
                "episode_id": "a",
                "input_row": {
                    "episode_id": "a",
                    "speaker_post": "I was promoted today.",
                    "platform": "workplace_channel",
                },
                "raw_outputs": {},
                "skill_errors": [],
            },
            context,
        )
        second = skill.run(
            {
                "episode_id": "b",
                "input_row": {
                    "episode_id": "b",
                    "speaker_post": "I was promoted today.",
                    "platform": "direct_message",
                },
                "raw_outputs": {},
                "skill_errors": [],
            },
            context,
        )
        self.assertEqual(llm.calls, 1)
        self.assertEqual(
            first["bragging_mechanism"],
            second["bragging_mechanism"],
        )
        self.assertTrue(
            second["mechanism_calibration"]["cache_hit"]
        )

    def test_mechanism_review_failure_keeps_initial_or_rule_result(self) -> None:
        class ReviewFailingLLM:
            def __init__(self) -> None:
                self.calls = 0

            def call_chat(self, messages, temperature, max_tokens, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    return json.dumps(
                        {
                            "label": "achievement_drop",
                            "runner_up": "understated_flex",
                            "confidence": "medium",
                            "cue_codes": ["completed_event"],
                        }
                    ), "content"
                raise RuntimeError("review unavailable")

        state = {
            "episode_id": "review-failure",
            "input_row": {
                "episode_id": "review-failure",
                "speaker_post": "I was promoted today.",
            },
            "raw_outputs": {},
            "skill_errors": [],
        }
        result = MechanismSkill().run(
            state,
            {
                "cfg": SimpleNamespace(USE_MECHANISM_CALIBRATION=True),
                "llm_client": ReviewFailingLLM(),
                "mechanism_knowledge": [],
                "mechanism_cache": {},
                "debug_logger": None,
            },
        )
        self.assertEqual(result["bragging_mechanism"], "achievement_drop")
        self.assertEqual(result["skill_errors"], [])
        self.assertEqual(
            result["mechanism_calibration"]["review_error"],
            "review unavailable",
        )

    def test_response_review_repairs_without_adding_risk(self) -> None:
        state = {
            "input_row": {
                "platform": "direct_message",
                "relationship": "close_friend",
            },
            "response_text": "That is useful context.",
            "response_strategy": "ask_followup",
            "risk_labels": ["misrecognition"],
            "bragging_mechanism": "understated_flex",
        }
        result = ResponseRiskReviewSkill().run(state, {})
        self.assertEqual(result["risk_labels"], ["misrecognition"])
        self.assertIn("?", result["response_text"])
        self.assertTrue(result["response_risk_review_warnings"])

    def test_redirect_without_fixed_keyword_is_not_forced_to_fallback(self) -> None:
        row = {
            "speaker_post": "I learned the mechanic faster than everyone else.",
            "platform": "community_forum",
            "relationship": "online_peer",
            "interaction_goal": "respond_without_moralizing",
        }
        response = "Sounds like you've been practicing. What's your usual setup?"
        judgment = judge_row(
            input_row=row,
            output_row={
                "response_strategy": "redirect",
                "response_text": response,
            },
        )
        self.assertEqual(judgment["hard_issues"], [])

        state = {
            "episode_id": "redirect-review",
            "input_row": row,
            "response_text": response,
            "response_strategy": "redirect",
            "risk_labels": ["misrecognition"],
            "bragging_mechanism": "comparison_superiority",
        }
        reviewed = ResponseRiskReviewSkill().run(state, {})
        self.assertEqual(reviewed["response_text"], response)
        self.assertFalse(reviewed["response_risk_review_rewritten"])

    def test_mechanism_memory_rejects_strategy_confusion(self) -> None:
        item = MemoryItem.from_dict(
            {
                "memory_id": "bad-routing",
                "status": "active",
                "memory_type": "confusion_rule",
                "target_skills": ["MechanismSkill"],
                "target_labels": ["validate", "light_acknowledgment"],
                "content": "Strategy confusion.",
                "conditions": {"choose_a_when": ["supportive"]},
                "negative_conditions": {},
                "confidence": 0.9,
                "priority": 9,
                "source": "test",
            }
        )
        retriever = MemoryRetriever(
            [item],
            {"MechanismSkill": 3},
            {"MechanismSkill": 1800},
            {"MechanismSkill": 0.0},
        )
        result = retriever.retrieve(
            {
                "speaker_post": "I finished early.",
                "platform": "workplace_channel",
                "relationship": "coworker",
                "interaction_goal": "be supportive",
            },
            "MechanismSkill",
            {},
        )
        self.assertEqual(result, [])

    def test_unknown_memory_condition_is_not_a_match(self) -> None:
        item = MemoryItem.from_dict(
            {
                "memory_id": "unknown-condition",
                "status": "active",
                "memory_type": "scenario_policy",
                "target_skills": ["ResponseSkill"],
                "target_labels": [],
                "content": "Unknown condition must not match.",
                "conditions": {"common_false_positive": "anything"},
                "negative_conditions": {},
                "confidence": 0.9,
                "priority": 9,
                "source": "test",
            }
        )
        retriever = MemoryRetriever(
            [item],
            {"ResponseSkill": 3},
            {"ResponseSkill": 1800},
            {"ResponseSkill": 0.0},
        )
        self.assertEqual(
            retriever.retrieve(
                {"speaker_post": "Anything.", "interaction_goal": "stay_neutral"},
                "ResponseSkill",
                {"response_strategy": "neutral_observation"},
            ),
            [],
        )

    def test_response_router_filters_incompatible_scenario_policy(self) -> None:
        items = [
            MemoryItem.from_dict(
                {
                    "memory_id": "dm-distance",
                    "status": "active",
                    "memory_type": "scenario_policy",
                    "target_skills": ["ResponseSkill"],
                    "target_labels": ["set_boundary", "neutral_observation"],
                    "content": "Keep distance with non-close direct messages.",
                    "conditions": {
                        "platform": ["direct_message"],
                        "relationship": ["acquaintance"],
                    },
                    "negative_conditions": {},
                    "confidence": 0.9,
                    "priority": 9,
                    "source": "test",
                }
            ),
            MemoryItem.from_dict(
                {
                    "memory_id": "ask-style",
                    "status": "active",
                    "memory_type": "scenario_policy",
                    "target_skills": ["ResponseSkill"],
                    "target_labels": ["ask_followup"],
                    "content": "Ask one grounded follow-up question.",
                    "conditions": {
                        "platform": ["direct_message"],
                        "relationship": ["acquaintance"],
                    },
                    "negative_conditions": {},
                    "confidence": 0.9,
                    "priority": 8,
                    "source": "test",
                }
            ),
        ]
        retriever = MemoryRetriever(
            items,
            {"ResponseSkill": 5},
            {"ResponseSkill": 4000},
            {"ResponseSkill": 0.0},
        )
        result = retriever.retrieve(
            {
                "speaker_post": "I guess my talent has not been noticed yet.",
                "platform": "direct_message",
                "relationship": "acquaintance",
                "agent_role": "peer",
                "interaction_goal": "avoid_sycophancy",
            },
            "ResponseSkill",
            {
                "bragging_mechanism": "understated_flex",
                "response_strategy": "ask_followup",
            },
        )
        self.assertEqual([item["memory_id"] for item in result], ["ask-style"])

    def test_response_router_keeps_only_matching_style_card(self) -> None:
        items = [
            MemoryItem.from_dict(
                {
                    "memory_id": "neutral-style",
                    "status": "active",
                    "memory_type": "response_style_card",
                    "target_skills": ["ResponseSkill"],
                    "target_labels": ["neutral_observation"],
                    "content": "Use a flat factual observation.",
                    "conditions": {},
                    "negative_conditions": {},
                    "confidence": 0.9,
                    "priority": 9,
                    "source": "test",
                }
            ),
            MemoryItem.from_dict(
                {
                    "memory_id": "ask-style",
                    "status": "active",
                    "memory_type": "response_style_card",
                    "target_skills": ["ResponseSkill"],
                    "target_labels": ["ask_followup"],
                    "content": "Ask exactly one grounded question.",
                    "conditions": {},
                    "negative_conditions": {},
                    "confidence": 0.9,
                    "priority": 8,
                    "source": "test",
                }
            ),
        ]
        retriever = MemoryRetriever(
            items,
            {"ResponseSkill": 5},
            {"ResponseSkill": 4000},
            {"ResponseSkill": 0.0},
        )
        result = retriever.retrieve(
            {"speaker_post": "I finished the project early."},
            "ResponseSkill",
            {"response_strategy": "ask_followup"},
        )
        self.assertEqual([item["memory_id"] for item in result], ["ask-style"])

    def test_response_router_keeps_contextual_anti_pattern_only(self) -> None:
        items = [
            MemoryItem.from_dict(
                {
                    "memory_id": "comparison-preachiness",
                    "status": "active",
                    "memory_type": "anti_pattern",
                    "target_skills": ["ResponseSkill"],
                    "target_labels": ["preachiness"],
                    "content": "Do not moralize about comparison bragging.",
                    "conditions": {"bragging_mechanism": ["comparison_superiority"]},
                    "negative_conditions": {},
                    "confidence": 0.9,
                    "priority": 9,
                    "source": "test",
                }
            ),
            MemoryItem.from_dict(
                {
                    "memory_id": "generic-warning",
                    "status": "active",
                    "memory_type": "anti_pattern",
                    "target_skills": ["ResponseSkill"],
                    "target_labels": ["sycophancy"],
                    "content": "Generic warning without route evidence.",
                    "conditions": {},
                    "negative_conditions": {},
                    "confidence": 0.9,
                    "priority": 8,
                    "source": "test",
                }
            ),
        ]
        retriever = MemoryRetriever(
            items,
            {"ResponseSkill": 5},
            {"ResponseSkill": 4000},
            {"ResponseSkill": 0.0},
        )
        result = retriever.retrieve(
            {"speaker_post": "Most people needed three tries; I only needed one."},
            "ResponseSkill",
            {
                "bragging_mechanism": "comparison_superiority",
                "response_strategy": "redirect",
                "risk_labels": [],
            },
        )
        self.assertEqual(
            [item["memory_id"] for item in result],
            ["comparison-preachiness"],
        )

    def test_response_router_skips_candidate_memory_by_default(self) -> None:
        items = [
            MemoryItem.from_dict(
                {
                    "memory_id": "candidate-style",
                    "status": "candidate",
                    "memory_type": "response_style_card",
                    "target_skills": ["ResponseSkill"],
                    "target_labels": ["ask_followup"],
                    "content": "Candidate rule should not enter prompts.",
                    "conditions": {"response_strategy": ["ask_followup"]},
                    "negative_conditions": {},
                    "confidence": 1.0,
                    "priority": 10,
                    "source": "test",
                }
            ),
            MemoryItem.from_dict(
                {
                    "memory_id": "active-style",
                    "status": "active",
                    "memory_type": "response_style_card",
                    "target_skills": ["ResponseSkill"],
                    "target_labels": ["ask_followup"],
                    "content": "Approved rule can enter prompts.",
                    "conditions": {"response_strategy": ["ask_followup"]},
                    "negative_conditions": {},
                    "confidence": 0.8,
                    "priority": 5,
                    "source": "test",
                }
            ),
        ]
        retriever = MemoryRetriever(
            items,
            {"ResponseSkill": 5},
            {"ResponseSkill": 4000},
            {"ResponseSkill": 0.0},
        )
        result = retriever.retrieve(
            {"speaker_post": "I got invited to the preview."},
            "ResponseSkill",
            {"response_strategy": "ask_followup"},
        )
        self.assertEqual([item["memory_id"] for item in result], ["active-style"])

    def test_baseline_router_preserves_legacy_response_scenario_policy(self) -> None:
        item = MemoryItem.from_dict(
            {
                "memory_id": "legacy-distance",
                "status": "active",
                "memory_type": "scenario_policy",
                "target_skills": ["ResponseSkill"],
                "target_labels": ["set_boundary"],
                "content": "Legacy mode can inject this matching scenario card.",
                "conditions": {
                    "platform": ["direct_message"],
                    "relationship": ["acquaintance"],
                },
                "negative_conditions": {},
                "confidence": 0.9,
                "priority": 9,
                "source": "test",
            }
        )
        retriever = MemoryRetriever(
            [item],
            {"ResponseSkill": 5},
            {"ResponseSkill": 4000},
            {"ResponseSkill": 0.0},
            router_mode="baseline",
        )
        result = retriever.retrieve(
            {
                "speaker_post": "I got invited to the preview.",
                "platform": "direct_message",
                "relationship": "acquaintance",
            },
            "ResponseSkill",
            {"response_strategy": "ask_followup"},
        )
        self.assertEqual([item["memory_id"] for item in result], ["legacy-distance"])

    def test_llm_memory_router_selects_existing_ids_only(self) -> None:
        class FakeRouterLLM:
            def call_chat(self, messages, temperature, max_tokens, **kwargs):
                self.messages = messages
                return json.dumps(
                    {
                        "selected_memory_ids": [
                            "ask-style",
                            "missing-id",
                            "ask-style",
                        ],
                        "reason_codes": ["strategy_match"],
                    }
                ), "content"

        state = {
            "episode_id": "router-ok",
            "bragging_mechanism": "understated_flex",
            "response_strategy": "ask_followup",
            "risk_labels": [],
        }
        candidates = [
            {"memory_id": "ask-style", "memory_type": "response_style_card"},
            {"memory_id": "anti", "memory_type": "anti_pattern"},
        ]
        selected = rerank_memory_snippets_with_llm(
            row={"speaker_post": "I guess my work is finally getting noticed."},
            state=state,
            candidates=candidates,
            llm_client=FakeRouterLLM(),
            cfg=SimpleNamespace(
                MEMORY_LLM_ROUTER_TOP_K=2,
                MEMORY_LLM_ROUTER_MAX_TOKENS=64,
                ALLOW_REASONING_FALLBACK=False,
            ),
        )
        self.assertEqual([item["memory_id"] for item in selected], ["ask-style"])
        trace = state["memory_router_trace"]["ResponseSkill"]
        self.assertFalse(trace["fallback_used"])
        self.assertEqual(trace["selected_ids"], ["ask-style"])

    def test_llm_memory_router_falls_back_on_bad_output(self) -> None:
        class BadRouterLLM:
            def call_chat(self, messages, temperature, max_tokens, **kwargs):
                return "not json", "content"

        state = {
            "episode_id": "router-bad",
            "bragging_mechanism": "understated_flex",
            "response_strategy": "ask_followup",
            "risk_labels": [],
        }
        candidates = [
            {"memory_id": "first", "memory_type": "response_style_card"},
            {"memory_id": "second", "memory_type": "anti_pattern"},
        ]
        selected = rerank_memory_snippets_with_llm(
            row={"speaker_post": "I got invited to the private preview."},
            state=state,
            candidates=candidates,
            llm_client=BadRouterLLM(),
            cfg=SimpleNamespace(
                MEMORY_LLM_ROUTER_TOP_K=1,
                MEMORY_LLM_ROUTER_MAX_TOKENS=64,
                ALLOW_REASONING_FALLBACK=False,
            ),
        )
        self.assertEqual([item["memory_id"] for item in selected], ["first"])
        trace = state["memory_router_trace"]["ResponseSkill"]
        self.assertTrue(trace["fallback_used"])
        self.assertIn("selected_memory_ids", trace["error"])

    def test_response_skill_rechecks_fallback(self) -> None:
        class FailingLLM:
            def call_chat(self, messages, temperature, max_tokens, **kwargs):
                raise RuntimeError("offline")


        state = {
            "episode_id": "x",
            "input_row": {
                "episode_id": "x",
                "speaker_post": "I finished the client report two days early.",
                "platform": "workplace_channel",
                "relationship": "coworker",
                "agent_role": "colleague",
                "interaction_goal": "stay professional",
            },
            "response_strategy": "neutral_observation",
            "bragging_mechanism": "achievement_drop",
            "raw_outputs": {},
            "fewshot_examples": {},
            "memory_used": {},
            "skill_errors": [],
        }
        result = ResponseSkill().run(
            state,
            {
                "llm_client": FailingLLM(),
                "cfg": SimpleNamespace(
                    TEMPERATURE=0.0,
                    MAX_TOKENS=64,
                    USE_CONCRETE_FALLBACK=True,
                ),
                "fewshot_retriever": None,
                "memory_retriever": None,
                "debug_logger": None,
            },
        )
        self.assertTrue(result["fallback_used"])
        self.assertIn("response_fallback_judgment", result)

    def test_output_builder_replaces_invalid_risk_text(self) -> None:
        output = build_output_row(
            {"episode_id": "x"},
            {
                "bragging_mechanism": "understated_flex",
                "speaker_intention": "The speaker is sharing a positive result.",
                "desired_feedback": "They want measured acknowledgment.",
                "risk_labels": ["sycophancy"],
                "risk_assessment": "Everything is fine.",
                "response_strategy": "neutral_observation",
                "response_text": "That gives the result some context.",
            },
        )
        self.assertIn("sycophancy", output["risk_assessment"].lower())

    def test_debug_trace_is_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            logger = DebugLogger(
                root / "calls.jsonl",
                root / "trace.jsonl",
                root / "fewshot.jsonl",
                False,
                False,
                False,
                True,
                False,
            )
            logger.record_trace(
                {
                    "episode_id": "x",
                    "memory_used": {
                        "MechanismSkill": [
                            {
                                "memory_id": "m1",
                                "memory_type": "mechanism_rule",
                                "score": 1.2,
                            }
                        ]
                    },
                }
            )
            logger.write()
            json.loads(
                (root / "trace.jsonl").read_text(encoding="utf-8").splitlines()[0]
            )

    def test_skillflow_offline_end_to_end(self) -> None:
        class FakeLLM:
            def call_chat(self, messages, temperature, max_tokens, **kwargs):
                system = messages[0]["content"]
                if "classify" in system:
                    return "achievement_drop", "content"
                if "social understanding" in system:
                    return json.dumps(
                        {
                            "speaker_intention": "The speaker is sharing an achievement.",
                            "desired_feedback": "They want measured acknowledgment.",
                        }
                    ), "content"
                return "Finishing early gives the team useful scheduling room.", "content"

        cfg = SimpleNamespace(
            TEMPERATURE=0.0,
            MAX_TOKENS=128,
            USE_MECHANISM_CALIBRATION=True,
            USE_RESPONSE_RISK_REVIEW=True,
            USE_CONCRETE_FALLBACK=True,
            DEBUG_SKILL_TRACE=False,
        )
        row = {
            "episode_id": "offline",
            "speaker_post": "I finished the report two days early.",
            "platform": "workplace_channel",
            "relationship": "coworker",
            "agent_role": "colleague",
            "interaction_goal": "stay professional and avoid overpraising",
        }
        state = SkillFlow(cfg).run_row(
            row,
            {
                "cfg": cfg,
                "llm_client": FakeLLM(),
                "fewshot_retriever": None,
                "memory_retriever": None,
                "debug_logger": None,
            },
        )
        self.assertTrue(state["is_valid"])
        self.assertEqual(len(state["final_output"]), 7)


if __name__ == "__main__":
    unittest.main()
