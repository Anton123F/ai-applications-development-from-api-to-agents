import json
import anthropic
from pathlib import Path

from commons.constants import ANTHROPIC_API_KEY


SKILLS_VERSION = "skills-2025-10-02"

def get_or_create_skill(skill_title: str, skill_dir: Path,  client: anthropic.Anthropic) -> str:
    #TODO:
    # - List all custom skills using the beta skills API (source="custom", betas=[SKILLS_VERSION])
    # - If a skill with matching display_title already exists, print its info and return its ID
    # - Otherwise create a new skill with the title and files from skill_dir (use anthropic.lib.files_from_dir)
    # - Print the new skill ID and return it
    skills = client.beta.skills.list(source="custom", betas=[SKILLS_VERSION])
    is_match_skill = False
    for skill in skills:
        if skill.display_title == skill_title:
            is_match_skill = skill
            break
    if is_match_skill:
        print(f"{is_match_skill}")
        return is_match_skill.id
    else:
        beta_skill = client.beta.skills.create(display_title=skill_title, files=anthropic.lib.files_from_dir(skill_dir))
        print(f"new skill: => {beta_skill}")
        return beta_skill.id


def delete_skills(client: anthropic.Anthropic):
    #TODO:
    # - List all custom skills
    # - For each skill, list all its versions and delete each one (print confirmation per version)
    # - Then delete the skill itself (print confirmation)
    skills = client.beta.skills.list(source="custom", betas=[SKILLS_VERSION])
    for skill in skills:
        versions = client.beta.skills.versions.list(skill_id=skill.id, betas=[SKILLS_VERSION])
        for version in versions:
            beta_deleted_skill_version = client.beta.skills.versions.delete(
                version=version.version,
                skill_id=version.skill_id,
            )
            print(f"delete skill version :=> {beta_deleted_skill_version.id}")
        beta_deleted_skill = client.beta.skills.delete(
            skill_id=skill.id,
        )
        print(f"deleted skill: {beta_deleted_skill.id}")

def chat(client: anthropic.Anthropic, skill_id: str, log_request: bool=True, log_response: bool = True):
    """Multi-turn chat loop that reuses the container across turns."""
    messages = []
    container_id = None
    print("\nStyle Guide Agent is ready. Ask it to write, rewrite, or review any text.")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            break

        messages.append({"role": "user", "content": user_input})

        #TODO:
        # - Build a container dict with the skill reference (type "custom", skill_id, version "latest")
        # - If container_id is already set, include it in the container dict to reuse the running container
        # - Build the full request_payload (model, max_tokens, messages, container, betas, tools)
        #   Note: betas must include "code-execution-2025-08-25" and SKILLS_VERSION; tool type is "code_execution_20250825"
        # - If log_request is True, print the request payload as indented JSON
        # - Call client.beta.messages.create with the request payload
        # - If log_response is True, print the full response as indented JSON;
        #   otherwise join all text blocks from response.content and print as "Claude: <text>"
        # - If the response has a container, save its ID to container_id for reuse on next turns
        # - Append the assistant message to messages (role "assistant", content response.content)
        container = {
            "type": "custom", 
            "skill_id": skill_id,
            "version": "latest"
        }
        if container_id:
            container["container_id"] = container_id
        payload = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 1024,
            "messages": messages,
            "container": container,
            "tools": [{"type": "code_execution_20250825"}],
            "betas": ["code-execution-2025-08-25", SKILLS_VERSION]
        }
        if log_request:
            print(json.dumps(payload, indent=4))

        response = client.beta.messages.create(**payload)

        if log_response:
            print(json.dumps(response.model_dump(), indent=4))
        else:
            content = []
            for chunk in response.content:
                content.append(chunk.text)
            print(f"Claude: {' '.join(content)}")
        if response.container:
            container_id = response.container.id
        messages.append({"role": "assistant", "content": response.content})


STYLE_SKILL_TITLE = "style-guide"
STYLE_SKILL_DIR = Path(__file__).parent / "_skills" / STYLE_SKILL_TITLE

CALCULATOR_SKILL_TITLE = "calculator"
CALCULATOR_SKILL_DIR = Path(__file__).parent / "_skills" / CALCULATOR_SKILL_TITLE

def main():
    #TODO:
    # - Create an Anthropic client
    # - Call get_or_create_skill (choose STYLE_SKILL or CALCULATOR_SKILL dir/title to test)
    # - Call chat with the client and skill_id
    # - Call delete_skills to clean up after the session
    client = anthropic.Anthropic(
        api_key="Key-here",
    )
    skill_id = get_or_create_skill(client=client, skill_title="calculator", skill_dir="/_skills/calculator")
    chat(client=client, skill_id=skill_id)
    delete_skills(client=client)

if __name__ == "__main__":
    main()