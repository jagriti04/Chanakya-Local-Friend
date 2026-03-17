"""
Utility functions for text processing and response handling.

Provides get_plain_text_content() to extract clean text from various response types.
"""

import re

from langchain_core.messages import BaseMessage

last_ai_response = ""


def get_plain_text_content(response_object):
    """Extract and clean plain text from dict, BaseMessage, or string responses."""
    raw_text = ""
    if isinstance(response_object, dict) and "output" in response_object:
        raw_text = str(response_object["output"]).strip()
    elif isinstance(response_object, BaseMessage) and hasattr(response_object, "content"):
        raw_text = str(response_object.content).strip()
    elif isinstance(response_object, str):
        raw_text = response_object.strip()
    else:
        raw_text = str(response_object).strip()
    cleaned_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
    cleaned_text = re.sub(r"<think\s*/>", "", cleaned_text)
    cleaned_text = re.sub(r"<tool_call>.*", "", cleaned_text, flags=re.DOTALL)
    cleaned_text = re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", cleaned_text)
    cleaned_text = re.sub(r"_(.*?)_", r"\1", cleaned_text)
    cleaned_text = re.sub(r"`(.*?)`", r"\1", cleaned_text)
    cleaned_text = re.sub(r"#", "", cleaned_text)
    cleaned_text = cleaned_text.replace("```python", "").replace("```", "")
    emoji_pattern = re.compile(
        r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U000024C2-\U0001F251]+",
        flags=re.UNICODE,
    )
    cleaned_text = emoji_pattern.sub(r"", cleaned_text)
    cleaned_text = cleaned_text.replace("*", "")
    cleaned_text = re.sub(r"[^\S\r\n]+", " ", cleaned_text).strip()
    return cleaned_text
