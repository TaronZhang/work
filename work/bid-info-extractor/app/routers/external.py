"""External API endpoints — Bearer Token protected.

Provides machine-readable bid task data for integration with external systems.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import CalendarEvent, Project
from app.security.auth import verify_bearer

router = APIRouter(prefix="/api/external", tags=["external"])


@router.get("/health")
async def health():
    """Health check — no auth required."""
    return {"status": "ok", "version": "2.0.0"}


@router.get("/tasks", dependencies=[Depends(verify_bearer)])
async def list_tasks(
    status: str = Query("active", description="active | all | completed"),
    db: AsyncSession = Depends(get_db),
):
    """Get bid task list with details. Requires Bearer Token.

    Query params:
        status: "active" (default, excluding archived), "all", "completed"
    """
    query = select(Project).order_by(Project.submission_deadline.asc().nullslast())

    result = await db.execute(query)
    projects = result.scalars().all()

    now = __import__("datetime").datetime.now()

    tasks = []
    for i, p in enumerate(projects, 1):
        # Determine if project is active or completed
        is_completed = False
        if p.submission_deadline:
            is_completed = p.submission_deadline < now

        # Filter by status
        if status == "active" and is_completed:
            continue
        if status == "completed" and not is_completed:
            continue

        # Get associated calendar event
        cal_query = select(CalendarEvent).where(
            CalendarEvent.project_id == p.id
        ).order_by(CalendarEvent.created_at.desc()).limit(1)
        cal_result = await db.execute(cal_query)
        cal = cal_result.scalar_one_or_none()

        feishu_info = None
        if cal:
            feishu_info = {
                "remind_date": cal.event_date.isoformat() if cal.event_date else None,
                "slot": (
                    f"{cal.slot_start.strftime('%H:%M')}-{cal.slot_end.strftime('%H:%M')}"
                    if cal.slot_start and cal.slot_end
                    else None
                ),
                "status": cal.status,
            }

        tasks.append({
            "seq": i,
            "client_name": p.bidder_name or "",
            "project_name": p.project_name or "",
            "bid_obtain_deadline": (
                p.bid_obtain_deadline.strftime("%Y-%m-%d %H:%M")
                if p.bid_obtain_deadline else None
            ),
            "submission_deadline": (
                p.submission_deadline.strftime("%Y-%m-%d %H:%M")
                if p.submission_deadline else None
            ),
            "status": "completed" if is_completed else p.status,
            "feishu_event": feishu_info,
        })

    # Count active tasks
    active_count = sum(
        1 for p in projects
        if p.submission_deadline and p.submission_deadline >= now
    )

    return {
        "active_count": active_count,
        "total_count": len(tasks),
        "tasks": tasks,
    }


@router.get("/stats", dependencies=[Depends(verify_bearer)])
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get summary statistics. Requires Bearer Token."""
    result = await db.execute(select(Project))
    projects = result.scalars().all()

    now = __import__("datetime").datetime.now()
    from datetime import timedelta

    active = [p for p in projects if p.submission_deadline and p.submission_deadline >= now]
    completed = [p for p in projects if p.submission_deadline and p.submission_deadline < now]
    urgent = [
        p for p in active
        if p.submission_deadline and (p.submission_deadline - now).days <= 7
    ]

    return {
        "total": len(projects),
        "active": len(active),
        "completed": len(completed),
        "urgent": len(urgent),
        "without_deadline": len([p for p in projects if not p.submission_deadline]),
    }
