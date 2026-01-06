import json
import logging
import os

from openai import AsyncOpenAI
from pydantic import BaseModel

from models.chat_config import ChatConfig
from models.media import Media
from models.message import Message
from models.messages_enriched import EnrichedMessage
from models.user import User

ai_client = AsyncOpenAI(
    base_url="https://api.studio.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_STUDIO_API_KEY"),
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
        return f'Сообщение {msg_id}: от {username} на id={reply_to}: "{msg_text}"'
    else:
        return f'Сообщение {msg_id}: от {username}: "{msg_text}"'


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

    previous_messages_formatted = "\n".join(format_message(msg.raw_data, usernames.get(msg.sender_id, "Unknown")) for msg in previous_messages)

    return f"""
    ПРЕДЫДУЩИЕ СООБЩЕНИЯ:
    {previous_messages_formatted}

    ТЕКУЩЕЕ СООБЩЕНИЕ:
    {format_message(message.raw_data, usernames.get(message.sender_id, "Unknown"))}
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
    result = await session.execute(select(EnrichedMessage).where(EnrichedMessage.chat_id == chat_id, 
                                                                 EnrichedMessage.message_id == message_id))
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
    result = await session.execute(select(Media).where(Media.chat_id == chat_id, 
                                                       Media.message_id == message_id, Media.media_type == "photo"))
    media = result.scalar_one_or_none()
    if media and media.text_description:
        photo_description = media.text_description

    # Add photo description to context if available
    if photo_description:
        context_with_photo = f"{context}\n\nОПИСАНИЕ ФОТОГРАФИИ В СООБЩЕНИИ:\n{photo_description}"
    else:
        context_with_photo = context

    logger.info(f"Generating bot response for message {message_id} in chat {chat_id}")

    try:
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": context_with_photo,
                    }
                ],
            },
        ]
        print(context_with_photo)
        response = await ai_client.chat.completions.create(
            model=text_model,
            messages=messages,
            max_tokens=450,
            temperature=0.85,
            presence_penalty=0.2,
            frequency_penalty=0.2,
        )
        response_text = response.choices[0].message.content.strip()

        # Return None if response is empty or just whitespace
        if not response_text:
            logger.debug(f"Bot decided not to respond to message {message_id} in chat {chat_id}")
            return None

        logger.info(f"Generated bot response for message {message_id} in chat {chat_id}: {response_text[:50]}...")
        return response_text
    except Exception as e:
        logger.exception(f"Failed to generate bot response: {e}")
        return None
