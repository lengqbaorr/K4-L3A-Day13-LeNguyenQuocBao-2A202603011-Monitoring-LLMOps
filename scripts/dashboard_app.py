"""Dashboard 6 panel cho lab Day 13 Monitoring & LLMOps.

Chạy từ thư mục gốc repo:

    streamlit run scripts/dashboard_app.py

Nguồn dữ liệu: data/logs.jsonl (đọc trực tiếp, không tổng hợp lại bằng tay).
Contract 6 panel lấy từ config/dashboard.yaml để tiêu đề, đơn vị, time range
và threshold luôn khớp khi chạy validate_dashboard.py.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = Path(os.getenv("LOG_PATH", str(REPO_ROOT / "data" / "logs.jsonl")))
CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"

st.set_page_config(page_title="Day 13 Monitoring & LLMOps", layout="wide")

CONFIG = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["dashboard"]
PANELS = {panel["id"]: panel for panel in CONFIG["panels"]}
TIME_RANGE_MINUTES = int(CONFIG["time_range_minutes"])
REFRESH_SECONDS = int(CONFIG["refresh_seconds"])

THRESHOLD_COLOR = "#d62728"


def load_logs() -> pd.DataFrame:
    if not LOG_PATH.exists():
        return pd.DataFrame()
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    if "ts" not in frame.columns:
        return pd.DataFrame()
    frame["ts"] = pd.to_datetime(frame["ts"], errors="coerce", utc=True)
    return frame.dropna(subset=["ts"])


def threshold_caption(panel_id: str, extra: str = "") -> str:
    threshold = PANELS[panel_id]["threshold"]
    unit = PANELS[panel_id]["unit"]
    operator = "≤" if threshold["operator"] == "lte" else "≥"
    caption = (
        f"Threshold: {threshold['aggregation']} {operator} {threshold['value']} {unit}"
        f" | nguồn: {PANELS[panel_id]['source']} | window: {TIME_RANGE_MINUTES} phút"
    )
    return f"{caption} | {extra}" if extra else caption


def timeline_chart(
    frame: pd.DataFrame,
    *,
    x: str,
    y: str,
    color: str | None = None,
    y_title: str,
    threshold: float | None = None,
    chart_type: str = "line",
) -> alt.Chart:
    encoding = {
        "x": alt.X(
            f"{x}:T",
            title="time (UTC)",
            axis=alt.Axis(labelAngle=-45, tickCount={"interval": "minute", "step": 5}),
        ),
        "y": alt.Y(f"{y}:Q", title=y_title),
    }
    if color is not None:
        encoding["color"] = alt.Color(f"{color}:N", title="series")
        encoding["detail"] = alt.Detail(f"{color}:N")
    if chart_type == "bar":
        if color is not None:
            encoding["opacity"] = alt.Opacity(f"{color}:N", legend=None)
        chart = alt.Chart(frame).mark_bar().encode(**encoding)
    else:
        chart = alt.Chart(frame).mark_line(strokeWidth=2).encode(**encoding)

    if threshold is not None:
        rule = (
            alt.Chart(pd.DataFrame({"limit": [threshold]}))
            .mark_rule(color=THRESHOLD_COLOR, strokeDash=[6, 4], strokeWidth=1.5)
            .encode(y=alt.Y("limit:Q"))
        )
        chart = chart + rule
    return chart.properties(height=260)


def minutes_frame(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["minute"] = frame["ts"].dt.floor("1min")
    return frame


@st.fragment(run_every=REFRESH_SECONDS)
def render_dashboard() -> None:
    now = pd.Timestamp.now(tz="UTC")
    cutoff = now - pd.Timedelta(minutes=TIME_RANGE_MINUTES)
    logs = load_logs()
    window = (
        logs[(logs["ts"] >= cutoff) & (logs["ts"] <= now)]
        if not logs.empty
        else pd.DataFrame(columns=["ts", "event"])
    )

    st.title("K4-L3A Day 13 Monitoring & LLMOps — 6 panel dashboard")
    st.caption(
        f"Time range: {cutoff.strftime('%Y-%m-%d %H:%M')} → {now.strftime('%Y-%m-%d %H:%M')} UTC "
        f"({TIME_RANGE_MINUTES} phút gần nhất) | refresh: {REFRESH_SECONDS}s | "
        f"nguồn: {LOG_PATH.name} | dòng dữ liệu trong window: {len(window)}"
    )

    received = window[window["event"] == "request_received"]
    failed = window[window["event"] == "request_failed"]
    sent = window[window["event"] == "response_sent"]

    latency_panel = PANELS["latency"]
    if len(sent):
        latency = minutes_frame(sent)
        grouped = latency.groupby("minute")["latency_ms"]
        latency_series = pd.DataFrame(
            {
                "p50": grouped.quantile(0.50),
                "p95": grouped.quantile(0.95),
                "p99": grouped.quantile(0.99),
            }
        ).join(
            latency.groupby("minute")["ttft_ms"].quantile(0.95).rename("ttft_p95")
        )
        latency_long = latency_series.reset_index().melt(
            "minute", var_name="series", value_name="ms"
        )
        latency_chart = timeline_chart(
            latency_long,
            x="minute",
            y="ms",
            color="series",
            y_title="ms",
            threshold=float(latency_panel["threshold"]["value"]),
        )
        p95 = grouped.quantile(0.95).max()
        ttft_p95 = latency["ttft_ms"].quantile(0.95)
        st.subheader(latency_panel["title"])
        st.altair_chart(latency_chart, width="stretch")
        st.caption(
            threshold_caption(
                "latency",
                f"p95 cao nhất trong window: {p95:.0f} ms | TTFT p95: {ttft_p95:.0f} ms",
            )
        )
    else:
        st.subheader(latency_panel["title"])
        st.info("Chưa có event response_sent trong window.")

    traffic_panel = PANELS["traffic"]
    if len(received):
        traffic = minutes_frame(received).groupby("minute").size().rename("requests_per_minute")
        traffic_frame = traffic.reset_index()
        traffic_chart = timeline_chart(
            traffic_frame,
            x="minute",
            y="requests_per_minute",
            y_title="requests/minute",
            threshold=float(traffic_panel["threshold"]["value"]),
            chart_type="bar",
        )
        st.subheader(traffic_panel["title"])
        st.altair_chart(traffic_chart, width="stretch")
        st.caption(
            threshold_caption(
                "traffic",
                f"tổng request: {len(received)} | trung bình {len(received) / TIME_RANGE_MINUTES:.1f} req/phút",
            )
        )
    else:
        st.subheader(traffic_panel["title"])
        st.info("Chưa có request_received trong window.")

    errors_panel = PANELS["errors"]
    st.subheader(errors_panel["title"])
    if len(received):
        requests_per_minute = minutes_frame(received).groupby("minute").size()
        error_rate = (
            minutes_frame(failed).groupby("minute").size()
            .reindex(requests_per_minute.index, fill_value=0)
            .div(requests_per_minute)
            .mul(100).rename("error_rate_pct")
        )
        error_chart = timeline_chart(
            error_rate.reset_index(),
            x="minute",
            y="error_rate_pct",
            y_title="percent",
            threshold=float(errors_panel["threshold"]["value"]),
        )
        st.altair_chart(error_chart, width="stretch")
        error_rate_pct = 100 * len(failed) / len(received)
        retrieval_base = (
            window[window["tool_success"].notna()]
            if "tool_success" in window.columns
            else pd.DataFrame()
        )
        if len(retrieval_base):
            retrieval_pct = 100 * (retrieval_base["tool_success"] == True).sum() / len(retrieval_base)  # noqa: E712
        else:
            retrieval_pct = float("nan")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Error rate", f"{error_rate_pct:.2f} %")
        col_b.metric("Retrieval success", f"{retrieval_pct:.1f} %")
        failed_types = failed["error_type"] if "error_type" in failed.columns else pd.Series(dtype=object)
        breakdown = ", ".join(
            f"{name}: {count}" for name, count in failed_types.value_counts().items()
        ) or "không có lỗi"
        col_c.metric("Error breakdown", breakdown)
        st.caption(threshold_caption("errors", "error rate tính trên request_received"))
    else:
        st.info("Chưa có request_received trong window.")

    cost_panel = PANELS["cost"]
    st.subheader(cost_panel["title"])
    if len(sent):
        cost = minutes_frame(sent).groupby("minute")["cost_usd"].sum().rename("usd").reset_index()
        cost_chart = timeline_chart(
            cost, x="minute", y="usd", y_title="USD/minute", chart_type="bar"
        )
        st.altair_chart(cost_chart, width="stretch")
        total_cost = float(sent["cost_usd"].sum())
        col_a, col_b = st.columns(2)
        col_a.metric("Tổng cost trong window", f"{total_cost:.4f} USD")
        limit = float(cost_panel["threshold"]["value"])
        col_b.metric("Ngưỡng tổng", f"{limit:.1f} USD", delta=f"còn {limit - total_cost:.4f} USD")
        st.caption(threshold_caption("cost", f"trung bình {total_cost / max(len(sent), 1):.4f} USD/request"))
    else:
        st.info("Chưa có response_sent trong window.")

    tokens_panel = PANELS["tokens"]
    st.subheader(tokens_panel["title"])
    if len(sent):
        token_frame = minutes_frame(sent).groupby("minute")[["tokens_in", "tokens_out"]].sum().reset_index()
        token_long = token_frame.melt("minute", var_name="series", value_name="tokens")
        token_chart = timeline_chart(
            token_long, x="minute", y="tokens", color="series", y_title="tokens/minute"
        )
        st.altair_chart(token_chart, width="stretch")
        tokens_in = int(sent["tokens_in"].sum())
        tokens_out = int(sent["tokens_out"].sum())
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("tokens_in", f"{tokens_in:,}")
        col_b.metric("tokens_out", f"{tokens_out:,}")
        col_c.metric("Ngưỡng tổng", f"{int(tokens_panel['threshold']['value']):,} tokens")
        st.caption(threshold_caption("tokens"))
    else:
        st.info("Chưa có response_sent trong window.")

    quality_panel = PANELS["quality"]
    st.subheader(quality_panel["title"])
    if len(sent):
        quality = minutes_frame(sent).groupby("minute")["quality_score"].mean().rename("quality").reset_index()
        quality_chart = timeline_chart(
            quality,
            x="minute",
            y="quality",
            y_title="score (0–1)",
            threshold=float(quality_panel["threshold"]["value"]),
        )
        st.altair_chart(quality_chart, width="stretch")
        st.caption(
            threshold_caption(
                "quality",
                f"mean trong window: {sent['quality_score'].mean():.2f} | mẫu: {len(sent)} response",
            )
        )
    else:
        st.info("Chưa có response_sent trong window.")


render_dashboard()
