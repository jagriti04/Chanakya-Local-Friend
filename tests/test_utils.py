"""
Tests for src/chanakya/utils/utils.py

Focus: get_plain_text_content() function - cleaning and extracting
plain text from various input types.
"""

import sys
import unittest

sys.path.insert(0, "/home/jailuser/git")

from src.chanakya.utils.utils import get_plain_text_content


class TestGetPlainTextContentStringInput(unittest.TestCase):
    """Tests when input is a plain string."""

    def test_plain_string_returned_as_is(self):
        result = get_plain_text_content("Hello world")
        self.assertEqual(result, "Hello world")

    def test_strips_leading_whitespace(self):
        result = get_plain_text_content("  hello  ")
        self.assertEqual(result, "hello")

    def test_empty_string_returns_empty(self):
        result = get_plain_text_content("")
        self.assertEqual(result, "")

    def test_whitespace_only_returns_empty(self):
        result = get_plain_text_content("   \n  ")
        self.assertEqual(result, "")


class TestGetPlainTextContentDictInput(unittest.TestCase):
    """Tests when input is a dict (agent executor output)."""

    def test_extracts_output_key(self):
        result = get_plain_text_content({"output": "Hello from agent"})
        self.assertEqual(result, "Hello from agent")

    def test_extracts_output_key_strips_whitespace(self):
        result = get_plain_text_content({"output": "  Hello  "})
        self.assertEqual(result, "Hello")

    def test_dict_without_output_key_converted_to_str(self):
        result = get_plain_text_content({"response": "test"})
        # No "output" key, so it falls through to str()
        self.assertIsInstance(result, str)

    def test_output_key_with_think_tags_cleaned(self):
        result = get_plain_text_content({"output": "<think>reasoning</think>answer"})
        self.assertEqual(result, "answer")


class TestGetPlainTextContentThinkTagRemoval(unittest.TestCase):
    """Tests for <think>...</think> tag removal."""

    def test_removes_think_tags_and_content(self):
        result = get_plain_text_content("<think>internal reasoning</think>Final answer")
        self.assertEqual(result, "Final answer")

    def test_removes_multiline_think_tags(self):
        text = "<think>\nLine 1\nLine 2\n</think>Result"
        result = get_plain_text_content(text)
        self.assertEqual(result, "Result")

    def test_removes_self_closing_think_tag(self):
        result = get_plain_text_content("before<think/>after")
        self.assertEqual(result, "beforeafter")

    def test_removes_think_with_spaces_in_self_closing(self):
        result = get_plain_text_content("before<think />after")
        self.assertEqual(result, "beforeafter")

    def test_handles_no_think_tags(self):
        result = get_plain_text_content("Just plain text")
        self.assertEqual(result, "Just plain text")

    def test_multiple_think_blocks_all_removed(self):
        text = "<think>first</think>middle<think>second</think>end"
        result = get_plain_text_content(text)
        self.assertEqual(result, "middleend")


class TestGetPlainTextContentToolCallRemoval(unittest.TestCase):
    """Tests for <tool_call> tag removal."""

    def test_removes_tool_call_and_rest_of_text(self):
        result = get_plain_text_content("Before text<tool_call>some tool call data")
        self.assertEqual(result, "Before text")

    def test_removes_tool_call_multiline(self):
        result = get_plain_text_content('Prefix\n<tool_call>\n{"tool": "search"}\n')
        self.assertEqual(result, "Prefix")


class TestGetPlainTextContentMarkdownCleaning(unittest.TestCase):
    """Tests for Markdown syntax removal."""

    def test_removes_bold_asterisks(self):
        result = get_plain_text_content("**bold text**")
        self.assertEqual(result, "bold text")

    def test_removes_italic_asterisks(self):
        result = get_plain_text_content("*italic text*")
        self.assertEqual(result, "italic text")

    def test_removes_italic_underscore(self):
        result = get_plain_text_content("_italic_")
        self.assertEqual(result, "italic")

    def test_removes_inline_code(self):
        result = get_plain_text_content("`code snippet`")
        self.assertEqual(result, "code snippet")

    def test_removes_heading_hash(self):
        result = get_plain_text_content("# Heading")
        # The # is removed and the resulting " Heading" is stripped by final normalization
        self.assertEqual(result, "Heading")

    def test_removes_code_block(self):
        result = get_plain_text_content("```python\nprint('hello')\n```")
        self.assertNotIn("```", result)

    def test_removes_remaining_asterisks(self):
        # After bold/italic removal, any remaining * should be removed
        result = get_plain_text_content("some * text")
        self.assertNotIn("*", result)


class TestGetPlainTextContentEmojiRemoval(unittest.TestCase):
    """Tests for emoji removal."""

    def test_removes_emoji(self):
        result = get_plain_text_content("Hello \U0001f600 World")
        self.assertNotIn("\U0001f600", result)
        self.assertIn("Hello", result)
        self.assertIn("World", result)

    def test_removes_multiple_emojis(self):
        result = get_plain_text_content("\U0001f680 Rocket \U0001f44d Thumbs up")
        self.assertNotIn("\U0001f680", result)
        self.assertNotIn("\U0001f44d", result)

    def test_no_emoji_unchanged(self):
        result = get_plain_text_content("No emojis here")
        self.assertEqual(result, "No emojis here")


class TestGetPlainTextContentWhitespaceNormalization(unittest.TestCase):
    """Tests for whitespace normalization."""

    def test_collapses_multiple_spaces(self):
        result = get_plain_text_content("too   many   spaces")
        self.assertEqual(result, "too many spaces")

    def test_collapses_tabs(self):
        result = get_plain_text_content("tab\there")
        self.assertEqual(result, "tab here")

    def test_preserves_newlines(self):
        result = get_plain_text_content("line1\nline2")
        self.assertIn("\n", result)

    def test_strips_final_result(self):
        result = get_plain_text_content("  hello  ")
        self.assertEqual(result, "hello")


class TestGetPlainTextContentBaseMessageInput(unittest.TestCase):
    """Tests when input is a BaseMessage-like object."""

    def test_extracts_content_from_base_message(self):
        from langchain_core.messages import AIMessage

        msg = AIMessage(content="AI response text")
        result = get_plain_text_content(msg)
        self.assertEqual(result, "AI response text")

    def test_extracts_content_with_think_tags(self):
        from langchain_core.messages import AIMessage

        msg = AIMessage(content="<think>thinking</think>answer")
        result = get_plain_text_content(msg)
        self.assertEqual(result, "answer")


class TestGetPlainTextContentOtherTypes(unittest.TestCase):
    """Tests when input is a non-standard type."""

    def test_integer_input_converted(self):
        result = get_plain_text_content(42)
        self.assertEqual(result, "42")

    def test_none_input_converted_to_none_string(self):
        result = get_plain_text_content(None)
        self.assertEqual(result, "None")

    def test_list_input_converted_to_string(self):
        result = get_plain_text_content(["item1", "item2"])
        self.assertIsInstance(result, str)


class TestGetPlainTextContentEdgeCases(unittest.TestCase):
    """Edge cases and regression tests."""

    def test_complex_mixed_input(self):
        text = "<think>Let me reason</think>**Important** result: `code` _italic_"
        result = get_plain_text_content(text)
        self.assertNotIn("<think>", result)
        self.assertNotIn("**", result)
        self.assertNotIn("`", result)
        self.assertIn("Important", result)
        self.assertIn("result", result)

    def test_no_double_space_after_cleaning(self):
        # After removing markdown, should not have double spaces
        result = get_plain_text_content("word **bold** word")
        self.assertNotIn("  ", result)

    def test_output_with_think_and_markdown(self):
        payload = {"output": "<think>reasoning</think>**Bold answer**: yes"}
        result = get_plain_text_content(payload)
        self.assertNotIn("<think>", result)
        self.assertNotIn("**", result)
        self.assertIn("Bold answer", result)

    def test_hash_inside_url_preserved_if_no_space(self):
        # Hash not preceded by whitespace shouldn't be stripped by comment logic,
        # but the # removal at the end of get_plain_text_content removes all #
        result = get_plain_text_content("test#value")
        # The function removes all # with re.sub(r'#', '', cleaned_text)
        self.assertNotIn("#", result)

    def test_long_think_block_removed(self):
        long_think = "<think>" + ("reasoning " * 100) + "</think>Final"
        result = get_plain_text_content(long_think)
        self.assertEqual(result, "Final")


if __name__ == "__main__":
    unittest.main()
