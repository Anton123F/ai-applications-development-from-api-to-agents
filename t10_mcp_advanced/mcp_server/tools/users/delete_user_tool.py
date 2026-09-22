from typing import Any

from t10_mcp_advanced.mcp_server.tools.users.base import BaseUserServiceTool


class DeleteUserTool(BaseUserServiceTool):

    @property
    def name(self) -> str:
        #TODO: Provide tool name as `delete_users`
        return "delete_users"

    @property
    def description(self) -> str:
        #TODO: Provide description of this tool
        return "delete user"

    @property
    def input_schema(self) -> dict[str, Any]:
        #TODO:
        # Provide tool params Schema. This tool applies user `id` (number) as a parameter and it is required
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "number",
                    "description": "user id"
                }
            },
            "required": ["id"],
            "additionalProperties": False
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        #TODO:
        # 1. Get int `id` from arguments
        # 2. Call user_client delete_user and return its results (it is async, don't forget to await)
        id = int(arguments.get("id"))
        return await self._user_client.delete_user(id)