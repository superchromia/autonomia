#!/usr/bin/env python3
import argparse
import asyncio
import gzip
import json
import os
from collections import deque
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.types import Message


def make_jsonable(x: Any) -> Any:
    if x is None or isinstance(x, (str, int, float, bool)):
        return x
    if isinstance(x, (datetime, date)):
        return x.isoformat()
    if isinstance(x, dict):
        return {str(k): make_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [make_jsonable(v) for v in x]
    return str(x)


def open_text_maybe_gz(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "at", encoding="utf-8", newline="\n")
    return open(path, "a", encoding="utf-8", newline="\n")


def load_checkpoint(path: str) -> Dict[str, int]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {str(k): int(v) for k, v in data.items()}


def save_checkpoint(path: str, ckpt: Dict[str, int]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ckpt, f, ensure_ascii=False)
    os.replace(tmp, path)


def is_text_only(msg: Message) -> bool:
    # сервисные сообщения (вступил/вышел/пин/и т.п.)
    if getattr(msg, "action", None) is not None:
        return False
    # любое медиа (фото/видео/стикер/голос/док/опрос и т.д.) — режем
    if getattr(msg, "media", None) is not None:
        return False
    # оставляем только обычный текст
    text = getattr(msg, "message", None)
    if not text or not text.strip():
        return False
    return True


class ReplyTextCache:
    """
    LRU-ish кэш для (chat_id, message_id) -> text.
    Не бесконечный, чтобы не сожрать RAM на миллионах сообщений.
    """

    def __init__(self, max_items: int):
        self.max_items = max_items
        self.data: Dict[Tuple[int, int], str] = {}
        self.order = deque()  # keys in insertion order

    def get(self, key: Tuple[int, int]) -> Optional[str]:
        return self.data.get(key)

    def put(self, key: Tuple[int, int], text: str) -> None:
        if not text:
            return
        if key in self.data:
            self.data[key] = text
            return
        self.data[key] = text
        self.order.append(key)
        while len(self.order) > self.max_items:
            old = self.order.popleft()
            # может быть уже перезаписан/удалён — проверяем
            self.data.pop(old, None)


async def get_reply_text_best_effort(
    msg: Message,
    dialog_id: int,
    cache: ReplyTextCache,
    fetch_missing: bool,
) -> Optional[str]:
    reply_to = getattr(msg, "reply_to", None)
    reply_id = getattr(reply_to, "reply_to_msg_id", None) if reply_to else None
    if not isinstance(reply_id, int):
        return None

    key = (dialog_id, reply_id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    if not fetch_missing:
        return None

    try:
        r = await msg.get_reply_message()
        if not r:
            return None
        text = (getattr(r, "message", None) or "").strip()
        if not text:
            return None
        cache.put(key, text)
        return text
    except RPCError:
        return None


async def dump_all_text_only_with_reply_text(
    api_id: int,
    api_hash: str,
    session: str,
    out_path: str,
    checkpoint_path: str,
    save_every: int,
    reverse: bool,
    fetch_missing_replies: bool,
    reply_cache_size: int,
) -> None:
    ckpt = load_checkpoint(checkpoint_path)
    cache = ReplyTextCache(max_items=reply_cache_size)

    client = TelegramClient(session, api_id, api_hash)
    await client.start()

    me = await client.get_me()
    my_id = getattr(me, "id", None)

    total_written = 0
    total_seen = 0
    total_chats = 0

    with open_text_maybe_gz(out_path) as out:
        async for dialog in client.iter_dialogs():
            total_chats += 1
            entity = dialog.entity
            dialog_id = dialog.id
            chat_key = str(dialog_id)

            last_id = ckpt.get(chat_key, 0)

            chat_meta = {
                "dialog_id": dialog_id,
                "entity_type": type(entity).__name__,
                "title": getattr(dialog, "name", None),
                "username": getattr(entity, "username", None),
            }

            try:
                async for msg in client.iter_messages(
                    entity,
                    min_id=last_id,
                    reverse=reverse,  # True: старые->новые
                    limit=None,
                ):
                    total_seen += 1

                    # чекпоинт обновляем всегда, даже если сообщение пропускаем
                    mid = getattr(msg, "id", None)
                    if isinstance(mid, int) and mid > (ckpt.get(chat_key, 0) or 0):
                        ckpt[chat_key] = mid

                    if not is_text_only(msg):
                        if total_seen % save_every == 0:
                            out.flush()
                            save_checkpoint(checkpoint_path, ckpt)
                        continue

                    # добавляем текущее сообщение в кэш (полезно для будущих reply)
                    this_text = (msg.message or "").strip()
                    if this_text:
                        cache.put((dialog_id, msg.id), this_text)

                    reply_to = getattr(msg, "reply_to", None)
                    reply_id = getattr(reply_to, "reply_to_msg_id", None) if reply_to else None
                    reply_text = await get_reply_text_best_effort(
                        msg=msg,
                        dialog_id=dialog_id,
                        cache=cache,
                        fetch_missing=fetch_missing_replies,
                    )

                    fwd = getattr(msg, "fwd_from", None)
                    fwd_dict = make_jsonable(fwd.to_dict()) if fwd else None

                    record = {
                        "chat": chat_meta,
                        "self_user_id": my_id,
                        "message": {
                            "id": msg.id,
                            "date": make_jsonable(msg.date),
                            "sender_id": msg.sender_id,
                            "out": bool(getattr(msg, "out", False)),
                            "text": msg.message,
                            "edit_date": make_jsonable(getattr(msg, "edit_date", None)),
                            "forward": fwd_dict,
                            "reply_to_msg_id": reply_id if isinstance(reply_id, int) else None,
                            "reply_to_text": reply_text,
                        },
                    }

                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    total_written += 1

                    if total_written % save_every == 0:
                        out.flush()
                        save_checkpoint(checkpoint_path, ckpt)

            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 1)
            except RPCError:
                continue

        out.flush()
        save_checkpoint(checkpoint_path, ckpt)

    await client.disconnect()
    print(f"Done. Chats: {total_chats}, seen: {total_seen}, written(text-only): {total_written}")
    print(f"Output: {out_path}")
    print(f"Checkpoint: {checkpoint_path}")


def main():

    p = argparse.ArgumentParser(description="Dump ALL Telegram TEXT-ONLY messages + replied-to text into JSONL (optionally .gz)")
    p.add_argument("--api-id", type=int, default=int(os.environ.get("TELEGRAM_API_ID", "0")))
    p.add_argument("--api-hash", type=str, default=os.environ.get("TELEGRAM_API_HASH", ""))
    p.add_argument("--session", type=str, default="tg_dumper.session")
    p.add_argument("--out", type=str, default="telegram_text_only_with_replies.jsonl")
    p.add_argument("--checkpoint", type=str, default="telegram_text_only_with_replies.checkpoint.json")
    p.add_argument("--save-every", type=int, default=5000)
    p.add_argument("--newest-first", action="store_true", help="Dump newest->oldest (default oldest->newest)")
    p.add_argument("--fetch-missing-replies", action="store_true", help="If reply_to_text not in cache, fetch replied message from Telegram (more API calls)")
    p.add_argument("--reply-cache-size", type=int, default=200000, help="Max cached (chat_id,message_id)->text entries for fast reply lookups")
    args = p.parse_args()

    if not args.api_id or not args.api_hash:
        raise SystemExit("Need --api-id and --api-hash (or TELEGRAM_API_ID/TELEGRAM_API_HASH env vars).")

    reverse = not args.newest_first  # reverse=True => старые->новые
    asyncio.run(
        dump_all_text_only_with_reply_text(
            api_id=args.api_id,
            api_hash=args.api_hash,
            session=args.session,
            out_path=args.out,
            checkpoint_path=args.checkpoint,
            save_every=args.save_every,
            reverse=reverse,
            fetch_missing_replies=args.fetch_missing_replies,
            reply_cache_size=args.reply_cache_size,
        )
    )


if __name__ == "__main__":
    main()
