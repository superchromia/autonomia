import logging
import os

import aiohttp

logger = logging.getLogger("nebius")

GUIDED_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "mood": {"type": "string"},
    },
}


class NebiusAIStudioClient:
    def __init__(
        self, model_id: str, api_key: str = None, base_url: str = None
    ):
        self.model_id = model_id
        self.api_key = api_key or os.environ.get("NEBIUS_STUDIO_API_KEY")
        self.base_url = base_url or "https://api.studio.nebius.com/v1/"

    async def chat_completion(
        self,
        messages,
        max_tokens: int,
        temperature: float,
        extra_body=None,
        response_format=None,
    ):
        url = self.base_url + "chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if extra_body:
            payload.update(extra_body)
        if response_format:
            payload["response_format"] = response_format
        logger.debug(f"Sending async request to Nebius: {payload}")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, json=payload, timeout=30
            ) as resp:
                logger.debug(f"Nebius response status: {resp.status}")
                resp.raise_for_status()
                data = await resp.json()
                logger.debug(f"Nebius response data: {data}")
                return data

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        messages,
        temperature: float = 0.7,
        max_tokens: int = 256,
    ) -> str:
        ctx_messages = [
            {"role": "system", "content": system_prompt},
        ]
        ctx_messages.extend(messages)
        ctx_messages.append({"role": "user", "content": user_prompt})
        data = await self.chat_completion(
            messages=ctx_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body=None,
            response_format=None,
        )
        # Return the text of the first response
        return data["choices"][0]["message"]["content"]
