import json
from datetime import UTC, datetime

from models.scheduled_task import ScheduledTask
from scheduler_runtime import (
    create_scheduled_task,
    delete_scheduled_task,
    edit_scheduled_task,
    scheduler,
    sync_scheduled_tasks,
)

CREATE_SCHEDULED_TASK_NAME = "create_scheduled_task"
EDIT_SCHEDULED_TASK_NAME = "edit_scheduled_task"
DELETE_SCHEDULED_TASK_NAME = "delete_scheduled_task"

CREATE_SCHEDULED_TASK_TOOL = {
    "type": "function",
    "function": {
        "name": CREATE_SCHEDULED_TASK_NAME,
        "description": (
            "Schedule a planned message and generate reply using full chat context."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Optional unique task id.",
                },
                "query": {
                    "type": "string",
                    "description": "Query text to process at run time.",
                },
                "cron_expression": {
                    "type": "string",
                    "description": "Optional 5-field crontab expression.",
                },
                "run_at": {
                    "type": "string",
                    "description": "Optional ISO datetime for one-time run.",
                },
                "chat_id": {
                    "type": "integer",
                    "description": (
                        "Optional chat id, defaults to current chat."
                    ),
                },
                "send_to_chat": {
                    "type": "boolean",
                    "description": "Send generated response to chat.",
                },
                "planned_sender_id": {
                    "type": "integer",
                    "description": (
                        "Optional sender id for the planned message."
                    ),
                },
                "reply_to_message_id": {
                    "type": "integer",
                    "description": (
                        "Optional message id this planned message replies to."
                    ),
                },
            },
            "required": ["query"],
        },
    },
}

EDIT_SCHEDULED_TASK_TOOL = {
    "type": "function",
    "function": {
        "name": EDIT_SCHEDULED_TASK_NAME,
        "description": "Edit an existing scheduled query task.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Existing task id.",
                },
                "query": {
                    "type": "string",
                    "description": "Optional replacement query.",
                },
                "cron_expression": {
                    "type": "string",
                    "description": "Optional new CRON expression.",
                },
                "run_at": {
                    "type": "string",
                    "description": "Optional new one-time ISO datetime.",
                },
                "chat_id": {
                    "type": "integer",
                    "description": "Optional replacement chat id.",
                },
                "send_to_chat": {
                    "type": "boolean",
                    "description": "Optional send to chat flag.",
                },
                "planned_sender_id": {
                    "type": "integer",
                    "description": (
                        "Optional replacement planned sender id."
                    ),
                },
                "reply_to_message_id": {
                    "type": "integer",
                    "description": (
                        "Optional replacement reply target message id."
                    ),
                },
            },
            "required": ["task_id"],
        },
    },
}

DELETE_SCHEDULED_TASK_TOOL = {
    "type": "function",
    "function": {
        "name": DELETE_SCHEDULED_TASK_NAME,
        "description": "Delete a scheduled query task.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Existing task id.",
                }
            },
            "required": ["task_id"],
        },
    },
}


def _default_task_id(context) -> str:
    ts = int(datetime.now(UTC).timestamp())
    chat_id = getattr(context, "chat_id", "global")
    message_id = getattr(context, "current_message_id", "manual")
    return f"scheduled_query_{chat_id}_{message_id}_{ts}"


def _to_bool(value, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return bool(value)


async def create_task(context, arguments: dict) -> str:
    query = (arguments.get("query") or "").strip()
    if not query:
        return "Missing required argument: query"

    task_id = (
        (arguments.get("task_id") or "").strip()
        or _default_task_id(context)
    )
    chat_id = arguments.get("chat_id", context.chat_id)
    cron_expression = (arguments.get("cron_expression") or "").strip() or None
    run_at = (arguments.get("run_at") or "").strip() or None
    send_to_chat = arguments.get("send_to_chat", True)
    planned_sender_id = arguments.get("planned_sender_id")
    reply_to_message_id = arguments.get("reply_to_message_id")

    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        return "Invalid chat_id"
    if planned_sender_id is not None:
        try:
            planned_sender_id = int(planned_sender_id)
        except (TypeError, ValueError):
            return "Invalid planned_sender_id"
    if reply_to_message_id is not None:
        try:
            reply_to_message_id = int(reply_to_message_id)
        except (TypeError, ValueError):
            return "Invalid reply_to_message_id"

    try:
        send_to_chat = _to_bool(send_to_chat, default=True)
        existing = await context.session.get(ScheduledTask, task_id)
        if existing:
            return f"Task with id '{task_id}' already exists"

        db_task = ScheduledTask(
            id=task_id,
            chat_id=chat_id,
            query=query,
            cron_expression=cron_expression,
            run_at=(
                datetime.fromisoformat(run_at)
                if run_at
                else None
            ),
            send_to_chat=send_to_chat,
            planned_sender_id=planned_sender_id,
            reply_to_message_id=reply_to_message_id,
            enabled=True,
        )
        context.session.add(db_task)
        await context.session.commit()

        job = create_scheduled_task(
            task_id=task_id,
            chat_id=chat_id,
            query=query,
            cron_expression=cron_expression,
            run_at=run_at,
            send_to_chat=send_to_chat,
            planned_sender_id=planned_sender_id,
            reply_to_message_id=reply_to_message_id,
        )
        await sync_scheduled_tasks(session=context.session)
        return json.dumps(
            {
                "status": "ok",
                "action": "created",
                "task_id": task_id,
                "chat_id": chat_id,
                "query": query,
                "cron_expression": cron_expression,
                "run_at": run_at,
                "next_run_time": (
                    job.next_run_time.isoformat()
                    if job and job.next_run_time
                    else None
                ),
            },
            ensure_ascii=False,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return json.dumps(
            {
                "status": "error",
                "action": "create",
                "task_id": task_id,
                "error": str(exc),
            },
            ensure_ascii=False,
        )


async def edit_task(context, arguments: dict) -> str:
    _ = context
    task_id = (arguments.get("task_id") or "").strip()
    if not task_id:
        return "Missing required argument: task_id"

    query = arguments.get("query")
    cron_expression = (arguments.get("cron_expression") or "").strip() or None
    run_at = (arguments.get("run_at") or "").strip() or None
    chat_id = arguments.get("chat_id")
    send_to_chat = arguments.get("send_to_chat")
    planned_sender_id = arguments.get("planned_sender_id")
    reply_to_message_id = arguments.get("reply_to_message_id")

    if chat_id is not None:
        try:
            chat_id = int(chat_id)
        except (TypeError, ValueError):
            return "Invalid chat_id"

    if send_to_chat is not None:
        send_to_chat = _to_bool(send_to_chat, default=True)
    if planned_sender_id is not None:
        try:
            planned_sender_id = int(planned_sender_id)
        except (TypeError, ValueError):
            return "Invalid planned_sender_id"
    if reply_to_message_id is not None:
        try:
            reply_to_message_id = int(reply_to_message_id)
        except (TypeError, ValueError):
            return "Invalid reply_to_message_id"

    try:
        db_task = await context.session.get(ScheduledTask, task_id)
        if not db_task:
            return f"Task with id '{task_id}' not found"

        if chat_id is not None:
            db_task.chat_id = chat_id
        if query is not None:
            db_task.query = query
        if cron_expression:
            db_task.cron_expression = cron_expression
            db_task.run_at = None
        if run_at:
            db_task.run_at = datetime.fromisoformat(run_at)
            db_task.cron_expression = None
        if send_to_chat is not None:
            db_task.send_to_chat = send_to_chat
        if planned_sender_id is not None:
            db_task.planned_sender_id = planned_sender_id
        if reply_to_message_id is not None:
            db_task.reply_to_message_id = reply_to_message_id
        await context.session.commit()

        job = edit_scheduled_task(
            task_id=task_id,
            chat_id=chat_id,
            query=query,
            cron_expression=cron_expression,
            run_at=run_at,
            send_to_chat=send_to_chat,
            planned_sender_id=planned_sender_id,
            reply_to_message_id=reply_to_message_id,
        )
        await sync_scheduled_tasks(session=context.session)
        return json.dumps(
            {
                "status": "ok",
                "action": "edited",
                "task_id": task_id,
                "next_run_time": (
                    job.next_run_time.isoformat()
                    if job and job.next_run_time
                    else None
                ),
            },
            ensure_ascii=False,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return json.dumps(
            {
                "status": "error",
                "action": "edit",
                "task_id": task_id,
                "error": str(exc),
            },
            ensure_ascii=False,
        )


async def delete_task(_context, arguments: dict) -> str:
    task_id = (arguments.get("task_id") or "").strip()
    if not task_id:
        return "Missing required argument: task_id"

    try:
        db_task = await context.session.get(ScheduledTask, task_id)
        if not db_task:
            return f"Task with id '{task_id}' not found"
        await context.session.delete(db_task)
        await context.session.commit()

        delete_scheduled_task(task_id)
        await sync_scheduled_tasks(session=context.session)
        return json.dumps(
            {
                "status": "ok",
                "action": "deleted",
                "task_id": task_id,
                "remaining_task_ids": [job.id for job in scheduler.get_jobs()],
            },
            ensure_ascii=False,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return json.dumps(
            {
                "status": "error",
                "action": "delete",
                "task_id": task_id,
                "error": str(exc),
            },
            ensure_ascii=False,
        )
