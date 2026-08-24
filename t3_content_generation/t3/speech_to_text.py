import base64
import os

from commons.constants import OPENAI_HOST, DIAL_API_VERSION
from t3_content_generation._openai_client import OpenAIClientT3


# https://developers.openai.com/api/docs/guides/speech-to-text

#TODO:
# You need to transcribe 'audio_sample.mp3':
#   - Create Client that will go to transcriptions OpenAI API
#   - Call API and provide file (pay attention that you work with 'multipart/form-data')
#   - Get response with transcription
# ---
# Hints:
#   - Use /v1/audio/transcriptions endpoint
#   - Use whisper-1 or gpt-4o-transcribe model
MODEL = "gpt-4o-transcribe"
endpoint = f"{OPENAI_HOST}/openai/deployments/{MODEL}/chat/completions?api-version={DIAL_API_VERSION}"

audio_path = os.path.join(os.path.dirname(__file__), "audio_sample.mp3")

with open(audio_path, "rb") as audio_file:
    audio_b64 = base64.b64encode(audio_file.read()).decode("utf-8")

client = OpenAIClientT3(endpoint=endpoint)
response = client.call(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": "Transcribe the audio",
            "custom_content": {
                "attachments": [
                    {"type": "audio/mpeg", "data": audio_b64}
                ]
            }
        }
    ]
)

print(response["choices"][0]["message"]["content"])
