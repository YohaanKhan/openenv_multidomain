from pathlib import Path

from benchmarks.compare_benchmark_summaries import _load_summary


def test_load_summary_extracts_primary_aggregate(tmp_path: Path):
    path = tmp_path / "summary.json"
    path.write_text(
        """
{
  "primary": {
    "aggregate": {
      "model": "qwen2.5:1.5b",
      "mean_average_score": 0.4
    }
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    payload = _load_summary(str(path))

    assert payload["model"] == "qwen2.5:1.5b"
    assert payload["mean_average_score"] == 0.4
