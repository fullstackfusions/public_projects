from __future__ import annotations

import asyncio
import json
from typing import Optional

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from shared.errors import NotFoundError

from ..domain.diff import get_or_create_device_result

router = APIRouter(tags=["streaming"])

_PRESIGNED_CACHE: dict[str, str] = {}
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
_INITIAL_CHUNK_SIZE = 4096


def _is_presigned_url(text: Optional[str]) -> bool:
    if not text:
        return False
    s = text.strip()
    return s.startswith("http://") or s.startswith("https://")


async def _fetch_url(url: str) -> str:
    url = url.strip()
    if url in _PRESIGNED_CACHE:
        return _PRESIGNED_CACHE[url]
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content = resp.text
    except httpx.HTTPStatusError as exc:
        content = f"Error fetching URL (HTTP {exc.response.status_code}): {url}"
    except httpx.RequestError as exc:
        content = f"Error fetching URL: {url} - {exc}"
    _PRESIGNED_CACHE[url] = content
    return content


async def _resolve_output(raw: Optional[str]) -> str:
    if not raw:
        return ""
    if _is_presigned_url(raw):
        return await _fetch_url(raw)
    return raw


async def _stream_initial_metadata(change_request_id: str, device_id: str):  # type: ignore[return]
    try:
        result = get_or_create_device_result(change_request_id, device_id)

        yield f"data: {json.dumps({'type': 'metadata', 'data': {'change_request_id': result.change_request_id, 'device_id': result.device_id, 'device_name': result.device_name, 'device_status': result.device_status, 'validation_status': result.validation_status, 'streaming_metadata': result.streaming_metadata.model_dump() if result.streaming_metadata else None}})}\n\n"
        await asyncio.sleep(0.05)

        for side, outputs in [("pre_check", result.pre_check_output), ("post_check", result.post_check_output)]:
            if outputs:
                for idx, cmd in enumerate(outputs):
                    yield f"data: {json.dumps({'type': f'{side}_command', 'data': {'index': idx, 'command': cmd.command, 'size': cmd.size, 'total_commands': len(outputs)}})}\n\n"

        yield f"data: {json.dumps({'type': 'llm_analysis', 'data': {'analysis': result.llm_analysis}})}\n\n"

        for side_label, outputs in [("pre", result.pre_check_output), ("post", result.post_check_output)]:
            if outputs:
                for idx, cmd in enumerate(outputs):
                    text = await _resolve_output(cmd.output)
                    if not text:
                        continue
                    chunk = text[:_INITIAL_CHUNK_SIZE]
                    yield f"data: {json.dumps({'type': 'initial_data', 'data': {'side': side_label, 'command_index': idx, 'chunk': chunk, 'offset': 0, 'total_size': len(text), 'has_more': len(text) > _INITIAL_CHUNK_SIZE}})}\n\n"

        yield f"data: {json.dumps({'type': 'initial_complete', 'data': {'message': 'Initial stream completed'}})}\n\n"

    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(exc)}})}\n\n"


async def _stream_next_chunk(
    change_request_id: str, device_id: str, offset: int, side: str, command_index: int
):  # type: ignore[return]
    try:
        result = get_or_create_device_result(change_request_id, device_id)
        outputs = result.pre_check_output if side == "pre" else result.post_check_output
        if not outputs or command_index >= len(outputs):
            raise NotFoundError("Command not found")

        text = await _resolve_output(outputs[command_index].output)
        if not text:
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': 'No output available for this command'}})}\n\n"
            return

        chunk = text[offset : offset + _INITIAL_CHUNK_SIZE]
        if chunk:
            yield f"data: {json.dumps({'type': 'chunk_data', 'data': {'side': side, 'command_index': command_index, 'chunk': chunk, 'offset': offset, 'total_size': len(text), 'has_more': offset + _INITIAL_CHUNK_SIZE < len(text)}})}\n\n"

        yield f"data: {json.dumps({'type': 'chunk_complete', 'data': {'message': 'Chunk delivered'}})}\n\n"

    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(exc)}})}\n\n"


@router.get("/{change_request_id}/{device_id}/stream")
async def stream_validation_result(
    change_request_id: str,
    device_id: str,
    offset: Optional[int] = None,
    side: Optional[str] = None,
    command_index: Optional[int] = None,
) -> StreamingResponse:
    if offset is not None and side is not None and command_index is not None:
        generator = _stream_next_chunk(change_request_id, device_id, offset, side, command_index)
    else:
        generator = _stream_initial_metadata(change_request_id, device_id)

    return StreamingResponse(generator, media_type="text/event-stream", headers=_SSE_HEADERS)
