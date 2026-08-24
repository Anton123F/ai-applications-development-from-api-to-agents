import base64
import os
from datetime import datetime

import requests as _requests

from commons.constants import OPENAI_API_KEY, OPENAI_HOST, DIAL_API_VERSION
from t3_content_generation._openai_client import OpenAIClientT3

# https://developers.openai.com/api/docs/guides/audio#add-audio-to-your-existing-application

#TODO:
# You need to generate answer in audio format based on the audio message:
#   - Create Client that is similar with OpenAIClients but extracts from message audio (instead of content)
#   - Call API
#   - Get response as base64 content, decode and save as .mp3 file
# ---
# Hints:
#   - Use /v1/chat/completions endpoint
#   - Use gpt-4o-audio-preview model
#   - Use modalities=["text", "audio"]
#   - Use audio={"voice": "ballad", "format": "mp3"}
#   - Use similar method to encode audio as you have done for images encoding


class OpenAIAudioClient(OpenAIClientT3):
    def call_audio(self, **kwargs) -> bytes:
        response = self.call(print_request=False, print_response=False, **kwargs)
        attachment_url = response["choices"][0]["message"]["custom_content"]["attachments"][0]["url"]
        full_url = attachment_url if attachment_url.startswith("http") else f"{OPENAI_HOST}/v1/{attachment_url}"

        audio_response = _requests.get(full_url, headers={"api-key": OPENAI_API_KEY})

        if audio_response.status_code != 200:
            raise Exception(f"Download failed HTTP {audio_response.status_code}: {audio_response.text}")
        return audio_response.content

STT_MODEL = "gpt-4o-transcribe"
stt_endpoint = f"{OPENAI_HOST}/openai/deployments/{STT_MODEL}/chat/completions?api-version={DIAL_API_VERSION}"

audio_path = os.path.join(os.path.dirname(__file__), "question.mp3")
with open(audio_path, "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode("utf-8")

stt_client = OpenAIClientT3(endpoint=stt_endpoint)
stt_response = stt_client.call(
    model=STT_MODEL,
    messages=[
        {
            "role": "user",
            "content": "Transcribe the audio",
            "custom_content": {
                "attachments": [{"type": "audio/mpeg", "data": audio_b64}]
            }
        }
    ]
)
question_text = stt_response["choices"][0]["message"]["content"]
print(f"Question: {question_text}")

CHAT_MODEL = "gpt-4o"
chat_endpoint = f"{OPENAI_HOST}/openai/deployments/{CHAT_MODEL}/chat/completions?api-version={DIAL_API_VERSION}"

chat_client = OpenAIClientT3(endpoint=chat_endpoint)
chat_response = chat_client.call(
    model=CHAT_MODEL,
    messages=[
        {"role": "system", "content": "Answer the question in a helpful and concise way."},
        {"role": "user", "content": question_text}
    ]
)
answer_text = chat_response["choices"][0]["message"]["content"]
print(f"Answer: {answer_text}")

TTS_MODEL = "tts-001"
tts_endpoint = f"{OPENAI_HOST}/openai/deployments/{TTS_MODEL}/chat/completions?api-version={DIAL_API_VERSION}"

audio_client = OpenAIAudioClient(endpoint=tts_endpoint)
audio_bytes = audio_client.call_audio(
    model=TTS_MODEL,
    messages=[
        {"role": "user", "content": answer_text}
    ]
)

output_path = os.path.join(os.path.dirname(__file__), f"answer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")
with open(output_path, "wb") as f:
    f.write(audio_bytes)

print(f"Saved to {output_path}")
