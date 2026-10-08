import os
from pathlib import Path
from secrets import compare_digest

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from usurp.browser.camofox import CamofoxEscalator
from usurp.rate_limit import RateLimitPolicy, TokenBucketRateLimiter
from usurp.service import BrowserChallengeError, RateLimitExceededError, SearchService
from usurp.transport import DeviceType, FastPathTransport, TransportRequest

app = FastAPI(title="usurp - SERP Extraction Engine")


class SearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    q: str = Field(min_length=1, max_length=2048)
    gl: str = Field(default="us", min_length=2, max_length=2)
    hl: str = Field(default="en", min_length=2, max_length=8)
    start: int = Field(default=0, ge=0)
    num: int = Field(default=10, ge=1, le=100)
    device: DeviceType = DeviceType.DESKTOP
    api_key: str | None = None
    no_cache: bool = False


async def get_query(
    q: str | None = None,
    gl: str = "us",
    hl: str = "en",
    start: int = 0,
    num: int = 10,
    device: DeviceType = DeviceType.DESKTOP,
    api_key: str | None = None,
    no_cache: bool = False,
) -> SearchQuery | None:
    if q is None:
        return None
    return SearchQuery(
        q=q,
        gl=gl,
        hl=hl,
        start=start,
        num=num,
        device=device,
        api_key=api_key,
        no_cache=no_cache,
    )


def get_service() -> SearchService:
    return SearchService(
        transport=FastPathTransport(),
        cache_path=Path.home() / ".cache" / "usurp" / "serp.sqlite3",
        escalator=CamofoxEscalator(),
        rate_limiter=TokenBucketRateLimiter(
            RateLimitPolicy(
                max_requests_per_minute=60,
                burst_capacity=10,
                per_proxy_delay_seconds=0.0,
            )
        ),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/search")
@app.get("/v1/search")
async def search(
    query: SearchQuery | None = Depends(get_query),  # noqa: B008
    service: SearchService = Depends(get_service),  # noqa: B008
) -> dict[str, object]:
    if query is None:
        raise HTTPException(status_code=400, detail="missing query parameters")
    expected_api_key = os.getenv("USURP_API_KEY")
    if expected_api_key is not None and (
        query.api_key is None or not compare_digest(query.api_key, expected_api_key)
    ):
        raise HTTPException(status_code=401, detail="invalid API key")
    try:
        response = await service.search(
            TransportRequest(
                query=query.q,
                country_code=query.gl,
                language_code=query.hl,
                start_offset=query.start,
                num_results=query.num,
                device_type=query.device,
            ),
            no_cache=query.no_cache,
            rate_limit_key=query.api_key or "anonymous",
        )
    except RateLimitExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except BrowserChallengeError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "browser_challenge_unresolved",
                "challenge_type": exc.challenge_type.value,
                "ticket_id": exc.ticket_id,
                "message": str(exc),
            },
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return response.model_dump(mode="json")
