import base64
import os
from datetime import datetime
import requests as _requests
from commons.constants import OPENAI_API_KEY

from commons.constants import OPENAI_HOST, DIAL_API_VERSION
from t3_content_generation._openai_client import OpenAIClientT3


# https://developers.openai.com/api/reference/resources/images/methods/generate
# ---
# Request:
# curl -X POST "https://api.openai.com/v1/images/generations" \
#     -H "Authorization: Bearer $OPENAI_API_KEY" \
#     -H "Content-type: application/json" \
#     -d '{
#         "model": "gpt-image-2",
#         "prompt": "smiling catdog."
#     }'
# Response:
# {
#   "created": 1699900000,
#   "data": [
#     {
#       "b64_json": Qt0n6ArYAEABGOhEoYgVAJFdt8jM79uW2DO...,
#     }
#   ]
# }

#TODO:
# You need to create some images with `gpt-image-2` model:
#   - Generate an image with 'Smiling catdog'
#   - Decode and save it locally
# ---
# Hints:
#   - Use OpenAIClientT3 to connect to OpenAI API
#   - Use /v1/images/generations endpoint
#   - The image will be returned in base64 format

MODEL = "gpt-image-2-2026-04-21"
endpoint = f"{OPENAI_HOST}/openai/deployments/{MODEL}/chat/completions?api-version={DIAL_API_VERSION}"
client = OpenAIClientT3(endpoint=endpoint)

response = client.call(
    model=MODEL,
    messages=[{"role": "user", "content": "Smiling catdog"}]
)

attachment_url = response["choices"][0]["message"]["custom_content"]["attachments"][0]["url"]
full_url = attachment_url if attachment_url.startswith("http") else f"{OPENAI_HOST}/v1/{attachment_url}"
print(f"Downloading from: {full_url}")

img_response = _requests.get(full_url, headers={"api-key": OPENAI_API_KEY})
if img_response.status_code != 200:
    raise Exception(f"Download failed HTTP {img_response.status_code}: {img_response.text}")
image_bytes = img_response.content
filename = os.path.join(os.path.dirname(__file__), f"catdog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

with open(filename, "wb") as f:
    f.write(image_bytes)

print(f"Saved: {filename}")
