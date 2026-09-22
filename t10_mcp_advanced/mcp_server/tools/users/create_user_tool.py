from typing import Any

from commons.user_service.user_info import UserCreate
from t10_mcp_advanced.mcp_server.tools.users.base import BaseUserServiceTool


class CreateUserTool(BaseUserServiceTool):

    @property
    def name(self) -> str:
        #TODO: Provide tool name as `add_user`
        return "add_user"

    @property
    def description(self) -> str:
        #TODO: Provide description of this tool
        return "create a new user"

    @property
    def input_schema(self) -> dict[str, Any]:
        #TODO: Provide tool params Schema. To do that you can create json schema from UserCreate pydentic model ` UserCreate.model_json_schema()`
        return UserCreate.model_json_schema()

    async def execute(self, arguments: dict[str, Any]) -> str:
        #TODO:
        # 1. Validate arguments with `UserCreate.model_validate`
        # 2. Call user_client add user and return its results (it is async, don't forget to await)
        user_data = UserCreate.model_validate(arguments)
        if user_data:
            return await self._user_client.add_user(user_data)