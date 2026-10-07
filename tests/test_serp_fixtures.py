from pathlib import Path

import pytest

from usurp.parser import parse_serp_html

FIXTURES = Path(__file__).parent / "fixtures" / "serp"


@pytest.mark.parametrize(
    ("fixture_name", "expected_title"),
    [
        ("organic.html", "Organic result"),
        ("featured-snippet.html", "Featured result"),
        ("knowledge-panel.html", "Python result"),
        ("mobile.html", "Mobile result"),
        ("pagination.html", "Paged result"),
    ],
)
def test_static_serp_fixtures_extract_results(fixture_name: str, expected_title: str) -> None:
    response = parse_serp_html(
        (FIXTURES / fixture_name).read_text(),
        query="fixture query",
    )

    assert response.organic_results[0].title == expected_title


def test_static_serp_fixtures_preserve_feature_fields() -> None:
    knowledge = parse_serp_html(
        (FIXTURES / "knowledge-panel.html").read_text(),
        query="python",
    )
    pagination = parse_serp_html(
        (FIXTURES / "pagination.html").read_text(),
        query="fixture query",
    )

    assert knowledge.knowledge_graph is not None
    assert knowledge.related_questions is not None
    assert pagination.pagination is not None
    assert "next" in pagination.pagination
