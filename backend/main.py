"""岗位季度分析 API。查询和聚合都在这里完成，供 Node 服务转发。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from analysis import (
    build_analysis,
    build_dataset,
    filter_records,
    read_frame,
    self_check,
)

DATASET: dict | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global DATASET
    today = date.today()
    frame = read_frame()
    DATASET = build_dataset(frame, today)
    self_check(frame, DATASET, today)
    print(
        "自检通过："
        f"{DATASET['source_rows']} 行，"
        f"{len(DATASET['categories'])} 个一级分类，"
        f"{sum(len(item['l2']) for item in DATASET['categories'])} 个二级分类，"
        f"{len(DATASET['quarters'])} 个季度，"
        f"进行中季度 {DATASET['ongoing_quarter']}"
    )
    yield


app = FastAPI(title="岗位季度分析", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def dataset() -> dict:
    if DATASET is None:
        raise HTTPException(status_code=503, detail="数据尚未加载完成")
    return DATASET


@app.get("/api/health")
def health():
    data = dataset()
    sample = next(
        item for item in data["categories"] if item["l1"] == "研发"
    )
    backend = sum(
        row["count"]
        for row in data["records"]
        if row["l1"] == "研发" and row["l2"] == "后端"
    )
    return {
        "ok": True,
        "rows": data["source_rows"],
        "pending_time_rows": data["pending_time_rows"],
        "categories": len(data["categories"]),
        "l2_count": sum(len(item["l2"]) for item in data["categories"]),
        "quarters": len(data["quarters"]),
        "ongoing_quarter": data["ongoing_quarter"],
        "sample": {"l1": "研发", "total": sample["total"], "后端": backend},
    }


@app.get("/api/meta")
def meta():
    data = dataset()
    return {
        "source": "jobs_enriched.xlsx",
        "sheet": "岗位主表",
        "rows": data["source_rows"],
        "pending_time_rows": data["pending_time_rows"],
        "categories": data["categories"],
        "quarters": data["quarters"],
        "ongoing_quarter": data["ongoing_quarter"],
        "notes": [
            "一条岗位计 1，统计表为岗位主表。",
            "与一级分类同名的二级分类单独保留，表示尚未再细分的岗位。",
            f"{data['ongoing_quarter']} 为进行中季度，数量只统计到当前已发布的岗位。",
            f"其中 {data['pending_time_rows']} 条岗位的发布时间标记为待复核，仍按已解析的发布季度计入。",
        ],
    }


@app.get("/api/analysis")
def analysis(
    l1: str = Query(..., description="一级分类"),
    start: str | None = Query(None, description="开始季度，如 2024Q1"),
    end: str | None = Query(None, description="结束季度，如 2026Q3"),
    focus: str | None = Query(None, description="排名和占比使用的季度"),
):
    try:
        return build_analysis(dataset(), l1=l1, start=start, end=end, focus=focus)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/records")
def records(
    l1: str | None = None,
    l2: str | None = None,
    start: str | None = None,
    end: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=200),
):
    try:
        rows = filter_records(dataset(), l1=l1, l2=l2, start=start, end=end)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    start_index = (page - 1) * page_size
    page_rows = rows[start_index : start_index + page_size]
    return {
        "items": [
            {**row, "key": f"{row['l1']}-{row['l2']}-{row['quarter_label']}"}
            for row in page_rows
        ],
        "total": len(rows),
        "page": page,
        "page_size": page_size,
    }
