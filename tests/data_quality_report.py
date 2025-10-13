import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

FIXTURES_DIR = Path(__file__).parent / "fixtures"
OUTPUT_MD = Path(__file__).parents[1] / "docs" / "generated" / "sample_data_report.md"

CUMULATIVE_HINTS = {
    "total_energy",
    "total_feed_in",
    "total_discharge",
    "total_charged",
    "total_house_energy",
    "supply_from_grid",
    "energy_from_pv",
}

@dataclass
class SeriesStats:
    name: str
    count: int
    start: Optional[datetime]
    end: Optional[datetime]
    duration_hours: float
    median_interval_seconds: Optional[float]
    large_gaps: List[Tuple[datetime, datetime, float]]
    non_monotonic_count: int
    min_value: Optional[float]
    max_value: Optional[float]

def parse_timestamp(ts: str) -> Optional[datetime]:
    ts = ts.strip()
    if not ts:
        return None
    for try_ts in (ts.replace("Z", "+00:00"), ts):
        try:
            return datetime.fromisoformat(try_ts)
        except Exception:
            continue
    return None

def median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2

def is_cumulative(name: str) -> bool:
    low = name.lower()
    return any(h in low for h in CUMULATIVE_HINTS)

def load_csv_series(path: Path):
    times: List[datetime] = []
    values: List[float] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "timestamp" in (reader.fieldnames or []) and "value" in (reader.fieldnames or []):
            for row in reader:
                t = parse_timestamp(row["timestamp"])
                try:
                    v = float(str(row["value"]).strip())
                except Exception:
                    continue
                if t is not None:
                    times.append(t)
                    values.append(v)
        else:
            headers = reader.fieldnames or []
            if len(headers) >= 2:
                tcol, vcol = headers[0], headers[1]
                for row in reader:
                    t = parse_timestamp(row.get(tcol, ""))
                    try:
                        v = float(str(row.get(vcol, "")).strip())
                    except Exception:
                        continue
                    if t is not None:
                        times.append(t)
                        values.append(v)
    pairs = sorted(zip(times, values), key=lambda x: x[0])
    dedup = []
    seen = set()
    for t, v in pairs:
        key = (t.isoformat(), v)
        if key in seen:
            continue
        seen.add(key)
        dedup.append((t, v))
    t_sorted = [t for t, _ in dedup]
    v_sorted = [v for _, v in dedup]
    return t_sorted, v_sorted

def analyze_series(name: str, times: List[datetime], values: List[float]) -> SeriesStats:
    if not times:
        return SeriesStats(name, 0, None, None, 0.0, None, [], 0, None, None)
    start, end = times[0], times[-1]
    duration_hours = (end - start).total_seconds() / 3600.0
    intervals = [(t2 - t1).total_seconds() for t1, t2 in zip(times[:-1], times[1:])]
    med_int = median(intervals) if intervals else None

    gap_threshold = max(3600.0, 3 * med_int) if med_int else 3600.0
    large_gaps: List[Tuple[datetime, datetime, float]] = []
    for t1, t2, dt in zip(times[:-1], times[1:], intervals):
        if dt >= gap_threshold:
            large_gaps.append((t1, t2, dt))

    non_mono = 0
    if is_cumulative(name):
        for v1, v2 in zip(values[:-1], values[1:]):
            if v2 < v1:
                non_mono += 1

    return SeriesStats(
        name=name,
        count=len(times),
        start=start,
        end=end,
        duration_hours=duration_hours,
        median_interval_seconds=med_int,
        large_gaps=large_gaps,
        non_monotonic_count=non_mono,
        min_value=min(values) if values else None,
        max_value=max(values) if values else None,
    )

def summarize_windows(times: List[datetime], gap_threshold: float):
    if not times:
        return []
    windows = []
    w_start = times[0]
    prev = times[0]
    for t in times[1:]:
        dt = (t - prev).total_seconds()
        if dt >= gap_threshold:
            windows.append((w_start, prev, (prev - w_start).total_seconds()))
            w_start = t
        prev = t
    windows.append((w_start, prev, (prev - w_start).total_seconds()))
    windows.sort(key=lambda x: x[2], reverse=True)
    return windows[:3]

def main():
    files = sorted([p for p in FIXTURES_DIR.glob("*.*") if p.suffix.lower() in {".csv", ".yaml"}])
    lines = []
    lines.append("# Sample Data Report\n")
    lines.append(f"Scanned directory: {FIXTURES_DIR}\n\n")

    for path in files:
        if path.suffix.lower() == ".yaml":
            lines.append(f"## {path.name}\n- YAML detected (prices today/tomorrow). Not analyzed as a series.\n\n")
            continue

        times, values = load_csv_series(path)
        s = analyze_series(path.name, times, values)
        lines.append(f"## {s.name}\n")
        lines.append(f"- Points: {s.count}\n")
        if s.start and s.end:
            lines.append(f"- Coverage: {s.start} → {s.end} ({s.duration_hours:.2f} h)\n")
        if s.median_interval_seconds is not None:
            lines.append(f"- Median interval: {s.median_interval_seconds:.0f} s\n")
        lines.append(f"- Non-monotonic segments: {s.non_monotonic_count}\n")
        if s.large_gaps:
            lines.append(f"- Large gaps (≥ max(1h, 3×median)): {len(s.large_gaps)}\n")
            for (t1, t2, dt) in sorted(s.large_gaps, key=lambda g: g[2], reverse=True)[:3]:
                lines.append(f"  - Gap: {t1} → {t2} ({dt/3600:.2f} h)\n")
        else:
            lines.append("- Large gaps: 0\n")
        if s.median_interval_seconds is not None and s.start and s.end:
            gap_threshold = max(3600.0, 3 * s.median_interval_seconds)
            wins = summarize_windows(times, gap_threshold)
            if wins:
                lines.append("- Suggested validation windows (top 3 continuous):\n")
                for w_start, w_end, secs in wins:
                    lines.append(f"  - {w_start} → {w_end} ({secs/3600:.2f} h)\n")
        lines.append("\n")

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote report to: {OUTPUT_MD}")

if __name__ == "__main__":
    main()
