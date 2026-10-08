from usurp.providers import GoogleProgrammableSearchProvider
from usurp.transport import TransportRequest


def test_google_programmable_search_maps_official_items_to_serp_shape() -> None:
    response = GoogleProgrammableSearchProvider._to_serp_response(
        {
            "items": [
                {
                    "title": "Official result",
                    "link": "https://example.test",
                    "displayLink": "example.test",
                    "snippet": "Official snippet",
                }
            ]
        },
        TransportRequest(query="test"),
    )

    assert response.organic_results[0].title == "Official result"
    assert response.organic_results[0].snippet == "Official snippet"
