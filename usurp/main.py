import os
from pathlib import Path
from secrets import compare_digest

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field

from usurp.browser.camofox import CamofoxEscalator
from usurp.escalation import EscalationManager
from usurp.providers import GoogleProgrammableSearchProvider
from usurp.rate_limit import RateLimitPolicy, TokenBucketRateLimiter
from usurp.service import BrowserChallengeError, RateLimitExceededError, SearchService
from usurp.transport import DeviceType, FastPathTransport, TransportRequest

app = FastAPI(title="usurp - SERP Extraction Engine")
templates = Jinja2Templates(directory=str(Path(__file__).parents[1] / "templates"))


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


class EscalationSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    rendered_html: str = Field(min_length=1, max_length=5_000_000)


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


_ESCALATION_MANAGER = EscalationManager(Path.home() / ".cache" / "usurp" / "escalations")


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
        escalation_manager=_ESCALATION_MANAGER,
        official_provider=GoogleProgrammableSearchProvider.from_environment(),
    )


def get_escalation_manager() -> EscalationManager:
    return _ESCALATION_MANAGER


def authorize_api_key(api_key: str | None) -> None:
    expected_api_key = os.getenv("USURP_API_KEY")
    if expected_api_key is not None and (
        api_key is None or not compare_digest(api_key, expected_api_key)
    ):
        raise HTTPException(status_code=401, detail="invalid API key")


@app.get("/admin/ui", response_class=HTMLResponse)
async def admin_ui(
    request: Request,
    api_key: str | None = None,
    manager: EscalationManager = Depends(get_escalation_manager),  # noqa: B008
) -> HTMLResponse:
    authorize_api_key(api_key)
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"tickets": manager.list_tickets(), "api_key": api_key},
    )


@app.post("/admin/ui/resolve")
async def admin_ui_resolve(
    api_key: str = Form(...),
    ticket_id: str = Form(...),
    html_file: UploadFile = File(...),  # noqa: B008
    manager: EscalationManager = Depends(get_escalation_manager),  # noqa: B008
) -> RedirectResponse:
    authorize_api_key(api_key)
    if html_file.content_type not in ("text/html", "application/xhtml+xml"):
        raise HTTPException(status_code=400, detail="html_file must be text/html")
    contents = (await html_file.read(5_000_001)).decode("utf-8")
    if len(contents) > 5_000_000:
        raise HTTPException(status_code=413, detail="html_file is too large")
    try:
        manager.submit_solution(ticket_id, contents)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="ticket not found") from exc
    return RedirectResponse(url=f"/admin/ui?api_key={api_key}", status_code=303)


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
    authorize_api_key(query.api_key)
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


@app.get("/admin/escalations")
async def list_escalations(
    api_key: str | None = None,
    manager: EscalationManager = Depends(get_escalation_manager),  # noqa: B008
) -> list[dict[str, object]]:
    authorize_api_key(api_key)
    return manager.list_tickets()


@app.post("/admin/escalations/{ticket_id}/resolve")
async def resolve_escalation(
    ticket_id: str,
    submission: EscalationSubmission,
    api_key: str | None = None,
    manager: EscalationManager = Depends(get_escalation_manager),  # noqa: B008
) -> dict[str, object]:
    authorize_api_key(api_key)
    try:
        return manager.submit_solution(ticket_id, submission.rendered_html)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="escalation ticket not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
