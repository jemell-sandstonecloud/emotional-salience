"""
Sandstone Bedrock LLM Abstraction.

Routes LLM calls through Amazon Bedrock. Handles multiple model families:
- Anthropic Claude (us.anthropic.*)
- Meta Llama (us.meta.*)
- Mistral (mistral.*)
- Amazon Titan (amazon.*)
- Cohere Command (cohere.*)

Falls back to direct Anthropic SDK if Bedrock unavailable.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

try:
    import boto3
except ImportError:
    boto3 = None


def detect_model_family(model_id):
    """Detect model family from model_id prefix."""
    if not model_id:
        return 'anthropic'
    if model_id.startswith('us.anthropic.') or model_id.startswith('anthropic.'):
        return 'anthropic'
    elif model_id.startswith('us.meta.') or model_id.startswith('meta.'):
        return 'meta'
    elif model_id.startswith('mistral.'):
        return 'mistral'
    elif model_id.startswith('amazon.'):
        return 'amazon'
    elif model_id.startswith('cohere.'):
        return 'cohere'
    else:
        return 'anthropic'


def _format_anthropic_body(system_prompt, messages, max_tokens):
    """Format request body for Anthropic Claude models via Bedrock."""
    return {
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': max_tokens,
        'system': system_prompt,
        'messages': messages,
    }


def _format_meta_body(system_prompt, messages, max_tokens):
    """Format request body for Meta Llama models via Bedrock."""
    prompt_parts = [f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|>"]
    for msg in messages:
        role = msg['role']
        content = msg['content']
        prompt_parts.append(f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>")
    prompt_parts.append("<|start_header_id|>assistant<|end_header_id|>\n\n")

    return {
        'prompt': ''.join(prompt_parts),
        'max_gen_len': max_tokens,
        'temperature': 0.7,
    }


def _format_mistral_body(system_prompt, messages, max_tokens):
    """Format request body for Mistral models via Bedrock."""
    all_messages = [{'role': 'system', 'content': system_prompt}] + messages
    return {
        'messages': all_messages,
        'max_tokens': max_tokens,
        'temperature': 0.7,
    }


def _format_titan_body(system_prompt, messages, max_tokens):
    """Format request body for Amazon Titan models via Bedrock."""
    user_messages = [m['content'] for m in messages if m['role'] == 'user']
    input_text = f"System: {system_prompt}\n\nUser: {user_messages[-1] if user_messages else ''}"
    return {
        'inputText': input_text,
        'textGenerationConfig': {
            'maxTokenCount': max_tokens,
            'temperature': 0.7,
            'topP': 0.9,
        }
    }


def _format_cohere_body(system_prompt, messages, max_tokens):
    """Format request body for Cohere Command models via Bedrock."""
    user_messages = [m['content'] for m in messages if m['role'] == 'user']
    chat_history = []
    for msg in messages[:-1]:
        role = 'USER' if msg['role'] == 'user' else 'CHATBOT'
        chat_history.append({'role': role, 'message': msg['content']})

    return {
        'message': user_messages[-1] if user_messages else '',
        'chat_history': chat_history,
        'preamble': system_prompt,
        'max_tokens': max_tokens,
        'temperature': 0.7,
    }


def _extract_response_text(response_body, family):
    """Extract plain text response from model-specific response format."""
    if family == 'anthropic':
        content = response_body.get('content', [])
        return content[0].get('text', '') if content else ''
    elif family == 'meta':
        return response_body.get('generation', '')
    elif family == 'mistral':
        choices = response_body.get('choices', [])
        if choices:
            return choices[0].get('message', {}).get('content', '')
        return ''
    elif family == 'amazon':
        results = response_body.get('results', [])
        if results:
            return results[0].get('outputText', '')
        return ''
    elif family == 'cohere':
        return response_body.get('text', '')
    else:
        return str(response_body)


def invoke_model(model_id, system_prompt, messages, max_tokens=1000):
    """
    Main entry point — invoke a Bedrock model.

    Args:
        model_id: Bedrock model ID (e.g. 'us.anthropic.claude-sonnet-4-5-v1')
        system_prompt: System prompt string
        messages: List of {'role': 'user'|'assistant', 'content': '...'}
        max_tokens: Max response tokens

    Returns:
        Plain text response string.
        Falls back to direct Anthropic SDK if Bedrock unavailable.
    """
    if model_id is None:
        model_id = config.BEDROCK_DEFAULT_MODEL

    family = detect_model_family(model_id)

    formatters = {
        'anthropic': _format_anthropic_body,
        'meta': _format_meta_body,
        'mistral': _format_mistral_body,
        'amazon': _format_titan_body,
        'cohere': _format_cohere_body,
    }
    formatter = formatters.get(family, _format_anthropic_body)
    body = formatter(system_prompt, messages, max_tokens)

    if boto3 is None:
        return _fallback_anthropic(system_prompt, messages, max_tokens)

    try:
        client = boto3.client('bedrock-runtime', region_name=config.BEDROCK_REGION)
        response = client.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=json.dumps(body)
        )
        response_body = json.loads(response['body'].read())
        return _extract_response_text(response_body, family)

    except Exception as e:
        try:
            return _fallback_anthropic(system_prompt, messages, max_tokens)
        except Exception:
            return f"[MOCK RESPONSE — no LLM available] Model: {model_id}, Context: {system_prompt[:200]}..."


def _fallback_anthropic(system_prompt, messages, max_tokens):
    """Fall back to direct Anthropic SDK."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text
    except ImportError:
        return f"[MOCK RESPONSE — anthropic SDK not installed] Context: {system_prompt[:200]}..."
    except Exception as e:
        return f"[API ERROR: {str(e)}] Context: {system_prompt[:200]}..."
