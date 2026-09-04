from typing import Any

from commons.user_service.user_info import UserUpdate
from t8_agent.task.tools.users.base import BaseUserServiceTool
from pydantic_core import ValidationError


class UpdateUserTool(BaseUserServiceTool):

    @property
    def name(self) -> str:
        #TODO: Provide tool name as `update_user`
        return 'update_user'

    @property
    def description(self) -> str:
        #TODO: Provide description of this tool
        return 'update user'

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
                    "description": "user id"
                },
                "new_info": UserUpdate.model_json_schema()
            },
            "required": ["id"],
            "additionalProperties": False
        }

    def execute(self, arguments: dict[str, Any]) -> str:
        #TODO:
        # 1. Get user `id` from `arguments`
        # 2. Get `new_info` from `arguments` and create `UserUpdate` via pydentic `UserUpdate.model_validate`
        # 3. Call user_client update_user and return its results
        # 4. Optional: You can wrap it with `try-except` and return error as string `f"Error while creating a new user: {str(e)}"`
        try:
            id: int = int(arguments["id"])
            user_update = UserUpdate.model_validate(arguments["new_info"])
            result = self._user_client.update_user(user_id=id, user_update_model=user_update)
            return result
        except ValidationError as e :
                    print(f"object could not be validated: {str(e)}")
        except Exception as e:
            print(f"Error while creating a new user: {str(e)}")
