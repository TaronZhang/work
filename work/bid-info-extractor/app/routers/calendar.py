from __future__ import annotations

"""Feishu calendar API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.db.models import CalendarEvent, Project
from app.services.feishu_calendar import (
    FeishuCalendarClient,
    allocate_calendar_slot,
)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class CreateEventRequest(BaseModel):
    project_id: int


@router.post("/create-event")
async def create_calendar_event(
    req: CreateEventRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a Feishu calendar reminder for a project."""
    result = await db.execute(select(Project).where(Project.id == req.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    if not project.submission_deadline:
        raise HTTPException(400, "请先提取元数据（含截止日期）")

    deadline = project.submission_deadline

    # Check if Feishu is configured
    feishu_app_id = settings.feishu_app_id
    feishu_app_secret = settings.feishu_app_secret
    if not feishu_app_id or not feishu_app_secret:
        raise HTTPException(400, "请先在设置中配置飞书 App ID 和 App Secret")

    # Get existing DB slots (for collision avoidance)
    existing_result = await db.execute(select(CalendarEvent))
    existing_events = existing_result.scalars().all()
    existing_slots = [
        (e.slot_start, e.slot_end)
        for e in existing_events
        if e.slot_start and e.slot_end
    ]

    # Try Feishu calendar integration
    event = None
    try:
        client = FeishuCalendarClient(feishu_app_id, feishu_app_secret)

        # Get calendar list, use primary or first
        calendars = await client.get_calendar_list()
        if not calendars:
            raise HTTPException(400, "未找到飞书日历，请确认应用已授权日历权限")

        calendar_id = calendars[0].get("calendar_id", "primary")

        # Query busy slots
        remind_date = deadline - __import__("datetime").timedelta(days=4)
        busy_slots = await client.get_freebusy(calendar_id, remind_date)

        # Allocate slot
        slot = allocate_calendar_slot(deadline, busy_slots, existing_slots)
        if not slot:
            raise HTTPException(500, "无法分配可用时间段")

        slot_start, slot_end = slot

        # Create event in Feishu
        event_title = f"📋 {project.project_name or '标书'} — 投标截止提醒"
        feishu_result = await client.create_event(
            calendar_id=calendar_id,
            summary=event_title,
            start_time=slot_start,
            end_time=slot_end,
        )

        # Save to DB
        event = CalendarEvent(
            project_id=project.id,
            feishu_event_id=feishu_result.feishu_event_id,
            calendar_id=calendar_id,
            event_title=event_title,
            event_date=slot_start,
            slot_start=slot_start,
            slot_end=slot_end,
            status="created" if feishu_result.success else "failed",
            error_message=feishu_result.error if not feishu_result.success else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        # If Feishu fails, still allocate a local slot
        from datetime import timedelta

        import_date = deadline - timedelta(days=4)
        # weekday adjust
        while import_date.weekday() >= 5:
            import_date = import_date - timedelta(days=1)

        slot_start, slot_end = allocate_calendar_slot(deadline, [], existing_slots) or (
            import_date.replace(hour=9, minute=0, second=0, microsecond=0),
            import_date.replace(hour=10, minute=0, second=0, microsecond=0),
        )

        event = CalendarEvent(
            project_id=project.id,
            event_title=f"📋 {project.project_name or '标书'} — 投标截止提醒",
            event_date=slot_start,
            slot_start=slot_start,
            slot_end=slot_end,
            status="failed",
            error_message=str(e),
        )

    db.add(event)
    await db.flush()

    return {
        "id": event.id,
        "event_title": event.event_title,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "slot_start": event.slot_start.isoformat() if event.slot_start else None,
        "slot_end": event.slot_end.isoformat() if event.slot_end else None,
        "status": event.status,
        "error_message": event.error_message,
    }


@router.get("/events")
async def list_events(db: AsyncSession = Depends(get_db)):
    """List all calendar events with project info."""
    result = await db.execute(
        select(CalendarEvent, Project.project_name, Project.submission_deadline)
        .join(Project, CalendarEvent.project_id == Project.id)
        .order_by(CalendarEvent.created_at.desc())
    )
    rows = result.all()
    return {
        "events": [
            {
                "id": event.id,
                "project_id": event.project_id,
                "project_name": project_name,
                "event_title": event.event_title,
                "event_date": event.event_date.isoformat() if event.event_date else None,
                "slot_start": event.slot_start.isoformat() if event.slot_start else None,
                "slot_end": event.slot_end.isoformat() if event.slot_end else None,
                "status": event.status,
                "error_message": event.error_message,
                "deadline": (
                    submission_deadline.isoformat() if submission_deadline else None
                ),
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event, project_name, submission_deadline in rows
        ]
    }


@router.delete("/events/{event_id}")
async def delete_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a calendar event from DB and Feishu."""
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, "事件不存在")

    # Try to delete from Feishu
    if event.feishu_event_id and event.calendar_id:
        feishu_app_id = settings.feishu_app_id
        feishu_app_secret = settings.feishu_app_secret
        if feishu_app_id and feishu_app_secret:
            try:
                client = FeishuCalendarClient(feishu_app_id, feishu_app_secret)
                await client.delete_event(event.calendar_id, event.feishu_event_id)
            except Exception:
                pass  # Always delete from DB even if Feishu delete fails

    await db.delete(event)
    return {"message": "已删除"}


@router.post("/events/{event_id}/retry")
async def retry_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Retry a failed calendar event creation."""
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, "事件不存在")

    # Delete old failed event, recreate
    await db.delete(event)
    await db.flush()

    # Re-create via the same logic
    return await create_calendar_event(
        CreateEventRequest(project_id=event.project_id), db
    )
