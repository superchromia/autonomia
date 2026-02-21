import json
import logging
import os

from openai import AsyncOpenAI
from pydantic import BaseModel

from context_builder import (
    collect_chat_memories,
    collect_message_context,
    collect_user_memories,
    format_message,
)
from mcp import (
    HTTPCPClient,
    MCPFunctionTool,
    SSEMCPClient,
    StdioMCPClient,
    format_tool_result,
)
from mcp.db_config import load_mcp_servers_from_db
from models.chat import Chat
from models.chat_config import ChatConfig
from models.media import Media
from models.message import Message
from models.messages_enriched import EnrichedMessage
from Tools import ToolExecutionContext, execute_builtin_tool, get_builtin_tools

ai_client = AsyncOpenAI(
    base_url=os.environ.get(
        "NEBIUS_BASE_URL",
        "https://api.tokenfactory.nebius.com/v1/",
    ),
    api_key=os.environ.get("NEBIUS_API_KEY") or os.environ.get("NEBIUS_STUDIO_API_KEY"),
)

logger = logging.getLogger("enrich_messages")

# Default system prompts
DEFAULT_ENRICHMENT_SYSTEM_PROMPT = """
Ты — роботесса в гонкочате с ником @autochromia. Общение идёт на русском языке. 
Твоя задача — определить контекст общения до сообщения и смысл сообщения.

Тебе на вход поступают сообщения из чата в формате: 
message {msg_id}: @{username} ответил на id={reply_to}: {msg_text} 
msg_id нужны для того чтобы ты мог ссылаться на сообщения в чате и связывать цепочки ответов.  

Если сообщение является ответом на другое сообщение, то ты должна в контексте учесть эту нитку диалога.

Ты получаешь на вход сообщения в формате:
'Сообщение {номер}: от {пользователь} на id={номер на который ответ}: "{текст сообщения}"'

Ты должна собрать контекст общения до сообщения и смысл текста сообщения.
Используй номера сообщений только для понимания порядка сообщений. Пользователям они недоступны.
"""

DEFAULT_RESPONSE_SYSTEM_PROMPT = """
Ты — роботесса в гонкочате с ником @autochromia. Общение идёт на русском языке.
Твоя задача — отвечать на сообщения в чате естественно и по делу.

Правила:
- Отвечай только если это уместно и по теме разговора
- Будь дружелюбной и общительной
- Используй эмодзи умеренно
- Если сообщение не требует ответа, верни пустую строку
- Отвечай кратко и по делу
- Учитывай контекст предыдущих сообщений
"""


class UserDescription(BaseModel):
    username: str
    description: str


class EnrichedMessageData(BaseModel):
    context: str
    meaning: str
    # new_user_description: List[UserDescription]


async def _load_mcp_function_tools(session):
    servers = await load_mcp_servers_from_db(session)
    servers = [server for server in servers if server.enabled]
    clients = []
    tools_map: dict[str, tuple[object, MCPFunctionTool]] = {}
    openai_tools = []

    for server in servers:
        client = None
        if server.transport == "sse" and server.url:
            client = SSEMCPClient(server)
        elif server.transport == "http" and server.url:
            client = HTTPCPClient(server)
        elif server.transport == "stdio" and server.command:
            client = StdioMCPClient(server)
        else:
            logger.warning(
                "Skipping MCP server %s due to invalid transport configuration",
                server.name,
            )
            continue

        try:
            await client.connect()
            clients.append(client)
            server_tools = await client.list_tools()
            for tool in server_tools:
                safe_name = f"{server.name}_{tool['name']}".replace("-", "_").replace(".", "_")
                fn = MCPFunctionTool(
                    function_name=f"mcp_{safe_name}"[:64],
                    server_name=server.name,
                    remote_tool_name=tool["name"],
                    description=tool.get("description") or f"MCP tool {tool['name']}",
                    parameters=tool.get("inputSchema") or {"type": "object", "properties": {}},
                )
                tools_map[fn.function_name] = (client, fn)
                openai_tools.append(fn.to_openai_tool())
        except Exception as exc:
            logger.warning(
                "Failed to initialize MCP server %s (%s): %s",
                server.name,
                server.transport,
                exc,
            )
            try:
                await client.close()
            except Exception:
                pass

    return clients, tools_map, openai_tools


def _get_builtin_tools() -> list[dict]:
    return get_builtin_tools()


async def _execute_builtin_tool(
    session,
    chat_id: int,
    function_name: str,
    arguments: dict,
    current_message_id: int | None = None,
    current_sender_id: int | None = None,
    current_chat_type: str | None = None,
) -> str | None:
    context = ToolExecutionContext(
        session=session,
        chat_id=chat_id,
        current_message_id=current_message_id,
        current_sender_id=current_sender_id,
        current_chat_type=current_chat_type,
    )
    return await execute_builtin_tool(context, function_name, arguments)


async def process_message(session, chat_id: int, message_id: int) -> Message:
    # Get chat config for model settings
    from sqlalchemy.future import select

    result = await session.execute(select(ChatConfig).where(ChatConfig.chat_id == chat_id))
    chat_config = result.scalar_one_or_none()

    if not chat_config:
        raise ValueError(f"ChatConfig not found for chat_id={chat_id}")

    if not chat_config.text_model:
        raise ValueError(f"text_model not configured for chat_id={chat_id}")
    if not chat_config.embeddings_model:
        raise ValueError(f"embeddings_model not configured for chat_id={chat_id}")
    if not chat_config.system_prompt:
        raise ValueError(f"system_prompt not configured for chat_id={chat_id}")

    text_model = chat_config.text_model
    embeddings_model = chat_config.embeddings_model
    system_prompt = chat_config.system_prompt

    context = await collect_message_context(session, chat_id=chat_id, message_id=message_id)

    logger.info(f"Collected context for message {message_id} in chat {chat_id}")
    response = await ai_client.chat.completions.create(
        model=text_model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": [{"type": "text", "text": context}]},
        ],
        extra_body={"guided_json": EnrichedMessageData.model_json_schema()},
    )
    response = response.choices[0].message.content
    logger.info(f"Collected response for message {message_id} in chat {chat_id}")
    data = json.loads(response)

    embeddings_data = await ai_client.embeddings.create(
        model=embeddings_model,
        input="""
        КОНТЕКСТ 
        {context}

        СМЫСЛ 
        {meaning}
        """.format(
            context=data["context"], meaning=data["meaning"]
        ),
    )
    logger.info(f"Collected embeddings for message {message_id} in chat {chat_id}")
    embeddings = embeddings_data.data[0].embedding

    # Check if enriched message already exists
    result = await session.execute(select(EnrichedMessage).where(EnrichedMessage.chat_id == chat_id, EnrichedMessage.message_id == message_id))
    existing_enriched_message = result.scalar_one_or_none()

    if existing_enriched_message:
        # Update existing enriched message
        existing_enriched_message.context = data["context"]
        existing_enriched_message.meaning = data["meaning"]
        existing_enriched_message.embeddings = embeddings
        logger.info(f"Updated existing enriched message: {chat_id}:{message_id}")
    else:
        # Create new enriched message
        db_enriched_message = EnrichedMessage(
            chat_id=chat_id,
            message_id=message_id,
            context=data["context"],
            meaning=data["meaning"],
            embeddings=embeddings,
        )
        session.add(db_enriched_message)
        logger.info(f"Created new enriched message: {chat_id}:{message_id}")
    await session.commit()


def _normalize_generation_settings(chat_config: ChatConfig) -> dict:
    max_tokens = int(chat_config.response_max_tokens or 450)
    max_tokens = max(1, max_tokens)

    temperature = float(chat_config.response_temperature or 0.85)
    temperature = max(0.0, min(2.0, temperature))

    presence_penalty = float(chat_config.response_presence_penalty or 0.2)
    presence_penalty = max(0.0, presence_penalty)

    frequency_penalty = float(chat_config.response_frequency_penalty or 0.2)
    frequency_penalty = max(0.0, frequency_penalty)

    return {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
    }


async def _load_response_settings(session, chat_id: int) -> tuple[str, str, dict]:
    from sqlalchemy.future import select

    result = await session.execute(select(ChatConfig).where(ChatConfig.chat_id == chat_id))
    chat_config = result.scalar_one_or_none()

    if not chat_config:
        raise ValueError(f"ChatConfig not found for chat_id={chat_id}")
    if not chat_config.text_model:
        raise ValueError(f"text_model not configured for chat_id={chat_id}")
    if not chat_config.system_prompt:
        raise ValueError(f"system_prompt not configured for chat_id={chat_id}")
    generation_settings = _normalize_generation_settings(chat_config)
    return chat_config.text_model, chat_config.system_prompt, generation_settings


async def _load_message_metadata(session, chat_id: int, message_id: int) -> tuple[int | None, str | None]:
    from sqlalchemy.future import select

    current_message_result = await session.execute(
        select(Message).where(
            Message.chat_id == chat_id,
            Message.message_id == message_id,
        )
    )
    current_message = current_message_result.scalar_one_or_none()
    current_sender_id = current_message.sender_id if current_message else None

    chat_result = await session.execute(select(Chat).where(Chat.id == chat_id))
    chat = chat_result.scalar_one_or_none()
    current_chat_type = chat.chat_type if chat else None
    return current_sender_id, current_chat_type


async def _load_photo_description(session, chat_id: int, message_id: int) -> str | None:
    from sqlalchemy.future import select

    result = await session.execute(
        select(Media).where(
            Media.chat_id == chat_id,
            Media.message_id == message_id,
            Media.media_type == "photo",
        )
    )
    media = result.scalar_one_or_none()
    if media and media.text_description:
        return media.text_description
    return None


def _build_context_with_photo(context: str, photo_description: str | None) -> str:
    if not photo_description:
        return context
    return f"{context}\n\nОПИСАНИЕ ФОТОГРАФИИ В СООБЩЕНИИ:\n{photo_description}"


def _build_generation_messages(system_prompt: str, context_with_photo: str, has_tools: bool) -> list[dict]:
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "system",
            "content": (
                "Отвечай только обычным текстом, без JSON, без разметки структур, "
                "без служебных полей. "
                "Не опирайся на память из текста контекста: "
                "память нужно получать только через tools. "
                "Если пользователь просит запомнить информацию, "
                "передает правило, или сообщает устойчивое предпочтение, "
                "сохрани это через tool save_memory с memory_scope='both'. "
                "Если отвечать не нужно, верни пустую строку."
            ),
        },
    ]
    if has_tools:
        messages.append(
            {
                "role": "system",
                "content": ("Перед ответом используй tools для памяти и фактов. " "Для памяти вызывай get_chat_memories и get_user_memories."),
            }
        )
    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": context_with_photo,
                }
            ],
        }
    )
    return messages


async def generate_bot_response(session, chat_id: int, message_id: int) -> str | None:
    """
    Generate a bot response to a message in a chat.
    Returns the response text or None if the bot should not respond.
    """
    text_model, system_prompt, generation_settings = await _load_response_settings(
        session,
        chat_id,
    )
    context = await collect_message_context(
        session,
        chat_id=chat_id,
        message_id=message_id,
    )
    current_sender_id, current_chat_type = await _load_message_metadata(
        session,
        chat_id=chat_id,
        message_id=message_id,
    )
    photo_description = await _load_photo_description(
        session,
        chat_id=chat_id,
        message_id=message_id,
    )
    context_with_photo = _build_context_with_photo(context, photo_description)

    logger.info(f"Generating bot response for message {message_id} in chat {chat_id}")

    mcp_clients = []
    try:
        from config import config

        tools_map: dict[str, tuple[object, MCPFunctionTool]] = {}
        mcp_openai_tools = []
        builtin_tools = _get_builtin_tools()
        if config.mcp_enabled:
            try:
                mcp_clients, tools_map, mcp_openai_tools = await _load_mcp_function_tools(session)
                if mcp_openai_tools:
                    logger.info(
                        "Loaded %s MCP tools for generation",
                        len(mcp_openai_tools),
                    )
            except Exception as exc:
                logger.warning("Failed to initialize MCP tools: %s", exc)

        all_tools = builtin_tools + mcp_openai_tools
        messages = _build_generation_messages(
            system_prompt=system_prompt,
            context_with_photo=context_with_photo,
            has_tools=bool(all_tools),
        )
        response_text = None
        max_tool_iterations = 8
        for attempt in range(1, 6):
            tool_iteration = 0
            while True:
                logger.info(f"Tool iteration: {tool_iteration}")
                tool_iteration += 1
                if tool_iteration > max_tool_iterations:
                    logger.warning(
                        "Reached MCP tool iteration limit for message %s in chat %s " "(attempt %s/5).",
                        message_id,
                        chat_id,
                        attempt,
                    )
                    break

                try:
                    completion_kwargs = {
                        "model": text_model,
                        "messages": messages,
                        "max_tokens": generation_settings["max_tokens"],
                        "temperature": generation_settings["temperature"],
                        "presence_penalty": generation_settings["presence_penalty"],
                        "frequency_penalty": generation_settings["frequency_penalty"],
                    }
                    if all_tools:
                        completion_kwargs["tools"] = all_tools
                        completion_kwargs["tool_choice"] = "auto"
                    logger.info(f"Completion kwargs: {completion_kwargs}")
                    response = await ai_client.chat.completions.create(**completion_kwargs)
                    logger.info(f"Response: {response}")
                except Exception as exc:
                    if mcp_openai_tools:
                        logger.warning(
                            "MCP request failed for message %s in chat %s; " "retrying without MCP. Error: %s",
                            message_id,
                            chat_id,
                            exc,
                        )
                        mcp_openai_tools = []
                        all_tools = builtin_tools
                        break
                    raise

                content = None
                tool_calls = None
                if response.choices and response.choices[0].message:
                    content = response.choices[0].message.content
                    tool_calls = response.choices[0].message.tool_calls

                if tool_calls:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": content or "",
                            "tool_calls": [
                                {
                                    "id": call.id,
                                    "type": call.type,
                                    "function": {
                                        "name": call.function.name,
                                        "arguments": call.function.arguments,
                                    },
                                }
                                for call in tool_calls
                            ],
                        }
                    )

                    for call in tool_calls:
                        function_name = call.function.name
                        try:
                            arguments = json.loads(call.function.arguments or "{}")
                        except json.JSONDecodeError:
                            arguments = {}

                        builtin_result = await _execute_builtin_tool(
                            session=session,
                            chat_id=chat_id,
                            function_name=function_name,
                            arguments=arguments,
                            current_message_id=message_id,
                            current_sender_id=current_sender_id,
                            current_chat_type=current_chat_type,
                        )
                        if builtin_result is not None:
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": call.id,
                                    "name": function_name,
                                    "content": builtin_result,
                                }
                            )
                            continue

                        if function_name not in tools_map:
                            logger.warning(
                                "Unknown tool call %s for message %s in chat %s",
                                function_name,
                                message_id,
                                chat_id,
                            )
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": call.id,
                                    "name": function_name,
                                    "content": "Tool is not available",
                                }
                            )
                            continue

                        client, tool_meta = tools_map[function_name]
                        tool_result = await client.call_tool(tool_meta.remote_tool_name, arguments)
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call.id,
                                "name": function_name,
                                "content": format_tool_result(tool_result),
                            }
                        )
                    continue

                if not content:
                    logger.warning(
                        "Empty model content for message %s in chat %s (attempt %s/5), retrying...",
                        message_id,
                        chat_id,
                        attempt,
                    )
                    break

                logger.info(f"Content: {content}")
                response_text = content
                if response_text:
                    break

                logger.warning(
                    "Empty response field for message %s in chat %s (attempt %s/5), retrying...",
                    message_id,
                    chat_id,
                    attempt,
                )
                break

            if response_text:
                break

        if not response_text:
            logger.debug(f"Bot decided not to respond to message {message_id} in chat {chat_id}")
            return None

        logger.info(f"Generated bot response for message {message_id} in chat {chat_id}: {response_text[:50]}...")
        return response_text
    except Exception as e:
        logger.exception(f"Failed to generate bot response: {e}")
        return None
    finally:
        for client in mcp_clients:
            try:
                await client.close()
            except Exception:
                pass
