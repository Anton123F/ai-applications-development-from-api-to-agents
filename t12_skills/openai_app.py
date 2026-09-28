import io
import json
import zipfile
from pathlib import Path

from openai import OpenAI
from openai.types.responses import ResponseFunctionShellToolCall

from commons.constants import OPENAI_API_KEY


def zip_skill(skill_dir: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path in skill_dir.rglob("*"):
            if path.is_file():
                z.write(path, arcname=path.relative_to(skill_dir.parent))
    buf.seek(0)
    return buf.read()


def get_or_create_skill(skill_name: str, skill_dir: Path, client: OpenAI):
    #TODO:
    # - List existing skills and return the ID if one with matching name already exists
    # - Otherwise zip the skill directory using zip_skill()
    # - Upload the zip as a new skill and return its ID
    pages = client.skills.list()
    for page in pages:
        for skill in page.data:
            if skill.name == skill_name:
                return skill.id
    z_skill = zip_skill(skill_dir=skill_dir)
    skill = client.skills.create(files=z_skill)
    return skill.id

def chat(client: OpenAI, skill_id: str, log_request: bool = True, log_response: bool = True):
    previous_response_id = None

    print("\nAgent is ready. Type your query or 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            break

        #TODO:
        # - Build an environment dict with type "container_auto" and the skill reference (type "skill_reference", skill_id)
        # - Build the request_payload (model, input with user message, shell tool with the environment)
        # - If previous_response_id is set, include it in the payload to chain conversation history
        # - If log_request is True, print the payload as indented JSON
        # - Call client.responses.create with the payload and save the response
        # - Update previous_response_id from the response
        # - If log_response is True, print the full response as indented JSON;
        #   otherwise print response.output_text
        environment = {
            "type": "container_auto",
            "skill_reference": {"type": "skill_reference", "skill_id": skill_id}
        }

        payload = {
            "model": "gpt-4o",
            "input": [{"role": "user", "content": user_input}],
            "tools": [{"type": "shell", "environment": environment}]
        }

        if previous_response_id:
            payload['previous_response_id'] = previous_response_id
        if log_request:
            print(json.dumps(payload, indent=4))
        response = client.responses.create(**payload)
        previous_response_id = response.id

        if log_response:
            print(json.dumps(response.to_dict(), indent=4))
        else:
            print(f"{response.output_text}")


def delete_skills(client: OpenAI):
    #TODO:
    # - List all uploaded skills
    # - Delete each one and print its name as confirmation
    skills = client.skills.list()
    for skill in skills.data:
        client.skills.delete(skill.id)
        print(skill.name)


STYLE_SKILL_NAME= "style-guide"
STYLE_SKILL_DIR = Path(__file__).parent / "_skills" / STYLE_SKILL_NAME

CALCULATOR_SKILL_NAME = "calculator"
CALCULATOR_SKILL_DIR = Path(__file__).parent / "_skills" / CALCULATOR_SKILL_NAME

def main():
    #TODO:
    # - Create an OpenAI client
    # - Call get_or_create_skill (choose CALCULATOR or STYLE skill dir/name to test)
    # - Call chat with the client and skill_id
    # - Call delete_skills to clean up after the session
    client = OpenAI()
    skill_id = get_or_create_skill(client=client, skill_name=CALCULATOR_SKILL_NAME, skill_dir=CALCULATOR_SKILL_DIR)

    chat(client=client, skill_id=skill_id)
    delete_skills(client=client)

if __name__ == "__main__":
    main()