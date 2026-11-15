"""按一级分类、二级分类和发布季度汇总岗位数，并计算相邻季度变化。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXCEL_PATH = ROOT / "jobs_enriched.xlsx"
SHEET = "岗位主表"


def quarter_index(year: int, quarter: int) -> int:
    return year * 4 + quarter


def quarter_label(year: int, quarter: int) -> str:
    return f"{year}Q{quarter}"


def parse_quarter(value: str) -> tuple[int, int]:
    text = value.strip().upper()
    year_text, quarter_text = text.split("Q", 1)
    year, quarter = int(year_text), int(quarter_text)
    if quarter not in (1, 2, 3, 4):
        raise ValueError(f"无效季度: {value}")
    return year, quarter


def current_quarter(today: date | None = None) -> tuple[int, int]:
    today = today or date.today()
    return today.year, (today.month - 1) // 3 + 1


def iter_quarters(start: tuple[int, int], end: tuple[int, int]):
    year, quarter = start
    while (year, quarter) <= end:
        yield year, quarter
        quarter += 1
        if quarter == 5:
            year += 1
            quarter = 1


def _change(previous: int | None, count: int) -> tuple[int | None, float | None]:
    if previous is None:
        return None, None
    delta = count - previous
    if previous == 0 and count == 0:
        return 0, 0.0
    if previous == 0:
        return delta, None
    return delta, round(delta / previous, 6)


def read_frame(path: Path = EXCEL_PATH) -> pd.DataFrame:
    frame = pd.read_excel(
        path,
        sheet_name=SHEET,
        usecols=[
            "analysis_category_l1",
            "analysis_category_l2",
            "publish_year",
            "publish_quarter",
            "publish_time_status",
        ],
    )
    frame = frame.rename(
        columns={
            "analysis_category_l1": "l1",
            "analysis_category_l2": "l2",
            "publish_year": "year",
            "publish_quarter": "quarter",
        }
    )
    frame["l1"] = frame["l1"].fillna("未分类").astype(str)
    frame["l2"] = frame["l2"].fillna("未分类").astype(str)
    frame["year"] = frame["year"].astype(int)
    frame["quarter"] = frame["quarter"].astype(int)
    frame["publish_time_status"] = frame["publish_time_status"].fillna("").astype(str)
    return frame


def build_dataset(frame: pd.DataFrame, today: date | None = None) -> dict:
    today = today or date.today()
    grouped = (
        frame.groupby(["l1", "l2", "year", "quarter"], dropna=False)
        .size()
        .rename("count")
        .reset_index()
    )
    l1_totals = frame.groupby("l1").size().sort_values(ascending=False)
    l2_totals = frame.groupby(["l1", "l2"]).size()
    categories = []
    for l1, total in l1_totals.items():
        order = l2_totals.loc[l1].sort_values(ascending=False)
        categories.append(
            {
                "l1": str(l1),
                "total": int(total),
                "l2": [str(name) for name in order.index],
            }
        )

    earliest = frame.sort_values(["year", "quarter"]).iloc[0]
    latest = frame.sort_values(["year", "quarter"]).iloc[-1]
    start = (int(earliest["year"]), int(earliest["quarter"]))
    end = (int(latest["year"]), int(latest["quarter"]))
    quarters = list(iter_quarters(start, end))
    calendar = current_quarter(today)
    ongoing = quarter_label(*calendar) if start <= calendar <= end else None

    counts = {
        (row.l1, row.l2, int(row.year), int(row.quarter)): int(row.count)
        for row in grouped.itertuples(index=False)
    }
    records = []
    for category in categories:
        l1 = category["l1"]
        for l2 in category["l2"]:
            previous = None
            for year, quarter in quarters:
                count = counts.get((l1, l2, year, quarter), 0)
                delta, rate = _change(previous, count)
                label = quarter_label(year, quarter)
                records.append(
                    {
                        "l1": l1,
                        "l2": l2,
                        "year": year,
                        "quarter": quarter,
                        "quarter_label": label,
                        "count": count,
                        "prev_count": previous,
                        "delta": delta,
                        "rate": rate,
                        "ongoing": label == ongoing,
                    }
                )
                previous = count

    quarter_meta = [
        {
            "year": year,
            "quarter": quarter,
            "label": quarter_label(year, quarter),
            "ongoing": quarter_label(year, quarter) == ongoing,
        }
        for year, quarter in quarters
    ]
    return {
        "source_rows": int(len(frame)),
        "pending_time_rows": int((frame["publish_time_status"] != "有效").sum()),
        "categories": categories,
        "quarters": quarter_meta,
        "ongoing_quarter": ongoing,
        "records": records,
    }


def self_check(frame: pd.DataFrame, dataset: dict, today: date | None = None) -> None:
    raw = frame.groupby(["l1", "l2", "year", "quarter"]).size()
    lookup = {
        (row["l1"], row["l2"], row["year"], row["quarter"]): row
        for row in dataset["records"]
    }
    if sum(row["count"] for row in dataset["records"]) != len(frame):
        raise AssertionError("补零后的岗位数合计与原始行数不一致")
    for key, count in raw.items():
        row = lookup.get((str(key[0]), str(key[1]), int(key[2]), int(key[3])))
        if row is None or row["count"] != int(count):
            raise AssertionError(f"汇总与原始分组不一致: {key}")
    same_name = lookup.get(("研发", "研发", 2025, 1))
    if same_name is None:
        raise AssertionError("与一级同名的二级分类没有单独保留")
    backend = [row for row in dataset["records"] if row["l1"] == "研发" and row["l2"] == "后端"]
    if sum(row["count"] for row in backend) != int(
        ((frame["l1"] == "研发") & (frame["l2"] == "后端")).sum()
    ):
        raise AssertionError("研发/后端合计不正确")
    for previous, current in zip(backend, backend[1:]):
        if current["prev_count"] != previous["count"]:
            raise AssertionError("环比上一季没有按日历季度衔接")
        if current["delta"] != current["count"] - previous["count"]:
            raise AssertionError("环比增减计算不正确")
    expected_ongoing = quarter_label(*current_quarter(today or date.today()))
    if dataset["ongoing_quarter"] != expected_ongoing:
        raise AssertionError(
            f"进行中季度应为 {expected_ongoing}，实际为 {dataset['ongoing_quarter']}"
        )
    if not any(row["ongoing"] and row["quarter_label"] == expected_ongoing for row in dataset["records"]):
        raise AssertionError(f"{expected_ongoing} 没有标记为进行中")
    earliest = frame.sort_values(["year", "quarter"]).iloc[0]
    latest = frame.sort_values(["year", "quarter"]).iloc[-1]
    expected_quarters = (
        quarter_index(int(latest["year"]), int(latest["quarter"]))
        - quarter_index(int(earliest["year"]), int(earliest["quarter"]))
        + 1
    )
    if len(dataset["quarters"]) != expected_quarters:
        raise AssertionError("季度序列长度不正确")


def _in_range(row: dict, start: tuple[int, int] | None, end: tuple[int, int] | None) -> bool:
    key = (row["year"], row["quarter"])
    if start and key < start:
        return False
    if end and key > end:
        return False
    return True


def filter_records(
    dataset: dict,
    l1: str | None = None,
    l2: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> list[dict]:
    start_key = parse_quarter(start) if start else None
    end_key = parse_quarter(end) if end else None
    if start_key and end_key and start_key > end_key:
        raise ValueError("开始季度晚于结束季度")
    rows = [
        row
        for row in dataset["records"]
        if (not l1 or row["l1"] == l1)
        and (not l2 or row["l2"] == l2)
        and _in_range(row, start_key, end_key)
    ]
    rows.sort(key=lambda row: (-row["year"], -row["quarter"], row["l1"], row["l2"]))
    return rows


def _latest_complete(rows: list[dict]) -> dict | None:
    complete = [row for row in rows if not row["ongoing"]]
    if not complete:
        return None
    return max(complete, key=lambda row: (row["year"], row["quarter"]))


def build_analysis(
    dataset: dict,
    l1: str,
    start: str | None = None,
    end: str | None = None,
    focus: str | None = None,
) -> dict:
    known = {item["l1"] for item in dataset["categories"]}
    if l1 not in known:
        raise ValueError(f"未知一级分类: {l1}")
    scoped = filter_records(dataset, l1=l1, start=start, end=end)
    if not scoped:
        raise ValueError("所选区间没有季度")

    l2_names = next(item["l2"] for item in dataset["categories"] if item["l1"] == l1)
    quarter_order = []
    for row in sorted(scoped, key=lambda item: (item["year"], item["quarter"])):
        if row["quarter_label"] not in quarter_order:
            quarter_order.append(row["quarter_label"])

    trend = [
        {
            "quarter": row["quarter_label"],
            "l2": row["l2"],
            "count": row["count"],
            "delta": row["delta"],
            "rate": row["rate"],
            "ongoing": row["ongoing"],
        }
        for row in sorted(scoped, key=lambda item: (item["year"], item["quarter"], l2_names.index(item["l2"])))
    ]
    quarter_totals = []
    for label in quarter_order:
        points = [item for item in trend if item["quarter"] == label]
        quarter_totals.append(
            {
                "quarter": label,
                "count": sum(item["count"] for item in points),
                "ongoing": points[0]["ongoing"],
            }
        )

    focus_label = focus or (
        _latest_complete(scoped)["quarter_label"]
        if _latest_complete(scoped)
        else quarter_order[-1]
    )
    if focus_label not in quarter_order:
        focus_label = quarter_order[-1]
    ranking_rows = [row for row in scoped if row["quarter_label"] == focus_label]
    focus_total = sum(row["count"] for row in ranking_rows)
    ranking = [
        {
            "l2": row["l2"],
            "count": row["count"],
            "share": round(row["count"] / focus_total, 6) if focus_total else 0,
            "delta": row["delta"],
            "rate": row["rate"],
            "prev_count": row["prev_count"],
        }
        for row in sorted(ranking_rows, key=lambda item: (-item["count"], item["l2"]))
    ]

    all_time = [row for row in dataset["records"] if row["l1"] == l1]
    all_quarters = sorted({(row["year"], row["quarter"], row["quarter_label"], row["ongoing"]) for row in all_time})
    complete_labels = [item[2] for item in all_quarters if not item[3]]
    latest_complete = complete_labels[-1] if complete_labels else None
    previous_complete = complete_labels[-2] if len(complete_labels) >= 2 else None

    def total_of(label: str | None) -> int | None:
        if label is None:
            return None
        return sum(row["count"] for row in all_time if row["quarter_label"] == label)

    latest_count = total_of(latest_complete)
    previous_count = total_of(previous_complete)
    qoq_delta, qoq_rate = _change(previous_count, latest_count or 0) if latest_count is not None else (None, None)
    if previous_count is None:
        qoq_delta, qoq_rate = None, None

    return {
        "l1": l1,
        "start": quarter_order[0],
        "end": quarter_order[-1],
        "focus": focus_label,
        "ongoing_quarter": dataset["ongoing_quarter"],
        "l2_names": l2_names,
        "summary": {
            "total_all_time": sum(row["count"] for row in all_time),
            "total_in_range": sum(item["count"] for item in quarter_totals),
            "l2_count": len(l2_names),
            "latest_complete_quarter": latest_complete,
            "latest_complete_count": latest_count,
            "previous_complete_quarter": previous_complete,
            "previous_complete_count": previous_count,
            "qoq_delta": qoq_delta,
            "qoq_rate": qoq_rate,
        },
        "trend": trend,
        "quarter_totals": quarter_totals,
        "ranking": ranking,
    }
