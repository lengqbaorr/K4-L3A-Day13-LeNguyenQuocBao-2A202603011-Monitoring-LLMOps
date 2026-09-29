"""Liệt kê trace trên Langfuse kèm correlation_id, prompt version, token và cost.

Ví dụ:
    python scripts/inspect_traces.py
    python scripts/inspect_traces.py --min-traces 10
    python scripts/inspect_traces.py --correlation-id req-12345678
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

FIELDS = "core,basic,io,metadata,model,usage,prompt,metrics,trace_context"


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")

    parser = argparse.ArgumentParser(description="Kiểm tra trace Langfuse của lab Day 13")
    parser.add_argument("--since-minutes", type=int, default=120)
    parser.add_argument("--min-traces", type=int, default=0)
    parser.add_argument("--correlation-id", default=None)
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    try:
        from langfuse import get_client
    except ImportError:  # pragma: no cover
        print("langfuse SDK chưa được cài")
        return 1

    client = get_client()
    now = datetime.now(timezone.utc)
    page = client.api.observations.get_many(
        from_start_time=now - timedelta(minutes=args.since_minutes),
        to_start_time=now + timedelta(minutes=5),
        limit=args.limit,
        fields=FIELDS,
    )

    traces: dict[str, dict] = {}
    for observation in page.data:
        data = observation.model_dump()
        entry = traces.setdefault(
            data.get("trace_id"),
            {
                "spans": set(),
                "correlation_id": None,
                "prompt_name": None,
                "prompt_label": None,
                "prompt_version": None,
                "prompt_source": None,
                "model": None,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "start": data.get("start_time"),
            },
        )
        entry["spans"].add(data.get("type"))
        metadata = data.get("metadata") or {}
        entry["correlation_id"] = entry["correlation_id"] or metadata.get("correlation_id")
        entry["prompt_name"] = entry["prompt_name"] or metadata.get("prompt_name")
        entry["prompt_label"] = entry["prompt_label"] or metadata.get("prompt_label")
        entry["prompt_version"] = entry["prompt_version"] or metadata.get("prompt_version")
        entry["prompt_source"] = entry["prompt_source"] or metadata.get("prompt_source")
        usage = data.get("usage_details") or {}
        cost = data.get("cost_details") or {}
        if data.get("type") == "GENERATION":
            entry["model"] = data.get("model")
            entry["tokens_in"] = usage.get("input", 0)
            entry["tokens_out"] = usage.get("output", 0)
            entry["cost_usd"] = cost.get("total_cost", 0.0)

    rows = sorted(traces.items(), key=lambda item: item[1]["start"] or datetime.min.replace(tzinfo=timezone.utc))
    if args.correlation_id:
        rows = [row for row in rows if row[1]["correlation_id"] == args.correlation_id]

    print(f"Trace tìm thấy: {len(rows)} (trong {args.since_minutes} phút gần nhất)")
    print(
        f"{'trace_id':34} {'correlation_id':16} {'prompt':26} {'model':20} "
        f"{'tok_in':>7} {'tok_out':>8} {'cost_usd':>10} spans"
    )
    for trace_id, info in rows:
        prompt = f"{info['prompt_name']}@{info['prompt_version']}[{info['prompt_label']}]"
        if info["prompt_source"] and info["prompt_source"] != "langfuse":
            prompt += f"({info['prompt_source']})"
        print(
            f"{str(trace_id)[:33]:34} {str(info['correlation_id'] or '-'):16} {prompt:26} "
            f"{str(info['model'] or '-'):20} {info['tokens_in']:>7} {info['tokens_out']:>8} "
            f"{info['cost_usd']:>10.6f} {','.join(sorted(s for s in info['spans'] if s))}"
        )

    complete = [
        info
        for _, info in rows
        if {"AGENT", "RETRIEVER", "GENERATION"}.issubset(info["spans"])
    ]
    print(f"Trace đủ root + retrieval + generation: {len(complete)}")

    if args.min_traces and len(rows) < args.min_traces:
        print(f"KHÔNG ĐẠT: cần tối thiểu {args.min_traces} trace")
        return 1
    if not rows:
        print("KHÔNG ĐẠT: chưa có trace nào")
        return 1
    print("ĐẠT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
