import json
import logging
import os
from typing import List, Literal

from openai import AsyncOpenAI
from pydantic import BaseModel

from models.message import Message
from models.messages_enriched import EnrichedMessage
from models.user import User

ai_client = AsyncOpenAI(
    base_url="https://api.studio.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_STUDIO_API_KEY"),
)

logger = logging.getLogger("enrich_messages")


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
    context = await collect_message_context(session, chat_id=chat_id, message_id=message_id)
    logger.info(f"Collected context for message {message_id} in chat {chat_id}")
    response = await ai_client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3",
        messages=[
            {
                "role": "system",
                "content": """
                Ты — роботесса в гонкочате с ником @autochromia. Общение идёт на русском языке. 
                Твоя задача — определить контекст общения до сообщения и смысл сообщения.

                Тебе на вход поступают сообщения из чата в формате: 
                message {msg_id}: @{username} ответил на id={reply_to}: {msg_text} 
                msg_id нужны для того чтобы ты мог ссылаться на сообщения в чате и связывать цепочки ответов.  

                Если сообщение является ответом на другое сообщение, то ты должна в контексте учесть эту нитку диалога.

                Ты получаешь на вход сообщения в формате:
                'Сообщение {номер}: от {пользователь} на id={номер на который ответ}: "{текст сообщения}"'

                Ты должна собрать контекст общения до сообщения и смысл текста сообщения.
                Используй номера сообщений только для понимания порядка сообщений. Пользователей они недоступны
                """,
            },
            {"role": "user", "content": [{"type": "text", "text": context}]},
        ],
        extra_body={"guided_json": EnrichedMessageData.model_json_schema()},
    )
    response = response.choices[0].message.content
    logger.info(f"Collected response for message {message_id} in chat {chat_id}")
    data = json.loads(response)

    embeddings_data = await ai_client.embeddings.create(
        model="Qwen/Qwen3-Embedding-8B",
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

    # Save enriched message
    db_enriched_message = EnrichedMessage(
        chat_id=chat_id,
        message_id=message_id,
        context=data["context"],
        meaning=data["meaning"],
        embeddings=embeddings,
    )
    session.add(db_enriched_message)
    await session.commit()
