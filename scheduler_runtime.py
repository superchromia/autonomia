import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from dependency import dependency
from models.message import Message
from models.scheduled_task import ScheduledTask

logger = logging.getLogger("scheduler_runtime")

scheduler = AsyncIOScheduler()


def _build_trigger(
    cron_expression: str | None = None,
    run_at: datetime | str | None = None,
):
    cron_value = (cron_expression or "").strip()
    has_run_at = run_at is not None and str(run_at).strip() != ""
    if bool(cron_value) == bool(has_run_at):
        raise ValueError("Provide exactly one of cron_expression or run_at")

    if cron_value:
        return CronTrigger.from_crontab(cron_value)

    if isinstance(run_at, datetime):
        run_date = run_at
    else:
        run_date = datetime.fromisoformat(str(run_at).strip())
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=UTC)
    return DateTrigger(run_date=run_date)


async def _run_query_job(
    task_id: str,
    chat_id: int,
    query: str,
    send_to_chat: bool = True,
    planned_sender_id: int | None = None,
    reply_to_message_id: int | None = None,
):
    async for session in dependency.get_session():
        max_id_result = await session.execute(
            select(func.max(Message.message_id)).where(
                Message.chat_id == chat_id
            )
        )
        max_message_id = max_id_result.scalar_one_or_none() or 0
        planned_message_id = int(max_message_id) + 1

        raw_data = {
            "id": planned_message_id,
            "message": query,
            "scheduled": True,
            "scheduled_task_id": task_id,
        }
        if reply_to_message_id is not None:
            raw_data["reply_to"] = {"reply_to_msg_id": reply_to_message_id}

        planned_message = Message(
            message_id=planned_message_id,
            chat_id=chat_id,
            sender_id=planned_sender_id,
            date=datetime.now(UTC),
            message_type="text",
            is_read=True,
            is_deleted=False,
            raw_data=raw_data,
        )
        session.add(planned_message)
        await session.commit()

        from processing.enrich_message import generate_bot_response

        response_text = await generate_bot_response(
            session=session,
            chat_id=chat_id,
            message_id=planned_message_id,
        )

        if send_to_chat and response_text:
            if not dependency.telegram_client:
                logger.warning(
                    "Scheduled query %s generated response but no telegram client",
                    task_id,
                )
                return
            await dependency.telegram_client.send_message(chat_id, response_text)

        logger.info(
            (
                "Scheduled query processed via full context pipeline: %s, "
                "chat_id=%s, message_id=%s, sent_to_chat=%s"
            ),
            task_id,
            chat_id,
            planned_message_id,
            send_to_chat,
        )
        break


def _apply_task_to_scheduler(task: ScheduledTask):
    if not task.enabled:
        if scheduler.get_job(task.id):
            scheduler.remove_job(task.id)
        return

    trigger = _build_trigger(
        cron_expression=task.cron_expression,
        run_at=task.run_at,
    )
    scheduler.add_job(
        _run_query_job,
        trigger=trigger,
        id=task.id,
        replace_existing=True,
        kwargs={
            "task_id": task.id,
            "chat_id": task.chat_id,
            "query": task.query,
            "send_to_chat": task.send_to_chat,
            "planned_sender_id": task.planned_sender_id,
            "reply_to_message_id": task.reply_to_message_id,
        },
    )


async def sync_scheduled_tasks(session: AsyncSession | None = None):
    owns_session = session is None
    if owns_session:
        async for new_session in dependency.get_session():
            session = new_session
            break
    if session is None:
        return

    result = await session.execute(select(ScheduledTask))
    tasks = result.scalars().all()
    db_ids = {task.id for task in tasks}

    for task in tasks:
        try:
            _apply_task_to_scheduler(task)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception(
                "Failed to apply scheduled task %s: %s",
                task.id,
                exc,
            )

    for job in scheduler.get_jobs():
        if job.func != _run_query_job:
            continue
        if job.id not in db_ids:
            scheduler.remove_job(job.id)


async def sync_scheduled_tasks_job():
    await sync_scheduled_tasks()


def create_scheduled_task(
    task_id: str,
    chat_id: int,
    query: str,
    cron_expression: str | None = None,
    run_at: str | None = None,
    send_to_chat: bool = True,
    planned_sender_id: int | None = None,
    reply_to_message_id: int | None = None,
):
    task = ScheduledTask(
        id=task_id,
        chat_id=chat_id,
        query=query,
        cron_expression=cron_expression,
        run_at=(
            datetime.fromisoformat(run_at)
            if isinstance(run_at, str) and run_at
            else run_at
        ),
        send_to_chat=send_to_chat,
        planned_sender_id=planned_sender_id,
        reply_to_message_id=reply_to_message_id,
        enabled=True,
    )
    _apply_task_to_scheduler(task)
    return scheduler.get_job(task_id)


def edit_scheduled_task(
    task_id: str,
    chat_id: int | None = None,
    query: str | None = None,
    cron_expression: str | None = None,
    run_at: str | None = None,
    send_to_chat: bool | None = None,
    planned_sender_id: int | None = None,
    reply_to_message_id: int | None = None,
):
    existing = scheduler.get_job(task_id)
    if not existing:
        raise ValueError(f"Task with id '{task_id}' not found")

    current = dict(existing.kwargs or {})
    next_chat_id = chat_id if chat_id is not None else current.get("chat_id")
    next_query = query if query is not None else current.get("query")
    next_send_to_chat = (
        send_to_chat
        if send_to_chat is not None
        else current.get("send_to_chat", True)
    )
    next_sender_id = (
        planned_sender_id
        if planned_sender_id is not None
        else current.get("planned_sender_id")
    )
    next_reply_id = (
        reply_to_message_id
        if reply_to_message_id is not None
        else current.get("reply_to_message_id")
    )

    trigger = existing.trigger
    if cron_expression or run_at:
        trigger = _build_trigger(
            cron_expression=cron_expression,
            run_at=run_at,
        )

    scheduler.add_job(
        _run_query_job,
        trigger=trigger,
        id=task_id,
        replace_existing=True,
        kwargs={
            "task_id": task_id,
            "chat_id": next_chat_id,
            "query": next_query,
            "send_to_chat": next_send_to_chat,
            "planned_sender_id": next_sender_id,
            "reply_to_message_id": next_reply_id,
        },
    )
    return scheduler.get_job(task_id)


def delete_scheduled_task(task_id: str):
    if not scheduler.get_job(task_id):
        raise ValueError(f"Task with id '{task_id}' not found")
    scheduler.remove_job(task_id)
