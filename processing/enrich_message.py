import json
import logging
import os
from datetime import UTC, datetime

from openai import AsyncOpenAI
from pydantic import BaseModel

from mcp import MCPFunctionTool, SSEMCPClient, format_tool_result
from models.chat_config import ChatConfig
from models.media import Media
from models import Memory
from models.message import Message
from models.messages_enriched import EnrichedMessage
from models.user import User

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


class BotResponseData(BaseModel):
    response: str
    context: str
    think: str


async def _load_mcp_function_tools():
    from config import config

    servers = [server for server in config.get_mcp_servers() if server.enabled and server.transport == "sse" and server.url]
    clients = []
    tools_map: dict[str, tuple[SSEMCPClient, MCPFunctionTool]] = {}
    openai_tools = []

    for server in servers:
        client = SSEMCPClient(server)
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

    return clients, tools_map, openai_tools


def _get_builtin_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_user_information_by_id",
                "description": "Get user profile details by Telegram user id. ALways use this function to check user info. Always check user info before responding to a message.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "integer",
                            "description": "Telegram user id",
                        }
                    },
                    "required": ["user_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "Get current UTC time in ISO format.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_message_content_by_number",
                "description": "Get message content by its message number (message_id) in current chat.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message_number": {
                            "type": "integer",
                            "description": "Message id/number in current chat",
                        }
                    },
                    "required": ["message_number"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "save_memory",
                "description": (
                    "Save an important long-term memory for this chat. "
                    "Use for facts, rules, and user preferences."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "memory_text": {
                            "type": "string",
                            "description": "Fact/rule/preference to remember",
                        },
                        "memory_type": {
                            "type": "string",
                            "description": "fact, rule, or preference",
                        },
                        "importance": {
                            "type": "integer",
                            "description": "Importance from 1 to 10",
                        },
                        "source_message_id": {
                            "type": "integer",
                            "description": "Message id where memory came from",
                        },
                    },
                    "required": ["memory_text"],
                },
            },
        },
    ]


async def _execute_builtin_tool(session, chat_id: int, function_name: str, arguments: dict) -> str | None:
    from sqlalchemy.future import select

    if function_name == "get_current_time":
        return datetime.now(UTC).isoformat()

    if function_name == "get_user_information_by_id":
        user_id = arguments.get("user_id")
        if user_id is None:
            return "Missing required argument: user_id"

        try:
            from telethon.tl.functions.users import GetFullUserRequest

            from dependency import dependency

            telethon_user = await dependency.telegram_client.get_entity(int(user_id))
            full = await dependency.telegram_client(GetFullUserRequest(id=telethon_user))
        except Exception as exc:
            return f"Failed to fetch full user {user_id} via Telethon: {exc}"

        if hasattr(full, "to_dict"):
            raw_full = full.to_dict()
        elif hasattr(full, "__dict__"):
            raw_full = full.__dict__
        else:
            raw_full = {"value": str(full)}
        result = json.dumps(raw_full, ensure_ascii=False, default=str)
        logger.info(f"Tool get_user_information_by_id result: {result}")
        return result

    if function_name == "save_memory":
        memory_text = (arguments.get("memory_text") or "").strip()
        if not memory_text:
            return "Missing required argument: memory_text"

        memory_type = (arguments.get("memory_type") or "fact").strip().lower()
        if memory_type not in {"fact", "rule", "preference"}:
            memory_type = "fact"

        importance = arguments.get("importance", 7)
        try:
            importance = int(importance)
        except (TypeError, ValueError):
            importance = 7
        importance = max(1, min(10, importance))

        source_message_id = arguments.get("source_message_id")
        if source_message_id is not None:
            try:
                source_message_id = int(source_message_id)
            except (TypeError, ValueError):
                source_message_id = None

        existing_result = await session.execute(
            select(Memory).where(
                Memory.chat_id == chat_id,
                Memory.memory_text == memory_text,
                Memory.is_active.is_(True),
            )
        )
        existing_memory = existing_result.scalar_one_or_none()

        if existing_memory:
            existing_memory.memory_type = memory_type
            existing_memory.importance = max(existing_memory.importance, importance)
            if source_message_id is not None:
                existing_memory.source_message_id = source_message_id
            await session.commit()
            return json.dumps(
                {
                    "status": "updated",
                    "memory_id": existing_memory.id,
                    "memory_text": existing_memory.memory_text,
                },
                ensure_ascii=False,
            )

        memory = Memory(
            chat_id=chat_id,
            source_message_id=source_message_id,
            memory_text=memory_text,
            memory_type=memory_type,
            importance=importance,
            is_active=True,
        )
        session.add(memory)
        await session.commit()
        return json.dumps(
            {
                "status": "saved",
                "memory_id": memory.id,
                "memory_text": memory.memory_text,
            },
            ensure_ascii=False,
        )

    if function_name == "get_message_content_by_number":
        message_number = arguments.get("message_number")
        if message_number is None:
            return "Missing required argument: message_number"
        result = await session.execute(
            select(Message).where(
                Message.chat_id == chat_id,
                Message.message_id == int(message_number),
            )
        )
        msg = result.scalar_one_or_none()
        if not msg:
            return f"Message {message_number} not found in chat {chat_id}"

        text = None
        if isinstance(msg.raw_data, dict):
            text = msg.raw_data.get("message")
        return json.dumps(
            {
                "message_id": msg.message_id,
                "chat_id": msg.chat_id,
                "sender_id": msg.sender_id,
                "date": msg.date.isoformat() if msg.date else None,
                "text": text,
                "message_type": msg.message_type,
            },
            ensure_ascii=False,
        )

    return None


async def collect_chat_memories(session, chat_id: int, limit: int = 20) -> str:
    from sqlalchemy.future import select

    result = await session.execute(
        select(Memory)
        .where(Memory.chat_id == chat_id, Memory.is_active.is_(True))
        .order_by(Memory.importance.desc(), Memory.updated_at.desc())
        .limit(limit)
    )
    memories = result.scalars().all()
    if not memories:
        return ""

    lines = []
    for memory in memories:
        lines.append(
            f"- [{memory.memory_type}|{memory.importance}/10] {memory.memory_text}"
        )
    return "\n".join(lines)


def format_message(raw_data, username):
    """
    Formats a message from raw_data dict as:
    "@username написал id=123: "Сообщение 1"
    "@username ответил  id=124 "Сообщение 2" на id=123"
    """
    msg_id = raw_data.get("id")
    msg_text = raw_data.get("message", "")

    reply_to = None
    if "reply_to" in raw_data and isinstance(raw_data["reply_to"], dict):
        reply_to = raw_data["reply_to"].get("reply_to_msg_id")

    if reply_to:
        return f'Сообщение {msg_id}: от user_id={username} на id={reply_to}: "{msg_text}"'
    else:
        return f'Сообщение {msg_id}: от user_id={username}: "{msg_text}"'


async def collect_message_context(session, chat_id: int, message_id: int) -> str:
    from sqlalchemy.future import select

    # Get current message
    result = await session.execute(select(Message).where(Message.chat_id == chat_id, Message.message_id == message_id))
    message = result.scalar_one_or_none()
    if not message:
        return "Message not found"

    # Get previous messages
    result = await session.execute(
        select(Message).where(Message.chat_id == chat_id, Message.message_id < message_id).order_by(Message.message_id.desc()).limit(50)
    )
    previous_messages = result.scalars().all()

    # Get usernames
    result = await session.execute(select(User))
    users = result.scalars().all()
    usernames = {}
    for user in users:
        username = user.username or f"{user.first_name} {user.last_name}".strip()
        usernames[user.id] = username

    previous_messages_formatted = "\n".join(format_message(msg.raw_data, msg.sender_id) for msg in previous_messages)
    memory_context = await collect_chat_memories(session, chat_id=chat_id)

    return f"""
    ПАМЯТЬ О ЧАТЕ:
    {memory_context if memory_context else "(пока пусто)"}

    ПРЕДЫДУЩИЕ СООБЩЕНИЯ:
    {previous_messages_formatted}

    ТЕКУЩЕЕ СООБЩЕНИЕ:
    {format_message(message.raw_data, message.sender_id)}
    """


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


async def generate_bot_response(session, chat_id: int, message_id: int) -> str | None:
    """
    Generate a bot response to a message in a chat.
    Returns the response text or None if the bot should not respond.
    """
    # Get chat config for model settings
    from sqlalchemy.future import select

    result = await session.execute(select(ChatConfig).where(ChatConfig.chat_id == chat_id))
    chat_config = result.scalar_one_or_none()

    if not chat_config:
        raise ValueError(f"ChatConfig not found for chat_id={chat_id}")

    if not chat_config.text_model:
        raise ValueError(f"text_model not configured for chat_id={chat_id}")
    if not chat_config.system_prompt:
        raise ValueError(f"system_prompt not configured for chat_id={chat_id}")

    text_model = chat_config.text_model
    system_prompt = chat_config.system_prompt

    context = await collect_message_context(session, chat_id=chat_id, message_id=message_id)

    # Get photo description if available
    photo_description = None
    result = await session.execute(select(Media).where(Media.chat_id == chat_id, Media.message_id == message_id, Media.media_type == "photo"))
    media = result.scalar_one_or_none()
    if media and media.text_description:
        photo_description = media.text_description

    # Add photo description to context if available
    if photo_description:
        context_with_photo = f"{context}\n\nОПИСАНИЕ ФОТОГРАФИИ В СООБЩЕНИИ:\n{photo_description}"
    else:
        context_with_photo = context

    logger.info(f"Generating bot response for message {message_id} in chat {chat_id}")

    mcp_clients = []
    try:
        from config import config

        tools_map: dict[str, tuple[SSEMCPClient, MCPFunctionTool]] = {}
        mcp_openai_tools = []
        builtin_tools = _get_builtin_tools()
        if config.mcp_enabled:
            try:
                mcp_clients, tools_map, mcp_openai_tools = await _load_mcp_function_tools()
                if mcp_openai_tools:
                    logger.info(
                        "Loaded %s MCP tools for generation",
                        len(mcp_openai_tools),
                    )
            except Exception as exc:
                logger.warning("Failed to initialize MCP tools: %s", exc)

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "system",
                "content": (
                    "Верни строго JSON с полями: "
                    "response (строка ответа пользователю), "
                    "context (краткая сводка контекста), "
                    "think (краткое рассуждение, почему такой ответ). "
                    "Если пользователь просит запомнить информацию, "
                    "передает правило, или сообщает устойчивое предпочтение, "
                    "сохрани это через tool save_memory. "
                ),
            },
        ]
        all_tools = builtin_tools + mcp_openai_tools
        if all_tools:
            messages.append(
                {
                    "role": "system",
                    "content": ("При необходимости используй подключенные MCP серверы " "для получения фактов перед ответом."),
                }
            )

        messages.extend(
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": context_with_photo,
                        }
                    ],
                }
            ]
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
                        "max_tokens": 450,
                        "temperature": 0.85,
                        "presence_penalty": 0.2,
                        "frequency_penalty": 0.2,
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "bot_response_payload",
                                "schema": BotResponseData.model_json_schema(),
                                "strict": True,
                            },
                        },
                    }
                    if all_tools:
                        completion_kwargs["tools"] = all_tools
                        completion_kwargs["tool_choice"] = "auto"

                    response = await ai_client.chat.completions.create(**completion_kwargs)
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
                try:
                    payload = json.loads(content) if isinstance(content, str) else content
                    logger.info(f"Payload: {payload}")
                    structured = BotResponseData.model_validate(payload)
                except Exception:
                    logger.warning("Invalid JSON payload for message %s in chat %s (attempt %s/5), retrying.. (%s) ", message_id, chat_id, attempt, content)
                    break

                logger.info(
                    "Model reasoning for message %s in chat %s: context=%s | think=%s",
                    message_id,
                    chat_id,
                    structured.context[:300],
                    structured.think[:300],
                )

                response_text = structured.response.strip()
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
