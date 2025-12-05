"""
Model Configuration

This module defines context window limits and helper functions for different LLM models.
Context windows are specified in tokens.
"""

# Model context windows (in tokens)
# We reserve 20% for the response, so 80% is available for input
MODEL_CONTEXT_WINDOWS = {
    'gemma3:1b': 32000,      # 32k total context
    'qwen3:1.7b': 40000,     # 40k total context
    'ministral-3:3b': 256000, # 256k total context
}

# Default fallback for unknown models
DEFAULT_CONTEXT_WINDOW = 4096

# Reserve percentage for response generation
INPUT_RESERVE_RATIO = 0.8  # 80% for input, 20% for response


def get_model_context_window(model_name: str) -> int:
    """
    Get the total context window for a model (in tokens).

    Args:
        model_name: Name of the Ollama model (e.g., 'gemma3:1b')

    Returns:
        int: Total context window size in tokens
    """
    return MODEL_CONTEXT_WINDOWS.get(model_name, DEFAULT_CONTEXT_WINDOW)


def get_max_input_tokens(model_name: str) -> int:
    """
    Get maximum tokens available for input (reserves space for response).

    Args:
        model_name: Name of the Ollama model

    Returns:
        int: Maximum input tokens (80% of total context window)
    """
    total = get_model_context_window(model_name)
    return int(total * INPUT_RESERVE_RATIO)


def get_max_input_chars(model_name: str) -> int:
    """
    Get maximum characters available for input.
    Uses conservative estimate of 4 characters per token.

    Args:
        model_name: Name of the Ollama model

    Returns:
        int: Approximate maximum input characters
    """
    max_tokens = get_max_input_tokens(model_name)
    # Conservative estimate: 4 characters per token
    return max_tokens * 4
