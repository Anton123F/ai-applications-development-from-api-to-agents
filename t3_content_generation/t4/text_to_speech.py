import os
from datetime import datetime

import requests as _requests

from commons.constants import OPENAI_API_KEY, OPENAI_HOST, DIAL_API_VERSION
from t3_content_generation._openai_client import OpenAIClientT3


class Voice:
    alloy: str = 'alloy'
    ash: str = 'ash'
    ballad: str = 'ballad'
    coral: str = 'coral'
    echo: str = 'echo'
    fable: str = 'fable'
    nova: str = 'nova'
    onyx: str = 'onyx'
    sage: str = 'sage'
    shimmer: str = 'shimmer'


# https://developers.openai.com/api/docs/guides/text-to-speech
# Request:
# curl https://api.openai.com/v1/audio/speech \
#   -H "Authorization: Bearer $OPENAI_API_KEY" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "model": "gpt-4o-mini-tts",
#     "input": "Why can't we say that black is white?",
#     "voice": "coral",
#     "instructions": "Speak in a cheerful and positive tone."
#   }' \
# Response:
#   bytes with audio

#TODO:
# You need to convert text to speech:
#   - Create Client that will go to speech OpenAI API
#   - Call API
#   - Get response and save as .mp3 file
# ---
# Hints:
#   - Use /v1/audio/speech endpoint
#   - Use gpt-4o-mini-tts model

MODEL = "tts-001"
endpoint = f"{OPENAI_HOST}/openai/deployments/{MODEL}/chat/completions?api-version={DIAL_API_VERSION}"

client = OpenAIClientT3(endpoint=endpoint)
response = client.call(
    model=MODEL,
    messages=[
        {"role": "system", "content": f"Voice: {Voice.coral}. Speak in a cheerful and positive tone."},
        {"role": "user", "content": "Why can't we say that black is white?"}
    ]
)

attachment_url = response["choices"][0]["message"]["custom_content"]["attachments"][0]["url"]
full_url = attachment_url if attachment_url.startswith("http") else f"{OPENAI_HOST}/v1/{attachment_url}"

audio_response = _requests.get(full_url, headers={"api-key": OPENAI_API_KEY})
if audio_response.status_code != 200:
    raise Exception(f"Download failed HTTP {audio_response.status_code}: {audio_response.text}")

output_path = os.path.join(os.path.dirname(__file__), f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")
with open(output_path, "wb") as f:
    f.write(audio_response.content)

print(f"Saved to {output_path}")