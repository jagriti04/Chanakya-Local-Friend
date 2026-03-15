"""
Tests for src/chanakya/core/react_agent.py — CustomReActSingleInputOutputParser

Focus: the complex parse() method with <think> block handling,
Action / Action Input extraction, Final Answer parsing, edge cases.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock


def _clean_chanakya_modules():
    for key in list(sys.modules.keys()):
        if 'chanakya' in key:
            del sys.modules[key]


def _set_env():
    os.environ.setdefault('APP_SECRET_KEY', 'test-react')
    os.environ.setdefault('FLASK_DEBUG', 'True')
    os.environ.setdefault('DATABASE_PATH', ':memory:')
    os.environ.setdefault('LLM_PROVIDER', 'ollama')


class TestReActParserFinalAnswer(unittest.TestCase):
    """Tests for parsing Final Answer responses."""

    @classmethod
    def setUpClass(cls):
        _set_env()
        _clean_chanakya_modules()
        from src.chanakya.core.react_agent import CustomReActSingleInputOutputParser
        cls.parser = CustomReActSingleInputOutputParser()

    def test_plain_final_answer(self):
        """Simple 'Final Answer: ...' should be parsed as AgentFinish."""
        from langchain_core.agents import AgentFinish
        result = self.parser.parse("Final Answer: Hello, I am your assistant.")
        self.assertIsInstance(result, AgentFinish)
        self.assertEqual(result.return_values['output'], 'Hello, I am your assistant.')

    def test_final_answer_with_think_wrapper(self):
        """Final Answer inside <think>...</think> should be parsed correctly."""
        from langchain_core.agents import AgentFinish
        text = "<think>\nThought: I know the answer.\nFinal Answer: The capital is Delhi.\n</think>"
        result = self.parser.parse(text)
        self.assertIsInstance(result, AgentFinish)
        self.assertIn('Delhi', result.return_values['output'])

    def test_final_answer_multiline(self):
        """Final Answer spanning the rest of text should be captured."""
        from langchain_core.agents import AgentFinish
        text = "Thought: I should respond.\nFinal Answer: Line one.\nLine two.\nLine three."
        result = self.parser.parse(text)
        self.assertIsInstance(result, AgentFinish)
        self.assertIn('Line one', result.return_values['output'])

    def test_final_answer_with_nested_think(self):
        """Final Answer with nested <think> blocks should still be found."""
        from langchain_core.agents import AgentFinish
        text = "<think>\n<think>inner reasoning</think>\nFinal Answer: Got it!\n</think>"
        result = self.parser.parse(text)
        self.assertIsInstance(result, AgentFinish)
        self.assertIn('Got it!', result.return_values['output'])


class TestReActParserAction(unittest.TestCase):
    """Tests for parsing Action / Action Input responses."""

    @classmethod
    def setUpClass(cls):
        _set_env()
        _clean_chanakya_modules()
        from src.chanakya.core.react_agent import CustomReActSingleInputOutputParser
        cls.parser = CustomReActSingleInputOutputParser()

    def test_simple_action(self):
        """Action: tool_name\nAction Input: input_string should be parsed as AgentAction."""
        from langchain_core.agents import AgentAction
        text = "Thought: I need to search.\nAction: brave_search\nAction Input: weather today"
        result = self.parser.parse(text)
        self.assertIsInstance(result, AgentAction)
        self.assertEqual(result.tool, 'brave_search')
        self.assertEqual(result.tool_input, 'weather today')

    def test_action_with_json_input(self):
        """Action Input with a JSON object should be parsed to a dict."""
        from langchain_core.agents import AgentAction
        text = 'Thought: I need data.\nAction: fetch\nAction Input: {"url": "http://example.com"}'
        result = self.parser.parse(text)
        self.assertIsInstance(result, AgentAction)
        self.assertEqual(result.tool, 'fetch')
        self.assertIsInstance(result.tool_input, dict)
        self.assertEqual(result.tool_input['url'], 'http://example.com')

    def test_action_inside_think_block(self):
        """Action inside <think>...</think> should be extracted correctly."""
        from langchain_core.agents import AgentAction
        text = "<think>\nThought: Need search.\nAction: calculate\nAction Input: 2 + 2\n</think>"
        result = self.parser.parse(text)
        self.assertIsInstance(result, AgentAction)
        self.assertEqual(result.tool, 'calculate')

    def test_action_without_action_input_raises(self):
        """Action: without an Action Input: should raise OutputParserException."""
        from langchain_core.exceptions import OutputParserException
        text = "Action: some_tool"
        with self.assertRaises(OutputParserException):
            self.parser.parse(text)

    def test_action_with_quoted_json_input(self):
        """Action Input wrapped in outer quotes with JSON inside should work."""
        from langchain_core.agents import AgentAction
        text = 'Thought: calculate.\nAction: calculate\nAction Input: "{"expression": "3*4"}"'
        result = self.parser.parse(text)
        self.assertIsInstance(result, AgentAction)


class TestReActParserEdgeCases(unittest.TestCase):
    """Edge case tests for the parser."""

    @classmethod
    def setUpClass(cls):
        _set_env()
        _clean_chanakya_modules()
        from src.chanakya.core.react_agent import CustomReActSingleInputOutputParser
        cls.parser = CustomReActSingleInputOutputParser()

    def test_empty_think_block_raises(self):
        """An empty <think></think> should raise OutputParserException."""
        from langchain_core.exceptions import OutputParserException
        with self.assertRaises(OutputParserException):
            self.parser.parse("<think></think>")

    def test_just_think_keyword_raises(self):
        """The literal string '<think>' should raise OutputParserException."""
        from langchain_core.exceptions import OutputParserException
        with self.assertRaises(OutputParserException):
            self.parser.parse("<think>")

    def test_plain_text_returns_finish(self):
        """A plain statement without Action or Final Answer should return AgentFinish."""
        from langchain_core.agents import AgentFinish
        result = self.parser.parse("I don't need any tools for this.")
        self.assertIsInstance(result, AgentFinish)
        self.assertIn("don't need", result.return_values['output'])

    def test_both_action_and_final_answer_last_final_answer_wins(self):
        """When both Action and Final Answer present, and Final Answer is later, it wins."""
        from langchain_core.agents import AgentFinish
        text = (
            "Thought: Let me try.\n"
            "Action: search\n"
            "Action Input: test\n"
            "Final Answer: I found the answer."
        )
        result = self.parser.parse(text)
        self.assertIsInstance(result, AgentFinish)
        self.assertIn('found the answer', result.return_values['output'])

    def test_both_action_and_final_answer_action_later_returns_action(self):
        """When both Action and Final Answer present, and Action is later, action is attempted."""
        from langchain_core.agents import AgentAction
        text = (
            "Thought: I'm not sure.\n"
            "Final Answer: Let me check.\n"
            "Thought: Actually I need a tool.\n"
            "Action: search\n"
            "Action Input: something"
        )
        result = self.parser.parse(text)
        self.assertIsInstance(result, AgentAction)
        self.assertEqual(result.tool, 'search')


class TestReActParserJsonInput(unittest.TestCase):
    """Tests for _parse_json_input helper method."""

    @classmethod
    def setUpClass(cls):
        _set_env()
        _clean_chanakya_modules()
        from src.chanakya.core.react_agent import CustomReActSingleInputOutputParser
        cls.parser = CustomReActSingleInputOutputParser()

    def test_parses_json_object(self):
        result = self.parser._parse_json_input('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_parses_json_array(self):
        result = self.parser._parse_json_input('[1, 2, 3]')
        self.assertEqual(result, [1, 2, 3])

    def test_returns_string_for_non_json(self):
        result = self.parser._parse_json_input('just a string')
        self.assertEqual(result, 'just a string')

    def test_returns_string_for_invalid_json(self):
        result = self.parser._parse_json_input('{invalid}')
        self.assertEqual(result, '{invalid}')

    def test_strips_whitespace(self):
        result = self.parser._parse_json_input('  {"a": 1}  ')
        self.assertEqual(result, {"a": 1})


class TestReActParserType(unittest.TestCase):
    """Test the _type property."""

    @classmethod
    def setUpClass(cls):
        _set_env()
        _clean_chanakya_modules()
        from src.chanakya.core.react_agent import CustomReActSingleInputOutputParser
        cls.parser = CustomReActSingleInputOutputParser()

    def test_type_property(self):
        self.assertEqual(
            self.parser._type,
            "custom_react_parser_chanakya_v_outer_think"
        )


if __name__ == '__main__':
    unittest.main()
