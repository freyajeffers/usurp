from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)


class ProxyProtocol(StrEnum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class DeviceType(StrEnum):
    DESKTOP = "desktop"
    MOBILE = "mobile"


class ProxyNode(StrictModel):
    id: UUID
    uri: HttpUrl
    protocol: ProxyProtocol
    region: str = Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    consecutive_failures: int = Field(default=0, ge=0)
    avg_latency_ms: float = Field(default=0.0, ge=0.0)
    is_active: bool = True
    quarantined_until: datetime | None = None


class TransportRequest(StrictModel):
    query: str = Field(min_length=1, max_length=2048)
    country_code: str = Field(default="us", min_length=2, max_length=2, pattern=r"^[a-z]{2}$")
    language_code: str = Field(default="en", min_length=2, max_length=8)
    start_offset: int = Field(default=0, ge=0)
    num_results: int = Field(default=10, ge=1, le=100)
    time_range: str | None = Field(default=None, max_length=64)
    device_type: DeviceType = DeviceType.DESKTOP
    session_id: str | None = Field(default=None, min_length=1, max_length=128)


class TransportResult(StrictModel):
    status_code: int = Field(ge=100, le=599)
    headers: dict[str, str]
    raw_html: str
    response_time_ms: float = Field(ge=0.0)
    proxy_used_id: UUID | None = None
    escalation_required: bool = False

    def as_mapping(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
