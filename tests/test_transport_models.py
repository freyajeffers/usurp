from uuid import uuid4

import pytest
from pydantic import ValidationError

from usurp.transport import DeviceType, ProxyNode, ProxyProtocol, TransportRequest, TransportResult


def test_transport_request_defaults_and_strict_bounds() -> None:
    request = TransportRequest(query="quantum error correction")
    assert request.country_code == "us"
    assert request.device_type is DeviceType.DESKTOP

    with pytest.raises(ValidationError):
        TransportRequest(query="", num_results=10)
    with pytest.raises(ValidationError):
        TransportRequest(query="test", num_results=101)


def test_proxy_node_requires_uppercase_iso_region() -> None:
    node = ProxyNode(
        id=uuid4(),
        uri="https://proxy.example.test:443",
        protocol=ProxyProtocol.HTTPS,
        region="US",
    )
    assert node.is_active is True
    with pytest.raises(ValidationError):
        ProxyNode(
            id=uuid4(),
            uri="https://proxy.example.test:443",
            protocol=ProxyProtocol.HTTPS,
            region="us",
        )


def test_transport_result_serializes_contract() -> None:
    result = TransportResult(
        status_code=200,
        headers={"content-type": "text/html"},
        raw_html="<html>",
        response_time_ms=12.5,
    )
    payload = result.as_mapping()
    assert payload["status_code"] == 200
    assert payload["escalation_required"] is False
