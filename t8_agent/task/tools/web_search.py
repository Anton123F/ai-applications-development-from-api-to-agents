from typing import Any

import requests

from commons.constants import OPENAI_RESPONSES_ENDPOINT
from t8_agent.task.tools.base import BaseTool


class WebSearchTool(BaseTool):

    def __init__(self, open_ai_api_key: str):
        self.__api_key = open_ai_api_key
        self.__endpoint = OPENAI_RESPONSES_ENDPOINT

    @property
    def name(self) -> str:
        #TODO: Provide tool name as `web_search_tool`
        return 'web_search_tool'

    @property
    def description(self) -> str:
        #TODO: Provide description of this tool
        return 'allow to perform a wev serach for additional info'

    @property
    def input_schema(self) -> dict[str, Any]:
        #TODO: Provide tool params Schema (it applies `request` string to search by)
        return {
            "type": "object",
            "properties": {
                "request": {
                    "type": "string",
                    "description": "The search query or request string."
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of search results to return.",
                    "default": 3
                }
            },
            "required": ["request"],
            "additionalProperties": False
        }

    def execute(self, arguments: dict[str, Any]) -> str:
        #TODO:
        # https://developers.openai.com/api/docs/guides/tools-web-search
        # 1. Make POST call to `gpt-5.2` with request "tools": [{"type": "web_search"}],
        # 4. Check if response status is 200 and if yes then return message content, otherwise return `f"Error: {response.status_code} {response.text}"`
        import requests

        url = self.__endpoint
        headers = {
            "Content-Type": "application/json",
            "api-key": self.__api_key
        }
        data = {
            "model": "gpt-5.2-2025-12-11",
            "tools": [{"type": "web_search"}],
            "input": arguments["request"]
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code != 200:
            return f"Error: {response.status_code} {response.text}"

        response_json = response.json()

        if "output" in response_json:
            for block in response_json["output"]:
                if block.get("type") == "output_text":
                    return block.get("text")
            else:
                print("No output blocks found in response.")