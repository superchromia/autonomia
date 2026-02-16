from Tools.get_current_time_tool import (
    NAME as GET_CURRENT_TIME_NAME,
    OPENAI_TOOL as GET_CURRENT_TIME_TOOL,
    execute as execute_get_current_time,
)
from Tools.get_message_content_by_number_tool import (
    NAME as GET_MESSAGE_CONTENT_NAME,
    OPENAI_TOOL as GET_MESSAGE_CONTENT_TOOL,
    execute as execute_get_message_content,
)
from Tools.get_user_information_by_id_tool import (
    NAME as GET_USER_INFO_NAME,
    OPENAI_TOOL as GET_USER_INFO_TOOL,
    execute as execute_get_user_info,
)
from Tools.memory_tools import (
    GET_CHAT_MEMORIES_NAME,
    GET_CHAT_MEMORIES_TOOL,
    GET_USER_MEMORIES_NAME,
    GET_USER_MEMORIES_TOOL,
    SAVE_MEMORY_NAME,
    SAVE_MEMORY_TOOL,
    get_chat_memories,
    get_user_memories,
    save_memory,
)

BUILTIN_TOOLS = [
    GET_USER_INFO_TOOL,
    GET_CURRENT_TIME_TOOL,
    GET_MESSAGE_CONTENT_TOOL,
    SAVE_MEMORY_TOOL,
    GET_USER_MEMORIES_TOOL,
    GET_CHAT_MEMORIES_TOOL,
]

_EXECUTORS = {
    GET_USER_INFO_NAME: execute_get_user_info,
    GET_CURRENT_TIME_NAME: execute_get_current_time,
    GET_MESSAGE_CONTENT_NAME: execute_get_message_content,
    SAVE_MEMORY_NAME: save_memory,
    GET_USER_MEMORIES_NAME: get_user_memories,
    GET_CHAT_MEMORIES_NAME: get_chat_memories,
}


def get_builtin_tools() -> list[dict]:
    return BUILTIN_TOOLS


async def execute_builtin_tool(context, function_name: str, arguments: dict) -> str | None:
    handler = _EXECUTORS.get(function_name)
    if not handler:
        return None
    return await handler(context, arguments)
