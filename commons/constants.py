"""
Configuration constants for AI service integrations.

This module centralizes all API endpoints, API keys, and default configuration
values used across different AI service providers (OpenAI, Anthropic, Gemini).

All API keys are loaded from environment variables for security.
"""
from dotenv import load_dotenv
load_dotenv()

import os

# Default system prompt used across all AI services
DEFAULT_SYSTEM_PROMPT = "You are an assistant who answers concisely and informatively."

# OpenAI API configuration (via EPAM DIAL gateway)
DIAL_HOST = "https://ai-proxy.lab.epam.com"
DIAL_API_VERSION = "2025-04-01-preview"
OPENAI_HOST = DIAL_HOST
OPENAI_CHAT_COMPLETIONS_ENDPOINT = DIAL_HOST
OPENAI_RESPONSES_ENDPOINT = f"{DIAL_HOST}/openai/v1/responses"
OPENAI_EMBEDDINGS_ENDPOINT = f"{DIAL_HOST}/openai/deployments"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Anthropic API configuration
ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# Google Gemini API configuration
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# User Service API configuration
USER_SERVICE_ENDPOINT = "http://localhost:8041"