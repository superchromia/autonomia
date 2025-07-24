import json
import os

from openai import AsyncOpenAI

from dependency import dependency
from repositories.chat_repository import Chat, ChatRepository
from repositories.enriched_message_repository import EnrichedMessageRepository
from repositories.message_repository import Message, MessageRepository
from repositories.user_repository import User, UserRepository

ai_client = AsyncOpenAI(
    base_url="https://api.studio.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_STUDIO_API_KEY"),
)

from typing import List, Literal

from pydantic import BaseModel


class UserDescription(BaseModel):
    username: str
    description: str


class EnrichedMessage(BaseModel):
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


async def collect_message_context(message_repo: MessageRepository, user_repo: UserRepository, chat_id: int, message_id: int) -> list[Message]:
    message = await message_repo.get_message(message_id, chat_id)
    thread_messages = await message_repo.get_messages_thread(chat_id, message_id)
    previous_messages = await message_repo.get_previous_n_messages(chat_id, message_id, 50)
    usernames = await user_repo.get_usernames()

    thread_messages_formatted = "\n".join(format_message(msg.raw_data, usernames.get(msg.sender_id)) for msg in thread_messages)
    previous_messages_formatted = "\n".join(format_message(msg.raw_data, usernames.get(msg.sender_id)) for msg in previous_messages)

    return f"""
    ПРЕДЫДУЩИЕ СООБЩЕНИЯ:
    {previous_messages_formatted}

    ВЕТКА СООБЩЕНИЙ ДО ТЕКУЩЕГО:
    {thread_messages_formatted}

    ТЕКУЩЕЕ СООБЩЕНИЕ:
    {format_message(message.raw_data, usernames.get(message.sender_id))}
    """


async def process_message(session, chat_id: int, message_id: int) -> Message:
    message_repo = MessageRepository(session)
    chat_repo = ChatRepository(session)
    user_repo = UserRepository(session)
    enriched_message_repo = EnrichedMessageRepository(session)

    context = await collect_message_context(message_repo, user_repo, chat_id=chat_id, message_id=message_id)

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
        extra_body={"guided_json": EnrichedMessage.model_json_schema()},
    )
    response = response.choices[0].message.content
    data = json.loads(response)

    embeddings_data = await ai_client.embeddings.create(
        model="Qwen/Qwen3-Embedding-8B",
        input="""
        КОНТЕКСТ 
        {context}

        СМЫСЛ 
        {meaning}
        """.format(context=data["context"], meaning=data["meaning"]),
    )

    embeddings = embeddings_data.data[0].embedding

    await enriched_message_repo.save(
        dict(
            chat_id=chat_id,
            message_id=message_id,
            context=data["context"],
            meaning=data["meaning"],
            embeddings=embeddings,
        )
    )
