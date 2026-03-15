"""
Tests for src/chanakya/prompts/prompts.py and src/chanakya/prompts/__init__.py

Focus: Verify prompt template string constants contain required placeholders
and that the module exports them correctly.
"""

import sys
import unittest

sys.path.insert(0, "/home/jailuser/git")

from src.chanakya.prompts.prompts import (
    REACT_AGENT_PROMPT_TEMPLATE_STR,
    QUERY_REFINEMENT_TEMPLATE_STR,
)
from src.chanakya.prompts import (
    REACT_AGENT_PROMPT_TEMPLATE_STR as REACT_FROM_INIT,
    QUERY_REFINEMENT_TEMPLATE_STR as QUERY_FROM_INIT,
)


class TestReactAgentPromptTemplate(unittest.TestCase):
    """Tests for REACT_AGENT_PROMPT_TEMPLATE_STR."""

    def test_is_string(self):
        self.assertIsInstance(REACT_AGENT_PROMPT_TEMPLATE_STR, str)

    def test_is_not_empty(self):
        self.assertTrue(len(REACT_AGENT_PROMPT_TEMPLATE_STR.strip()) > 0)

    # --- Required placeholders for LangChain template ---

    def test_contains_dynamic_intro_and_memories_placeholder(self):
        self.assertIn("{dynamic_intro_and_memories}", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_tools_placeholder(self):
        self.assertIn("{tools}", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_tool_names_placeholder(self):
        self.assertIn("{tool_names}", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_tool_instructions_placeholder(self):
        self.assertIn("{tool_instructions}", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_chat_history_placeholder(self):
        self.assertIn("{chat_history}", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_input_placeholder(self):
        self.assertIn("{input}", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_agent_scratchpad_placeholder(self):
        self.assertIn("{agent_scratchpad}", REACT_AGENT_PROMPT_TEMPLATE_STR)

    # --- Required instruction keywords ---

    def test_contains_thought_keyword(self):
        self.assertIn("Thought:", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_action_keyword(self):
        self.assertIn("Action:", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_action_input_keyword(self):
        self.assertIn("Action Input:", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_final_answer_keyword(self):
        self.assertIn("Final Answer:", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_observation_keyword(self):
        self.assertIn("Observation:", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_previous_conversation_section(self):
        self.assertIn("PREVIOUS CONVERSATION:", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_current_user_request(self):
        self.assertIn("Current User Request:", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_error_handling_guidance(self):
        self.assertIn("Error Handling Guidance:", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_contains_begin_marker(self):
        self.assertIn("Begin!", REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_double_brace_escaping_for_json_example(self):
        # The template uses {{ }} to escape literal braces in the format string
        self.assertIn("{{", REACT_AGENT_PROMPT_TEMPLATE_STR)
        self.assertIn("}}", REACT_AGENT_PROMPT_TEMPLATE_STR)


class TestQueryRefinementTemplate(unittest.TestCase):
    """Tests for QUERY_REFINEMENT_TEMPLATE_STR."""

    def test_is_string(self):
        self.assertIsInstance(QUERY_REFINEMENT_TEMPLATE_STR, str)

    def test_is_not_empty(self):
        self.assertTrue(len(QUERY_REFINEMENT_TEMPLATE_STR.strip()) > 0)

    # --- Required placeholders ---

    def test_contains_ai_response_placeholder(self):
        self.assertIn("{ai_response}", QUERY_REFINEMENT_TEMPLATE_STR)

    def test_contains_user_question_placeholder(self):
        self.assertIn("{user_question}", QUERY_REFINEMENT_TEMPLATE_STR)

    # --- Required instruction content ---

    def test_contains_keywords_instruction(self):
        self.assertIn("keywords", QUERY_REFINEMENT_TEMPLATE_STR.lower())

    def test_contains_keywords_output_marker(self):
        self.assertIn("Keywords:", QUERY_REFINEMENT_TEMPLATE_STR)

    def test_mentions_commas_separator(self):
        self.assertIn("commas", QUERY_REFINEMENT_TEMPLATE_STR.lower())

    def test_mentions_knowledge_base(self):
        self.assertIn("knowledge base", QUERY_REFINEMENT_TEMPLATE_STR.lower())


class TestPromptsModuleExports(unittest.TestCase):
    """Tests for the __init__.py exports."""

    def test_react_prompt_exported_from_init(self):
        """REACT_AGENT_PROMPT_TEMPLATE_STR should be importable from the package."""
        self.assertIsNotNone(REACT_FROM_INIT)
        self.assertIsInstance(REACT_FROM_INIT, str)

    def test_query_refinement_exported_from_init(self):
        """QUERY_REFINEMENT_TEMPLATE_STR should be importable from the package."""
        self.assertIsNotNone(QUERY_FROM_INIT)
        self.assertIsInstance(QUERY_FROM_INIT, str)

    def test_react_prompt_same_object_from_both_paths(self):
        """Importing from prompts or from prompts.prompts should yield the same string."""
        self.assertEqual(REACT_FROM_INIT, REACT_AGENT_PROMPT_TEMPLATE_STR)

    def test_query_refinement_same_object_from_both_paths(self):
        """Importing from prompts or from prompts.prompts should yield the same string."""
        self.assertEqual(QUERY_FROM_INIT, QUERY_REFINEMENT_TEMPLATE_STR)

    def test_all_list_contains_both_names(self):
        """__all__ in prompts/__init__.py should declare both exports."""
        import src.chanakya.prompts as prompts_pkg
        if hasattr(prompts_pkg, "__all__"):
            self.assertIn("REACT_AGENT_PROMPT_TEMPLATE_STR", prompts_pkg.__all__)
            self.assertIn("QUERY_REFINEMENT_TEMPLATE_STR", prompts_pkg.__all__)


class TestPromptTemplateUsability(unittest.TestCase):
    """Tests that prompts work correctly with LangChain's PromptTemplate."""

    def test_react_template_can_be_used_in_langchain_prompt(self):
        """REACT_AGENT_PROMPT_TEMPLATE_STR should be valid for PromptTemplate."""
        try:
            from langchain_core.prompts import PromptTemplate
            # This should not raise an error
            template = PromptTemplate.from_template(
                template=REACT_AGENT_PROMPT_TEMPLATE_STR,
                partial_variables={"tool_instructions": "test instructions"},
            )
            self.assertIsNotNone(template)
        except Exception as e:
            self.fail(f"PromptTemplate creation failed: {e}")

    def test_query_refinement_template_can_be_used_in_chat_prompt(self):
        """QUERY_REFINEMENT_TEMPLATE_STR should be valid for ChatPromptTemplate."""
        try:
            from langchain_core.prompts import ChatPromptTemplate
            template = ChatPromptTemplate.from_template(QUERY_REFINEMENT_TEMPLATE_STR)
            self.assertIsNotNone(template)
        except Exception as e:
            self.fail(f"ChatPromptTemplate creation failed: {e}")

    def test_react_template_input_variables_correct(self):
        """The template should have the expected input variables."""
        from langchain_core.prompts import PromptTemplate
        template = PromptTemplate.from_template(
            template=REACT_AGENT_PROMPT_TEMPLATE_STR,
            partial_variables={"tool_instructions": ""},
        )
        required_vars = {
            "dynamic_intro_and_memories",
            "tools",
            "tool_names",
            "chat_history",
            "input",
            "agent_scratchpad",
        }
        for var in required_vars:
            self.assertIn(var, template.input_variables, f"Missing input variable: {var}")

    def test_query_refinement_template_input_variables_correct(self):
        """Query refinement template should have ai_response and user_question."""
        from langchain_core.prompts import ChatPromptTemplate
        template = ChatPromptTemplate.from_template(QUERY_REFINEMENT_TEMPLATE_STR)
        # Check that it can be formatted with those variables
        try:
            formatted = template.format_messages(
                ai_response="previous response",
                user_question="what is python?",
            )
            self.assertIsNotNone(formatted)
        except Exception as e:
            self.fail(f"Template formatting failed: {e}")


if __name__ == "__main__":
    unittest.main()