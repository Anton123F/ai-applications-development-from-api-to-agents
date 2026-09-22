from typing import Any

from t10_mcp_advanced.mcp_server.tools.users.base import BaseUserServiceTool


class SearchUsersTool(BaseUserServiceTool):

    @property
    def name(self) -> str:
        #TODO: Provide tool name as `search_users`
        return "search_users"

    @property
    def description(self) -> str:
        #TODO: Provide description of this tool
        return "search user"

    @property
    def input_schema(self) -> dict[str, Any]:
        #TODO:
        # Provide tool params Schema:
        # - name: str
        # - surname: str
        # - email: str
        # - gender: str
        # None of them are required (see UserClient.search_users method)
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "user name"
                },
                "surname": {
                    "type": "string",
                    "description": 'user surname'
                },
                "email": {
                    "type": "string",
                    "description": 'user email'
                },
                "gender": {
                    "type": "string",
                    "description": 'user gender'
                }
            },
            "required": [],
            "additionalProperties": False
        }
        

    async def execute(self, arguments: dict[str, Any]) -> str:
        #TODO:
        # Call user_client search_users (with `**arguments`) and return its results (it is async, don't forget to await)
        return self._user_client.search_users(**arguments)