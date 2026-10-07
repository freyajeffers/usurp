from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from selectolax.lexbor import LexborHTMLParser


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchMetadata(_StrictModel):
    id: str
    status: str
    created_at: str
    processed_at: str
    total_time_taken: float = Field(ge=0.0)
    google_url: str


class SearchParameters(_StrictModel):
    engine: str = "google"
    q: str
    gl: str
    hl: str
    start: int = Field(ge=0)
    num: int = Field(ge=1, le=100)
    device: str


class OrganicResult(_StrictModel):
    position: int = Field(ge=1)
    title: str = Field(min_length=1)
    link: str = Field(min_length=1)
    displayed_link: str = ""
    snippet: str = ""
    snippet_highlighted_words: list[str] | None = None
    date: str | None = None
    sitelinks: dict[str, list[dict[str, str]]] | None = None


class SerpApiResponse(_StrictModel):
    search_metadata: SearchMetadata
    search_parameters: SearchParameters
    organic_results: list[OrganicResult]
    knowledge_graph: dict[str, object] | None = None
    related_questions: list[dict[str, object]] | None = None
    related_searches: list[dict[str, object]] | None = None
    pagination: dict[str, object] | None = None


def parse_serp_html(
    raw_html: str,
    *,
    query: str,
    country_code: str = "us",
    language_code: str = "en",
    start: int = 0,
    num: int = 10,
    device: str = "desktop",
) -> SerpApiResponse:
    created = datetime.now(UTC).isoformat()
    tree = LexborHTMLParser(raw_html)
    results: list[OrganicResult] = []
    containers = tree.css("div.MjjYud")
    if not containers:
        containers = tree.css("div[data-snhf]")

    for container in containers:
        heading = container.css_first("h3")
        link_node = container.css_first("a[href]")
        if heading is None or link_node is None:
            continue
        link = link_node.attributes.get("href") or ""
        if not link.startswith(("http://", "https://")):
            continue
        snippet_node = container.css_first(".VwiC3b") or container.css_first("[data-sncf]")
        displayed_node = container.css_first("cite")
        results.append(
            OrganicResult(
                position=len(results) + 1,
                title=heading.text(strip=True),
                link=link,
                displayed_link=displayed_node.text(strip=True) if displayed_node else "",
                snippet=snippet_node.text(strip=True) if snippet_node else "",
            )
        )
        if len(results) >= num:
            break

    return SerpApiResponse(
        search_metadata=SearchMetadata(
            id=str(uuid4()),
            status="Success",
            created_at=created,
            processed_at=datetime.now(UTC).isoformat(),
            total_time_taken=0.0,
            google_url="https://www.google.com/search",
        ),
        search_parameters=SearchParameters(
            q=query,
            gl=country_code,
            hl=language_code,
            start=start,
            num=num,
            device=device,
        ),
        organic_results=results,
        pagination={},
    )


__all__ = [
    "OrganicResult",
    "SearchMetadata",
    "SearchParameters",
    "SerpApiResponse",
    "parse_serp_html",
]
