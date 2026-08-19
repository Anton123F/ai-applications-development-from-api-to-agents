import os

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
print(f"OpenAI API Key: {OPENAI_API_KEY}")  # Print only the first 4 characters for security