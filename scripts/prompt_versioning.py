"""Quản lý prompt version day13-chat trên Langfuse.

Các lệnh:
    python scripts/prompt_versioning.py bootstrap   # tạo v1 với label baseline + production
    python scripts/prompt_versioning.py create-v2   # tạo v2 với label candidate
    python scripts/prompt_versioning.py promote     # chuyển label production sang v2
    python scripts/prompt_versioning.py rollback    # chuyển label production về v1
    python scripts/prompt_versioning.py status      # in version + labels hiện tại
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.prompt_management import DEFAULT_PROMPT_TEMPLATE

PROMPT_NAME = "day13-chat"

PROMPT_V2 = (
    "Feature={{feature}}\n"
    "Docs={{docs}}\n"
    "Question={{message}}\n"
    "Instruction: answer in 2 short sentences using only the docs."
)


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")

    parser = argparse.ArgumentParser(description="Quản lý prompt version trên Langfuse")
    parser.add_argument(
        "action",
        choices=["bootstrap", "create-v2", "promote", "rollback", "status"],
    )
    args = parser.parse_args()

    from langfuse import get_client

    client = get_client()

    if args.action == "bootstrap":
        prompt = client.create_prompt(
            name=PROMPT_NAME,
            prompt=DEFAULT_PROMPT_TEMPLATE,
            type="text",
            labels=["baseline", "production"],
            commit_message="v1 baseline",
        )
        print(f"Created {PROMPT_NAME} v{prompt.version} labels=[baseline, production]")
    elif args.action == "create-v2":
        prompt = client.create_prompt(
            name=PROMPT_NAME,
            prompt=PROMPT_V2,
            type="text",
            labels=["candidate"],
            commit_message="v2 candidate",
        )
        print(f"Created {PROMPT_NAME} v{prompt.version} labels=[candidate]")
    elif args.action == "promote":
        client.update_prompt(name=PROMPT_NAME, version=2, new_labels=["candidate", "production"])
        print(f"Promoted: label 'production' -> {PROMPT_NAME} v2")
    elif args.action == "rollback":
        client.update_prompt(name=PROMPT_NAME, version=1, new_labels=["baseline", "production"])
        print(f"Rolled back: label 'production' -> {PROMPT_NAME} v1")
    elif args.action == "status":
        version = 1
        while version <= 50:
            try:
                prompt = client.get_prompt(PROMPT_NAME, version=version, type="text")
            except Exception:
                break
            if prompt is None:
                break
            labels = sorted(getattr(prompt, "labels", []) or [])
            print(f"v{version}: labels={labels}")
            version += 1

    client.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
