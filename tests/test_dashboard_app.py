from pathlib import Path
import json
from datetime import datetime, timezone

import altair as alt
import pytest
import yaml

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def _expected_titles() -> list[str]:
    config = yaml.safe_load((REPO_ROOT / "config" / "dashboard.yaml").read_text(encoding="utf-8"))
    return [panel["title"] for panel in config["dashboard"]["panels"]]


def test_dashboard_app_renders_six_contract_panels(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOG_PATH", str(tmp_path / "missing.jsonl"))
    app = AppTest.from_file(str(REPO_ROOT / "scripts" / "dashboard_app.py"), default_timeout=60)
    app.run()

    assert not app.exception
    assert [header.value for header in app.subheader] == _expected_titles()
    assert "Time range" in app.caption[0].value
    assert "refresh" in app.caption[0].value


def test_dashboard_error_chart_counts_failed_requests(monkeypatch, tmp_path) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    records = [
        {"ts": timestamp, "event": event}
        for event in ("request_received", "request_received", "request_failed")
    ]
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text("\n".join(json.dumps(row) for row in records), encoding="utf-8")
    monkeypatch.setenv("LOG_PATH", str(log_path))
    rates = []
    original = alt.Chart.mark_line

    def capture(chart, *args, **kwargs):
        if "error_rate_pct" in chart.data:
            rates.extend(chart.data["error_rate_pct"].tolist())
        return original(chart, *args, **kwargs)

    monkeypatch.setattr(alt.Chart, "mark_line", capture)
    app = AppTest.from_file(str(REPO_ROOT / "scripts" / "dashboard_app.py"), default_timeout=60)
    app.run()
    assert not app.exception
    assert rates == [50.0]
    assert next(metric.value for metric in app.metric if metric.label == "Error rate") == "50.00 %"
