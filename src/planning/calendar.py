"""Calendar boundary with read/insert only. Mock events persist across restarts."""

from __future__ import annotations

from datetime import datetime

from googleapiclient.errors import HttpError

from config.settings import settings
from src.calendar_api import events, mock_calendar
from src.domain.time import aware


class CalendarGateway:
    def __init__(self, store, mode: str, calendar_id: str):
        if mode not in {"mock", "live"}:
            raise ValueError("Unknown calendar mode")
        self.store, self.mode, self.calendar_id = store, mode, calendar_id

    def busy(self, start, end, timezone: str, exclude_ids=()) -> list[dict]:
        if self.mode == "live":
            return events.fetch_busy_blocks(
                start,
                end,
                self.calendar_id,
                timezone=timezone,
                exclude_ids=set(exclude_ids),
            )
        result = mock_calendar.fetch_mock_busy_blocks(start, end, timezone=timezone)
        for event in self.store.mock_events(self.calendar_id):
            if event["id"] in exclude_ids:
                continue
            a, b = (aware(event[key]["dateTime"], timezone) for key in ("start", "end"))
            if a < end and b > start:
                result.append({"start": a.isoformat(), "end": b.isoformat()})
        return result

    def get(self, event_id: str) -> dict | None:
        if self.mode == "mock":
            return next(
                (
                    event
                    for event in self.store.mock_events(self.calendar_id)
                    if event["id"] == event_id
                ),
                None,
            )
        try:
            return events.get_event(event_id, self.calendar_id)
        except HttpError as exc:
            if exc.resp.status == 404:
                return None
            raise

    def insert(self, event: dict, event_id: str) -> dict:
        if self.mode == "live":
            return events.create_event(
                summary=event["name"],
                description=event["description"],
                start=datetime.fromisoformat(event["start"]),
                end=datetime.fromisoformat(event["end"]),
                calendar_id=self.calendar_id,
                color_id=settings.AGENT_EVENT_COLOR_ID,
                event_id=event_id,
            )
        payload = {
            "id": event_id,
            "summary": event["name"],
            "description": event["description"],
            "start": {"dateTime": event["start"]},
            "end": {"dateTime": event["end"]},
            "status": "confirmed",
        }
        return self.store.insert_mock(self.calendar_id, event_id, payload)


def matches(event: dict, remote: dict) -> bool:
    """A same-ID response is only success if it describes the approved event."""
    try:
        return (
            remote.get("status") != "cancelled"
            and remote.get("summary") == event["name"]
            and aware(remote["start"]["dateTime"]) == aware(event["start"])
            and aware(remote["end"]["dateTime"]) == aware(event["end"])
        )
    except (KeyError, ValueError, TypeError):
        return False
