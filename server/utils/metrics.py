"""Prometheus counters and histograms for environment observability."""

from __future__ import annotations

from typing import Iterable, Tuple

try:
    from prometheus_client import (  # type: ignore[attr-defined]
        CONTENT_TYPE_LATEST,
        REGISTRY,
        Counter,
        Histogram,
        generate_latest,
    )
except ModuleNotFoundError:  # pragma: no cover - fallback for offline testing
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    _REGISTRY: list["_Metric"] = []


    def _format_labels(
        label_names: Iterable[str], values: Tuple[str, ...], extra: Iterable[Tuple[str, str]] = ()
    ) -> str:
        pairs = []
        pairs.extend(f'{name}="{value}"' for name, value in zip(label_names, values))
        pairs.extend(f'{name}="{value}"' for name, value in extra)
        if not pairs:
            return ""
        return "{" + ",".join(pairs) + "}"


    class _Metric:
        def __init__(self, name: str, description: str, labelnames: Iterable[str]) -> None:
            self.name = name
            self.description = description
            self.labelnames = tuple(labelnames)
            _REGISTRY.append(self)


    class _CounterChild:
        def __init__(self, metric: "_Counter", labels: Tuple[str, ...]) -> None:
            self._metric = metric
            self._labels = labels

        def inc(self, amount: float = 1.0) -> None:
            current = self._metric._samples.get(self._labels, 0.0)
            self._metric._samples[self._labels] = current + amount


    class _Counter(_Metric):
        def __init__(self, name: str, description: str, labelnames: Iterable[str]) -> None:
            super().__init__(name, description, labelnames)
            self._samples: dict[Tuple[str, ...], float] = {}

        def labels(self, **labels: str) -> _CounterChild:
            values = tuple(labels[name] for name in self.labelnames)
            return _CounterChild(self, values)

        def collect(self) -> Iterable[str]:
            lines = []
            for label_values, value in self._samples.items():
                label_str = _format_labels(self.labelnames, label_values)
                lines.append(f"{self.name}{label_str} {value}")
            return lines


    class _HistogramChild:
        def __init__(self, metric: "_Histogram", labels: Tuple[str, ...]) -> None:
            self._metric = metric
            self._labels = labels
            self._counts = [0] * len(metric._buckets)
            self._count = 0
            self._sum = 0.0

        def observe(self, value: float) -> None:
            self._count += 1
            self._sum += value
            for idx, boundary in enumerate(self._metric._buckets):
                if value <= boundary:
                    self._counts[idx] += 1

        def collect(self) -> Iterable[str]:
            lines = []
            for boundary, count in zip(self._metric._buckets, self._counts):
                lines.append(
                    f"{self._metric.name}_bucket"
                    f"{_format_labels(self._metric.labelnames, self._labels, (('le', str(boundary)),))} {count}"
                )
            lines.append(
                f"{self._metric.name}_bucket"
                f"{_format_labels(self._metric.labelnames, self._labels, (('le', '+Inf'),))} {self._count}"
            )
            lines.append(
                f"{self._metric.name}_count{_format_labels(self._metric.labelnames, self._labels)} {self._count}"
            )
            lines.append(
                f"{self._metric.name}_sum{_format_labels(self._metric.labelnames, self._labels)} {self._sum}"
            )
            return lines

    class _Histogram(_Metric):
        def __init__(
            self, name: str, description: str, labelnames: Iterable[str], buckets: Iterable[float]
        ) -> None:
            super().__init__(name, description, labelnames)
            self._buckets = tuple(buckets)
            self._samples: dict[Tuple[str, ...], _HistogramChild] = {}

        def labels(self, **labels: str) -> _HistogramChild:
            values = tuple(labels[name] for name in self.labelnames)
            if values not in self._samples:
                self._samples[values] = _HistogramChild(self, values)
            return self._samples[values]

        def collect(self) -> Iterable[str]:
            for child in self._samples.values():
                yield from child.collect()


    def generate_latest() -> bytes:
        lines = []
        for metric in _REGISTRY:
            if hasattr(metric, "collect"):
                lines.extend(metric.collect())
        return "\n".join(lines).encode("utf-8")


    Counter = _Counter
    Histogram = _Histogram


def _collector_name(name: str) -> str:
    """Normalize a metric name to the base collector key used by prometheus_client."""
    if name.endswith("_total"):
        return name[: -len("_total")]
    return name


def _get_or_create_metric(factory, name: str, description: str, labelnames: list[str], **kwargs):
    """Reuse an already-registered collector when the module is imported twice."""
    try:
        return factory(name, description, labelnames, **kwargs)
    except ValueError as exc:
        if "Duplicated timeseries" not in str(exc) or "REGISTRY" not in globals():
            raise
        existing = getattr(REGISTRY, "_names_to_collectors", {}).get(_collector_name(name))
        if existing is None:
            existing = getattr(REGISTRY, "_names_to_collectors", {}).get(name)
        if existing is None:
            raise
        return existing


episodes_total = _get_or_create_metric(
    Counter,
    "openenv_episodes_total",
    "Total number of episodes by domain/task and terminal status",
    ["domain", "task_id", "status"],
)

steps_total = _get_or_create_metric(
    Counter,
    "openenv_steps_total",
    "Total number of tool steps executed per domain/tool",
    ["domain", "tool_name"],
)

tool_errors_total = _get_or_create_metric(
    Counter,
    "openenv_tool_errors_total",
    "Total tool errors by domain/tool/error type",
    ["domain", "tool_name", "error_type"],
)

episode_duration = _get_or_create_metric(
    Histogram,
    "openenv_episode_duration_seconds",
    "Episode duration in seconds by domain",
    ["domain"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

grader_scores = _get_or_create_metric(
    Histogram,
    "openenv_grader_scores",
    "Grader score distribution by domain/task/difficulty",
    ["domain", "task_id", "difficulty"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)


def get_metrics_response() -> tuple[bytes, str]:
    """Return the latest metrics payload and the Prometheus content type."""
    return generate_latest(), CONTENT_TYPE_LATEST
