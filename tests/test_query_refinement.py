"""
Tests for src/chanakya/core/query_refinement.py

Focus: get_query_refinement_chain returns correct LLM types based on provider,
returns None when small model is not configured, and raises ValueError for unknown providers.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock


def _clean_chanakya_modules():
    for key in list(sys.modules.keys()):
        if 'chanakya' in key:
            del sys.modules[key]


class TestQueryRefinementOllamaProvider(unittest.TestCase):
    """Tests when LLM_PROVIDER is ollama."""

    def setUp(self):
        _clean_chanakya_modules()

    def test_returns_chain_with_ollama(self):
        """get_query_refinement_chain should return a chain for ollama provider."""
        with patch.dict(os.environ, {
            'APP_SECRET_KEY': 'test', 'FLASK_DEBUG': 'True',
            'DATABASE_PATH': ':memory:',
            'LLM_PROVIDER': 'ollama',
            'LLM_ENDPOINT': 'http://localhost:11434',
            'LLM_MODEL_NAME': 'llama3',
            'LLM_MODEL_NAME_SMALL': 'llama3',
            'LLM_ENDPOINT_SMALL': 'http://localhost:11434',
        }):
            from src.chanakya.core.query_refinement import get_query_refinement_chain
            chain = get_query_refinement_chain()
            self.assertIsNotNone(chain)


class TestQueryRefinementOpenAIProvider(unittest.TestCase):
    """Tests when LLM_PROVIDER is openai."""

    def setUp(self):
        _clean_chanakya_modules()

    def test_returns_chain_with_openai(self):
        """get_query_refinement_chain should return a chain for openai provider."""
        with patch.dict(os.environ, {
            'APP_SECRET_KEY': 'test', 'FLASK_DEBUG': 'True',
            'DATABASE_PATH': ':memory:',
            'LLM_PROVIDER': 'openai',
            'LLM_ENDPOINT': 'http://localhost:1234/v1',
            'LLM_MODEL_NAME': 'gpt-4',
            'LLM_MODEL_NAME_SMALL': 'gpt-3.5-turbo',
            'LLM_ENDPOINT_SMALL': 'http://localhost:1234/v1',
        }):
            from src.chanakya.core.query_refinement import get_query_refinement_chain
            chain = get_query_refinement_chain()
            self.assertIsNotNone(chain)


class TestQueryRefinementDisabled(unittest.TestCase):
    """Tests when small model is not configured."""

    def setUp(self):
        _clean_chanakya_modules()

    def test_returns_none_when_small_model_empty(self):
        """get_query_refinement_chain should return None when LLM_MODEL_NAME_SMALL is empty."""
        with patch.dict(os.environ, {
            'APP_SECRET_KEY': 'test', 'FLASK_DEBUG': 'True',
            'DATABASE_PATH': ':memory:',
            'LLM_PROVIDER': 'ollama',
            'LLM_ENDPOINT': 'http://localhost:11434',
            'LLM_MODEL_NAME': 'llama3',
            'LLM_MODEL_NAME_SMALL': '',
            'LLM_ENDPOINT_SMALL': 'http://localhost:11434',
        }):
            from src.chanakya.core.query_refinement import get_query_refinement_chain
            chain = get_query_refinement_chain()
            self.assertIsNone(chain)

    def test_returns_none_when_small_endpoint_empty(self):
        """get_query_refinement_chain should return None when LLM_ENDPOINT_SMALL is empty."""
        with patch.dict(os.environ, {
            'APP_SECRET_KEY': 'test', 'FLASK_DEBUG': 'True',
            'DATABASE_PATH': ':memory:',
            'LLM_PROVIDER': 'ollama',
            'LLM_ENDPOINT': 'http://localhost:11434',
            'LLM_MODEL_NAME': 'llama3',
            'LLM_MODEL_NAME_SMALL': 'llama3',
            'LLM_ENDPOINT_SMALL': '',
        }):
            from src.chanakya.core.query_refinement import get_query_refinement_chain
            chain = get_query_refinement_chain()
            self.assertIsNone(chain)


class TestQueryRefinementUnsupportedProvider(unittest.TestCase):
    """Tests with unsupported LLM_PROVIDER."""

    def setUp(self):
        _clean_chanakya_modules()

    def test_raises_for_unsupported_provider(self):
        """get_query_refinement_chain should raise ValueError for unknown providers."""
        with patch.dict(os.environ, {
            'APP_SECRET_KEY': 'test', 'FLASK_DEBUG': 'True',
            'DATABASE_PATH': ':memory:',
            'LLM_PROVIDER': 'anthropic',
            'LLM_ENDPOINT': 'http://localhost:11434',
            'LLM_MODEL_NAME': 'claude',
            'LLM_MODEL_NAME_SMALL': 'claude-small',
            'LLM_ENDPOINT_SMALL': 'http://localhost:11434',
        }):
            from src.chanakya.core.query_refinement import get_query_refinement_chain
            with self.assertRaises(ValueError) as ctx:
                get_query_refinement_chain()
            self.assertIn('anthropic', str(ctx.exception).lower())


class TestQueryRefinementLMStudioProvider(unittest.TestCase):
    """Tests when LLM_PROVIDER is lmstudio."""

    def setUp(self):
        _clean_chanakya_modules()

    def test_returns_chain_with_lmstudio(self):
        """get_query_refinement_chain should accept lmstudio as a provider."""
        with patch.dict(os.environ, {
            'APP_SECRET_KEY': 'test', 'FLASK_DEBUG': 'True',
            'DATABASE_PATH': ':memory:',
            'LLM_PROVIDER': 'lmstudio',
            'LLM_ENDPOINT': 'http://localhost:1234/v1',
            'LLM_MODEL_NAME': 'local-model',
            'LLM_MODEL_NAME_SMALL': 'local-model-small',
            'LLM_ENDPOINT_SMALL': 'http://localhost:1234/v1',
        }):
            from src.chanakya.core.query_refinement import get_query_refinement_chain
            chain = get_query_refinement_chain()
            self.assertIsNotNone(chain)


if __name__ == '__main__':
    unittest.main()
