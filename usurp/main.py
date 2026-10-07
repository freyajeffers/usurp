from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="usurp - SERP Extraction Engine (scaffold)")


class SearchQuery(BaseModel):
    q: str
    gl: str | None = "us"
    hl: str | None = "en"
    start: int | None = 0
    num: int | None = 10
    api_key: str | None = None


async def get_query(
    q: str | None = None,
    gl: str | None = "us",
    hl: str | None = "en",
    start: int = 0,
    num: int = 10,
    api_key: str | None = None,
) -> SearchQuery | None:
    if q is None:
        return None
    return SearchQuery(q=q, gl=gl, hl=hl, start=start, num=num, api_key=api_key)


@app.get("/search")
async def search(query: SearchQuery | None = Depends(get_query)) -> dict[str, object]:  # noqa: B008
    if query is None:
        raise HTTPException(status_code=400, detail="missing query parameters")
    # scaffold: return a strict SerpApi-like minimal response
    return {
        "search_metadata": {"query": query.q},
        "organic_results": [],
        "pagination": {},
    }
