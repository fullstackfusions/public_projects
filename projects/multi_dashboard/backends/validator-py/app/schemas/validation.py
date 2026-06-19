from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class StreamingMetadata(BaseModel):
    stream_id: str


class CommandOutput(BaseModel):
    command: str
    output: str
    size: str


class ValidationDeviceResult(BaseModel):
    change_request_id: str
    device_id: str
    device_name: str
    device_status: str
    validation_status: str
    pre_check_output: Optional[List[CommandOutput]] = None
    post_check_output: Optional[List[CommandOutput]] = None
    llm_analysis: str
    streaming_metadata: Optional[StreamingMetadata] = None


class ValidationTask(BaseModel):
    change_request_id: str
    change_description: str
    change_status: str
    created_at: str
    path: str


class PaginatedTasksResponse(BaseModel):
    tasks: List[ValidationTask]
    total: int
    page: int
    page_size: int
    total_pages: int
