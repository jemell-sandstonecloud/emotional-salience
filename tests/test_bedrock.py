"""Tests for Sandstone Bedrock LLM abstraction."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.bedrock import invoke_model, detect_model_family, _format_anthropic_body
import config


class TestDetectModelFamily(unittest.TestCase):
    def test_anthropic_model(self):
        self.assertEqual(detect_model_family("us.anthropic.claude-sonnet-4-5-v1"), "anthropic")

    def test_meta_model(self):
        self.assertEqual(detect_model_family("us.meta.llama3-1-70b-instruct-v1:0"), "meta")

    def test_mistral_model(self):
        self.assertEqual(detect_model_family("mistral.mistral-large-2407-v1:0"), "mistral")

    def test_titan_model(self):
        self.assertEqual(detect_model_family("amazon.titan-text-premier-v1:0"), "amazon")

    def test_default_model(self):
        family = detect_model_family(None)
        self.assertIsInstance(family, str)


class TestFormatAnthropicBody(unittest.TestCase):
    def test_body_structure(self):
        body = _format_anthropic_body(
            "You are helpful",
            [{"role": "user", "content": "Hello"}],
            1000
        )
        self.assertIn("messages", body)
        self.assertIn("system", body)
        self.assertIn("max_tokens", body)
        self.assertEqual(body["messages"], [{"role": "user", "content": "Hello"}])

    def test_max_tokens(self):
        body = _format_anthropic_body("sys", [{"role": "user", "content": "Hi"}], 500)
        self.assertEqual(body["max_tokens"], 500)


class TestInvokeModel(unittest.TestCase):
    @patch('core.bedrock.boto3')
    def test_invoke_returns_string(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.client.return_value = mock_client
        mock_client.invoke_model.return_value = {
            'body': MagicMock(read=MagicMock(return_value=b'{"content": [{"text": "Hello back!"}]}'))
        }
        result = invoke_model(None, "system", [{"role": "user", "content": "Hi"}], 500)
        self.assertIsInstance(result, str)


if __name__ == '__main__':
    unittest.main()
