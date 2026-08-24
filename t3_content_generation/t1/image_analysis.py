import base64
import os

from commons.constants import OPENAI_HOST, DIAL_API_VERSION
from t3_content_generation._openai_client import OpenAIClientT3


# https://developers.openai.com/api/docs/guides/images-vision?format=url&lang=curl
# https://developers.openai.com/api/docs/guides/images-vision?format=base64-encoded

#TODO:
# You need to analyse these 2 images:
#   - https://a-z-animals.com/media/2019/11/Elephant-male-1024x535.jpg
#   - in this folder we have 'logo.png', load it as encoded data (see documentation)
# ---
# Hints:
#   - Use OpenAIClientT3 to connect to OpenAI API
#   - Use /v1/chat/completions endpoint
#   - Function to encode image to base64 you can find in documentation
# ---
# In the end load both images (url and base64 encoded 'logo.png'), ask "Generate poem based on images" and se what will happen?

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
logo_base64 = encode_image(logo_path)

endpoint = f"{OPENAI_HOST}/openai/deployments/gpt-4o/chat/completions?api-version={DIAL_API_VERSION}"
client = OpenAIClientT3(endpoint=endpoint)

# client.call(
#     model="gpt-4o",
#     messages=[{"role": "user", "content": "Say hello"}]
# )

client.call(
    model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Generate poem based on images"},
                {
                    "type": "image_url",
                    "image_url": {"url": "https://a-z-animals.com/media/2019/11/Elephant-male-1024x535.jpg"}
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{logo_base64}"}
                }
            ]
        }
    ]
)
