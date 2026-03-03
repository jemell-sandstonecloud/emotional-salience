"""Tests for Bedrock LLM abstraction — model family detection, body formatting, fallback."""

import os
import sys
import unittest
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bedrock import (
    detect_model_family,
    _format_anthropic_body, _format_meta_body, _format_mistral_body,
    _format_titan_body, _format_cohere_body,
    _extract_response_text, invoke_model,
)


class TestModelFamilyDetection(unittest.TestCase):
    def test_anthropic_models(self):
        self.assertEqual(detect_model_family('us.anthropic.claude-sonnet-4-5-v1'), 'anthropic')
        self.assertEqual(detect_model_family('us.anthropic.claude-haiku-4-5-v1'), 'anthropic')
        self.assertEqual(detect_model_family('us.anthropic.claude-opus-4-v1'), 'anthropic')
        self.assertEqual(detect_model_family('anthropic.claude-3-5-sonnet-20241022-v2:0'), 'anthropic')

    def test_meta_models(self):
        self.assertEqual(detect_model_family('us.meta.llama3-1-70b-instruct-v1:0'), 'meta')

    def test_mistral_models(self):
        self.assertEqual(detect_model_family('mistral.mistral-large-2407-v1:0'), 'mistral')

    def test_amazon_models(self):
        self.assertEqual(detect_model_family('amazon.titan-text-premier-v1:0'), 'amazon')

    def test_cohere_models(self):
        self.assertEqual(detect_model_family('cohere.command-r-plus-v1:0'), 'cohere')

    def test_unknown_defaults_to_anthropic(self):
        self.assertEqual(detect_model_family('some.unknown.model'), 'anthropic')


class TestBodyFormatting(unittest.TestCase):
    def setUp(self):
        self.system_prompt = "You are a helpful assistant."
        self.messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there!'},
            {'role': 'user', 'content': 'How are you?'},
        ]
        self.max_tokens = 500

    def test_anthropic_body(self):
        body = _format_anthropic_body(self.system_prompt, self.messages, self.max_tokens)
        self.assertEqual(body['anthropic_version'], 'bedrock-2023-05-31')
        self.assertEqual(body['max_tokens'], 500)
        self.assertEqual(body['system'], self.system_prompt)
        self.assertEqual(len(body['messages']), 3)

    def test_meta_body(self):
        body = _format_meta_body(self.system_prompt, self.messages, self.max_tokens)
        self.assertIn('prompt', body)
        self.assertIn('system', body['prompt'])
        self.assertEqual(body['max_gen_len'], 500)
        self.assertIn('<|begin_of_text|>', body['prompt'])

    def test_mistral_body(self):
        body = _format_mistral_body(self.system_prompt, self.messages, self.max_tokens)
        self.assertEqual(body['max_tokens'], 500)
        self.assertEqual(len(body['messages']), 4)  # system + 3 conversation
        self.assertEqual(body['messages'][0]['role'], 'system')

    def test_titan_body(self):
        body = _format_titan_body(self.system_prompt, self.messages, self.max_tokens)
        self.assertIn('inputText', body)
        self.assertIn('System:', body['inputText'])
        self.assertEqual(body['textGenerationConfig']['maxTokenCount'], 500)

    def test_cohere_body(self):
        body = _format_cohere_body(self.system_prompt, self.messages, self.max_tokens)
        self.assertEqual(body['preamble'], self.system_prompt)
        self.assertIn('message', body)
        self.assertEqual(body['max_tokens'], 500)


class TestResponseExtraction(unittest.TestCase):
    def test_anthropic_extraction(self):
        body = {'content': [{'type': 'text', 'text': 'Hello world'}]}
        self.assertEqual(_extract_response_text(body, 'anthropic'), 'Hello world')

    def test_meta_extraction(self):
        body = {'generation': 'Hello from Llama'}
        self.assertEqual(_extract_response_text(body, 'meta'), 'Hello from Llama')

    def test_mistral_extraction(self):
        body = {'choices': [{'message': {'content': 'Hello from Mistral'}}]}
        self.assertEqual(_extract_response_text(body, 'mistral'), 'Hello from Mistral')

    def test_titan_extraction(self):
        body = {'results': [{'outputText': 'Hello from Titan'}]}
        self.assertEqual(_extract_response_text(body, 'amazon'), 'Hello from Titan')

    def test_cohere_extraction(self):
        body = {'text': 'Hello from Cohere'}
        self.assertEqual(_extract_response_text(body, 'cohere'), 'Hello from Cohere')

    def test_empty_response(self):
        self.assertEqual(_extract_response_text({'content': []}, 'anthropic'), '')


class TestInvokeModelFallback(unittest.TestCase):
    def test_invoke_returns_string(self):
        """invoke_model should always return a string, even in mock/fallback mode."""
        result = invoke_model(
            'us.anthropic.claude-sonnet-4-5-v1',
            'You are a test assistant.',
            [{'role': 'user', 'content': 'Test message'}],
            max_tokens=100
        )
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_invoke_with_none_model(self):
        """None model_id should use default."""
        result = invoke_model(
            None,
            'System prompt',
            [{'role': 'user', 'content': 'Hello'}],
        )
        self.assertIsInstance(result, str)


if __name__ == '__main__':
    unittest.main()
