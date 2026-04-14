import asyncio
import json
import logging

from fastapi import APIRouter
from starlette.responses import StreamingResponse

router = APIRouter(tags=["stream"])

logger = logging.getLogger(__name__)

event_queue: asyncio.Queue = asyncio.Queue(maxsize=100)


async def push_event(event_type: str, data: dict):
    try:
        event_queue.put_nowait({"event": event_type, "data": data})
    except asyncio.QueueFull:
        pass


async def event_generator():
    while True:
        try:
            event = await asyncio.wait_for(event_queue.get(), timeout=30)
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
        except asyncio.TimeoutError:
            yield ": keepalive\n\n"


@router.get("/stream")
async def stream_events():
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
