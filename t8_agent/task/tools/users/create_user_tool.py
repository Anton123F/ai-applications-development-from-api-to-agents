from typing import Any

from commons.user_service.user_info import UserCreate
from t8_agent.task.tools.users.base import BaseUserServiceTool

from pydantic_core import ValidationError


class CreateUserTool(BaseUserServiceTool):

    @property
    def name(self) -> str:
        #TODO: Provide tool name as `add_user`
        return 'add_user'

    @property
    def description(self) -> str:
        #TODO: Provide description of this tool
        return 'add a new user'

    @property
    def input_schema(self) -> dict[str, Any]:
        #TODO: Provide tool params Schema. To do that you can create json schema from UserCreate pydentic model ` UserCreate.model_json_schema()`
        return UserCreate.model_json_schema()

    def execute(self, arguments: dict[str, Any]) -> str:
        #TODO:
        # 1. Validate arguments with `UserCreate.model_validate`
        # 2. Call user_client add user and return its results
        # 3. Optional: You can wrap it with `try-except` and return error as string `f"Error while creating a new user: {str(e)}"`
        try:
            validated_user = UserCreate.model_validate(arguments)
            result = self._user_client.add_user(validated_user)
            return result
        except ValidationError as e :
            print(f"object could not be validated: {str(e)}")
        except Exception as e:
            print(f"Error while creating a new user: {str(e)}")