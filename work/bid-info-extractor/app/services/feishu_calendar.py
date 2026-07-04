from __future__ import annotations

"""Feishu Calendar API integration."""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import httpx

FEISHU_AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
FEISHU_CALENDAR_LIST_URL = "https://open.feishu.cn/open-apis/calendar/v4/calendars"
FEISHU_FREEBUSY_URL = "https://open.feishu.cn/open-apis/calendar/v4/freebusy/list"
FEISHU_EVENTS_URL = "https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events"


@dataclass
class CalendarEventResult:
    feishu_event_id: str = ""
    calendar_id: str = ""
    event_date: Optional[datetime] = None
    slot_start: Optional[datetime] = None
    slot_end: Optional[datetime] = None
    success: bool = False
    error: str = ""


class FeishuCalendarClient:
    """Async client for Feishu Calendar API."""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    async def _get_token(self) -> str:
        """Get or refresh tenant_access_token (cached for 2h)."""
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                FEISHU_AUTH_URL,
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"飞书认证失败: {data.get('msg', 'Unknown error')}")

            self._token = data["tenant_access_token"]
            self._token_expires_at = time.time() + data.get("expire", 7200)
            return self._token

    def _headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def get_calendar_list(self) -> list[dict]:
        """Get user's calendar list."""
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                FEISHU_CALENDAR_LIST_URL,
                headers=self._headers(token),
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"获取日历列表失败: {data.get('msg')}")
            return data.get("data", {}).get("calendar_list", [])

    async def get_freebusy(
        self, calendar_id: str, date: datetime
    ) -> list[dict]:
        """Query free/busy slots for a calendar on a specific date."""
        token = await self._get_token()
        time_min = date.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        time_max = date.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%dT%H:%M:%S+08:00")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                FEISHU_FREEBUSY_URL,
                headers=self._headers(token),
                json={
                    "time_min": time_min,
                    "time_max": time_max,
                    "user_id": calendar_id,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"查询忙闲失败: {data.get('msg')}")

            busy_list = data.get("data", {}).get("busy_list", [])
            return [
                {"start": b["start_time"], "end": b["end_time"]}
                for b in busy_list
            ]

    async def create_event(
        self,
        calendar_id: str,
        summary: str,
        start_time: datetime,
        end_time: datetime,
    ) -> CalendarEventResult:
        """Create a calendar event."""
        token = await self._get_token()

        body = {
            "summary": summary,
            "start_time": {
                "timestamp": start_time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            },
            "end_time": {
                "timestamp": end_time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            },
        }

        url = FEISHU_EVENTS_URL.format(calendar_id=calendar_id)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers=self._headers(token),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                return CalendarEventResult(
                    calendar_id=calendar_id,
                    slot_start=start_time,
                    slot_end=end_time,
                    success=False,
                    error=data.get("msg", "Unknown error"),
                )

            event_data = data.get("data", {}).get("event", {})
            return CalendarEventResult(
                feishu_event_id=event_data.get("event_id", ""),
                calendar_id=calendar_id,
                slot_start=start_time,
                slot_end=end_time,
                success=True,
            )

    async def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Delete a calendar event."""
        token = await self._get_token()
        url = f"{FEISHU_EVENTS_URL.format(calendar_id=calendar_id)}/{event_id}"

        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=self._headers(token))
            resp.raise_for_status()
            data = resp.json()
            return data.get("code") == 0


# ── Slot allocation algorithm ────────────────────────────

SLOT_CANDIDATES = [
    (9, 0, 10, 0),    # 09:00-10:00
    (11, 0, 12, 0),   # 11:00-12:00
    (13, 0, 14, 0),   # 13:00-14:00
    (15, 0, 16, 0),   # 15:00-16:00
    (16, 30, 17, 30), # 16:30-17:30 (extra slot)
]

MAX_BACKTRACK_DAYS = 3


def _is_weekday(d: datetime) -> bool:
    """Check if date is a weekday (Mon-Fri)."""
    return d.weekday() < 5


def _find_previous_weekday(d: datetime) -> datetime:
    """Find the nearest previous weekday."""
    while not _is_weekday(d):
        d = d - timedelta(days=1)
    return d


def _slot_overlaps_busy(
    slot_start: datetime,
    slot_end: datetime,
    busy_slots: list[dict],
) -> bool:
    """Check if a time slot overlaps with any busy slot."""
    for busy in busy_slots:
        # Parse Feishu timestamps — may be int (unix) or str (ISO)
        busy_start = _to_datetime(busy.get("start", ""))
        busy_end = _to_datetime(busy.get("end", ""))
        if busy_start and busy_end:
            if slot_start < busy_end and slot_end > busy_start:
                return True
    return False


def _to_datetime(val) -> Optional[datetime]:
    """Convert various timestamp formats to datetime."""
    if isinstance(val, int):
        return datetime.fromtimestamp(val)
    if isinstance(val, str):
        # Try ISO format
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00").replace("+08:00", "+08:00"))
        except (ValueError, TypeError):
            pass
    return None


def allocate_calendar_slot(
    deadline: datetime,
    busy_slots: list[dict],
    existing_slots_in_db: Optional[list] = None,
) -> tuple[datetime, datetime] | None:
    """Allocate a free calendar slot for a bid reminder.

    Rules:
    1. Remind date = deadline - 4 days (weekday-adjusted)
    2. Try slots: 9-10, 11-12, 13-14, 15-16, 16:30-17:30
    3. First free slot wins
    4. If all full, backtrack up to 3 previous weekdays

    Returns (slot_start, slot_end) or None if no slot found.
    """
    remind_date = deadline - timedelta(days=4)
    remind_date = _find_previous_weekday(remind_date)

    existing = existing_slots_in_db or []

    for backtrack in range(MAX_BACKTRACK_DAYS + 1):
        target_date = remind_date - timedelta(days=backtrack)
        if not _is_weekday(target_date):
            continue

        for sh, sm, eh, em in SLOT_CANDIDATES:
            slot_start = target_date.replace(hour=sh, minute=sm, second=0, microsecond=0)
            slot_end = target_date.replace(hour=eh, minute=em, second=0, microsecond=0)

            # Check against Feishu busy slots
            if _slot_overlaps_busy(slot_start, slot_end, busy_slots):
                continue

            # Check against existing DB slots
            db_conflict = False
            for exist_start, exist_end in existing:
                if slot_start < exist_end and slot_end > exist_start:
                    db_conflict = True
                    break
            if db_conflict:
                continue

            return (slot_start, slot_end)

    # Fallback: use the first slot on remind_date even if busy
    # (Feishu allows overlapping events)
    sh, sm, eh, em = SLOT_CANDIDATES[0]
    slot_start = remind_date.replace(hour=sh, minute=sm, second=0, microsecond=0)
    slot_end = remind_date.replace(hour=eh, minute=em, second=0, microsecond=0)
    return (slot_start, slot_end)
