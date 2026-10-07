from usurp.parser import SerpApiResponse, parse_serp_html

HTML = """
<div id="search">
  <div class="MjjYud">
    <a href="https://example.com/one"><h3>First result</h3></a>
    <div class="VwiC3b">First snippet text.</div>
    <cite>example.com › one</cite>
  </div>
  <div class="MjjYud">
    <a href="https://example.com/two"><h3>Second result</h3></a>
    <div class="VwiC3b">Second snippet text.</div>
    <cite>example.com › two</cite>
  </div>
</div>
"""


def test_parser_extracts_ordered_organic_results() -> None:
    response = parse_serp_html(HTML, query="example query", country_code="us", language_code="en")

    assert isinstance(response, SerpApiResponse)
    assert [item.position for item in response.organic_results] == [1, 2]
    assert response.organic_results[0].title == "First result"
    assert response.organic_results[0].link == "https://example.com/one"
    assert response.organic_results[1].snippet == "Second snippet text."
    assert response.search_parameters.q == "example query"


def test_parser_returns_valid_empty_response_when_no_results_exist() -> None:
    response = parse_serp_html("<html><body>No results</body></html>", query="missing")

    assert response.organic_results == []
    assert response.search_metadata.status == "Success"
    assert set(response.model_dump()) >= {
        "search_metadata",
        "search_parameters",
        "organic_results",
        "pagination",
    }
