"""Generate a deterministic SaaS SFT dataset from expert trajectories."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from benchmarks.saas_sft_utils import DEFAULT_ENV_URL, generate_expert_dataset


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_ENV_URL)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument(
        "--output-dir",
        default="artifacts/datasets/saas_sft",
        help="Directory for generated JSONL and summary files.",
    )
    args = parser.parse_args()

    rows, summary = generate_expert_dataset(base_url=args.base_url, repeats=args.repeats)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset_path = output_dir / "train.jsonl"
    with dataset_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    summary_payload = {
        "recorded_at": _timestamp(),
        "dataset_path": str(dataset_path),
        **summary,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary_payload, indent=2))


if __name__ == "__main__":
    main()
