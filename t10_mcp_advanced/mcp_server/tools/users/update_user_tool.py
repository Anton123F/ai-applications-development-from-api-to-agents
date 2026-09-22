from typing import Any

from commons.user_service.user_info import UserUpdate
from t10_mcp_advanced.mcp_server.tools.users.base import BaseUserServiceTool


class UpdateUserTool(BaseUserServiceTool):

    @property
    def name(self) -> str:
        #TODO: Provide tool name as `update_user`
        return "update_user"

    @property
    def description(self) -> str:
        #TODO: Provide description of this tool
        return "update user"

    @property
    def input_schema(self) -> dict[str, Any]:
        #TODO:
        # Provide tool params Schema:
        # - id: number, required, User ID that should be updated.
        # - new_info: UserUpdate.model_json_schema()
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "number",
                    "description": "user id that should be updated"
                },
                "new_info": UserUpdate.model_json_schema()
            },
            "required": ["id"],
            "additionalProperties": False
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        #TODO:
        # 1. Get user `id` from `arguments`
        # 2. Get `new_info` from `arguments` and create `UserUpdate` via pydentic `UserUpdate.model_validate`
        # 3. Call user_client update_user and return its results (it is async, don't forget to await)
        id = int(arguments.get("id"))
        new_info = UserUpdate.model_validate(arguments.get("new_info"))
        return await self._user_client.update_user(id, new_info)
        
