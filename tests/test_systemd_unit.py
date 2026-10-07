from pathlib import Path

UNIT_PATH = Path(__file__).parents[1] / "packaging" / "systemd" / "usurp.service"


def test_systemd_unit_declares_hardened_user_service() -> None:
    unit = UNIT_PATH.read_text()

    assert "[Unit]" in unit
    assert "[Service]" in unit
    assert "Type=exec" in unit
    assert "ExecStart=%h/Projects/usurp/.venv/bin/python -m uvicorn usurp.main:app" in unit
    assert "Restart=on-failure" in unit
    assert "RestartSec=5s" in unit
    assert "NoNewPrivileges=true" in unit
    assert "ProtectHome=read-only" in unit
    assert "PrivateTmp=true" in unit
    assert "ProtectSystem=strict" in unit
    assert "ReadWritePaths=%h/.cache/usurp" in unit
    assert "[Install]" in unit
    assert "WantedBy=default.target" in unit
