"""从 jobs_enriched.xlsx 导出列名，保存为数据字典文本，并生成 HTML。"""

from __future__ import annotations

import html
import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd

SOURCE = Path(__file__).with_name("jobs_enriched.xlsx")
OUTPUT = Path(__file__).with_name("jobs_enriched_数据字典.txt")
HTML_OUTPUT = Path(__file__).with_name("jobs_enriched_数据字典.html")

# 字段说明按列名整理，用于数据字典中的 description。
FIELD_DESCRIPTIONS: dict[str, str] = {
    "source_row": "原始数据行号",
    "id": "记录 ID",
    "code": "岗位编码",
    "title": "岗位名称",
    "portal_type": "招聘门户类型编码",
    "portal_name": "招聘门户名称",
    "fetched_at": "数据抓取时间（原始值）",
    "publish_time": "发布时间（原始数值）",
    "category_id": "职类 ID",
    "category_name": "职类名称",
    "category_parent_name": "上级职类名称",
    "city_code": "城市编码",
    "city_name": "城市名称",
    "city_names": "城市名称列表",
    "recruit_type_id": "招聘类型 ID",
    "recruit_type_name": "招聘类型名称",
    "recruit_parent_name": "招聘类型上级名称",
    "job_subject_name": "岗位主体名称",
    "description": "岗位描述",
    "requirement": "任职要求",
    "address": "工作地址",
    "recruit_group": "招聘分组",
    "project_status": "项目状态",
    "analysis_category_l1": "分析用一级职类",
    "analysis_category_l2": "分析用二级职类",
    "category_mapping_status": "职类映射状态",
    "publish_datetime": "发布时间（日期时间）",
    "publish_date": "发布日期",
    "publish_month": "发布月份",
    "publish_time_status": "发布时间解析状态",
    "fetched_datetime": "抓取时间（日期时间）",
    "publish_year": "发布年份",
    "publish_quarter": "发布季度",
    "publish_day": "发布日",
    "publish_day_name": "发布星期",
    "publish_is_weekend": "是否周末发布",
    "publish_iso_year": "ISO 周年份",
    "publish_weekofyear": "年内周次",
    "publish_week_start": "当周起始日",
    "publish_dayofyear": "年内第几天",
    "publish_ten_day_period": "发布旬（上旬/中旬/下旬）",
    "address_province": "地址解析：省",
    "address_city": "地址解析：市",
    "address_district": "地址解析：区县",
    "address_township": "地址解析：乡镇",
    "address_adcode": "地址行政区划代码",
    "address_detail": "地址详细部分",
    "address_status": "地址解析状态",
    "address_parse_source": "地址解析来源",
    "address_candidate_codes": "地址候选区划代码",
    "address_data_version": "地址数据版本",
    "recruit_group_source": "招聘分组来源",
    "district_filled": "补齐后的区县",
    "district_fill_status": "区县补齐状态",
    "district_fill_adcode": "区县补齐行政区划代码",
    "district_fill_rule": "区县补齐规则",
    "district_evidence_id": "区县补齐证据岗位 ID",
    "district_evidence_source_row": "区县补齐证据源行号",
    "district_evidence_address": "区县补齐证据地址",
    "district_current": "当前区县",
    "city_raw": "原始城市文本",
    "city_standard": "标准化城市",
    "province": "省份",
    "country_or_region": "国家或地区",
    "geo_code": "地理编码",
    "city_mapping_status": "城市映射状态",
    "city_source": "城市字段来源",
    "recruit_city_standard": "招聘城市（标准名）",
    "recruit_province": "招聘省份",
    "recruit_country_or_region": "招聘国家或地区",
    "recruit_site_code": "招聘站点编码",
    "recruit_adcode": "招聘行政区划代码",
    "recruit_geo_code": "招聘地理编码",
    "recruit_city_source": "招聘城市来源",
    "recruit_city_status": "招聘城市状态",
    "岗位数": "该城市标准对应的岗位数",
    "组合数": "该城市标准对应的组合数",
    "行数": "记录行数",
    "证据岗位ID": "用于补齐的证据岗位 ID",
    "证据源行号": "证据记录的源行号",
    "证据地址": "证据记录的地址",
    "规则": "补齐所使用的规则",
    "区划版本": "行政区划数据版本",
    "复核类型": "待复核问题的类型",
    "标识": "复核对象标识",
    "名称": "复核对象名称",
    "去重数": "去重后的数量",
    "已有证据": "已收集到的证据",
    "候选": "候选取值",
    "冲突原因": "需要复核的冲突原因",
    "下一步": "建议的下一步处理",
    "项目": "缺失登记项目",
    "说明": "缺失情况说明",
}


def _example(series: pd.Series) -> str | None:
    non_null = series.dropna()
    if non_null.empty:
        return None
    value = non_null.iloc[0]
    if isinstance(value, pd.Timestamp):
        text = value.isoformat()
    elif isinstance(value, (datetime, date)):
        text = value.isoformat()
    elif isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value).replace("\n", " ").strip()
    if len(text) > 80:
        text = text[:77] + "..."
    return text


def build_dictionary(path: Path) -> dict:
    workbook = pd.ExcelFile(path)
    tables: dict[str, dict] = {}
    for sheet in workbook.sheet_names:
        frame = pd.read_excel(workbook, sheet_name=sheet)
        fields = []
        for ordinal, column in enumerate(frame.columns, start=1):
            series = frame[column]
            null_count = int(series.isna().sum())
            fields.append(
                {
                    "ordinal": ordinal,
                    "name": str(column),
                    "dtype": str(series.dtype),
                    "nullable": null_count > 0,
                    "non_null_count": int(series.notna().sum()),
                    "null_count": null_count,
                    "unique_count": int(series.nunique(dropna=True)),
                    "example": _example(series),
                    "description": FIELD_DESCRIPTIONS.get(str(column), ""),
                }
            )
        tables[sheet] = {
            "row_count": int(len(frame)),
            "column_count": int(len(frame.columns)),
            "columns": [str(column) for column in frame.columns],
            "fields": fields,
        }
    return {
        "source_file": path.name,
        "table_count": len(tables),
        "tables": tables,
    }


def _fmt_int(value: int) -> str:
    return f"{value:,}"


def _dtype_meta(dtype: str) -> tuple[str, str]:
    if dtype.startswith("datetime"):
        return "time", "时间"
    if dtype.startswith("int"):
        return "int", "整数"
    if dtype.startswith("float"):
        return "float", "小数"
    if dtype.startswith("bool"):
        return "bool", "布尔"
    return "text", "文本"


def _completeness(field: dict, row_count: int) -> float:
    if row_count <= 0:
        return 0.0
    return field["non_null_count"] / row_count * 100


def _meter_class(percent: float) -> str:
    if percent >= 99.95:
        return "full"
    if percent >= 90:
        return "partial"
    return "low"


def _field_search_text(field: dict) -> str:
    parts = [
        field["name"],
        field["description"],
        field["dtype"],
        field["example"] or "",
    ]
    return " ".join(parts).lower()


def render_html(dictionary: dict) -> str:
    tables = dictionary["tables"]
    field_total = sum(table["column_count"] for table in tables.values())
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    source_name = html.escape(dictionary["source_file"])

    nav_items = [
        '<a class="nav-link" href="#overview"><span>总览</span></a>'
    ]
    overview_cards = []
    sections = []

    for index, (name, table) in enumerate(tables.items(), start=1):
        anchor = f"sheet-{index}"
        escaped_name = html.escape(name)
        nav_items.append(
            f'<a class="nav-link" href="#{anchor}">'
            f"<span>{escaped_name}</span>"
            f'<small>{table["column_count"]}</small></a>'
        )
        overview_cards.append(
            f'<a class="overview-card" href="#{anchor}">'
            f'<span class="eyebrow">工作表 {index:02d}</span>'
            f"<strong>{escaped_name}</strong>"
            f'<span class="overview-meta">{_fmt_int(table["row_count"])} 行'
            f' · {table["column_count"]} 个字段</span></a>'
        )

        chips = []
        rows = []
        for field in table["fields"]:
            field_id = f'{anchor}-f{field["ordinal"]}'
            kind, kind_label = _dtype_meta(field["dtype"])
            percent = _completeness(field, table["row_count"])
            example = field["example"] if field["example"] else "—"
            description = field["description"] or "—"
            nullable = "可空" if field["nullable"] else "必填"
            nullable_class = "yes" if field["nullable"] else "no"
            search = html.escape(_field_search_text(field), quote=True)
            chips.append(
                f'<a class="chip" href="#{field_id}" data-nulls="{field["null_count"]}" '
                f'data-search="{search}"><span>{field["ordinal"]:02d}</span>'
                f"<code>{html.escape(field['name'])}</code></a>"
            )
            rows.append(
                "<tr "
                f'id="{field_id}" data-nulls="{field["null_count"]}" data-search="{search}">'
                f'<td class="num">{field["ordinal"]}</td>'
                f"<td><code>{html.escape(field['name'])}</code></td>"
                f"<td>{html.escape(description)}</td>"
                f'<td><span class="type type-{kind}">{kind_label}</span>'
                f'<span class="dtype">{html.escape(field["dtype"])}</span></td>'
                f'<td><span class="flag flag-{nullable_class}">{nullable}</span></td>'
                f'<td class="meter-cell"><span class="meter {_meter_class(percent)}" '
                f'style="--p:{percent:.1f}"><i></i></span>'
                f'<span class="pct">{percent:.1f}%</span></td>'
                f'<td class="num">{_fmt_int(field["non_null_count"])}</td>'
                f'<td class="num">{_fmt_int(field["null_count"])}</td>'
                f'<td class="num">{_fmt_int(field["unique_count"])}</td>'
                f'<td class="example">{html.escape(example)}</td>'
                "</tr>"
            )

        sections.append(
            f'<section class="sheet" id="{anchor}" data-total="{table["column_count"]}">'
            '<header class="sheet-head">'
            f'<div><p class="eyebrow">工作表 {index:02d}</p><h2>{escaped_name}</h2></div>'
            '<dl class="sheet-stats">'
            f'<div><dt>记录</dt><dd>{_fmt_int(table["row_count"])}</dd></div>'
            '<div><dt>显示字段</dt><dd><span class="shown">'
            f'{table["column_count"]}</span>'
            f'<span class="of"> / {table["column_count"]}</span></dd></div>'
            "</dl></header>"
            f'<div class="chips">{"".join(chips)}</div>'
            '<div class="table-wrap"><table>'
            "<thead><tr>"
            "<th>#</th><th>字段名</th><th>说明</th><th>类型</th><th>约束</th>"
            "<th>完整度</th><th>非空</th><th>缺失</th><th>唯一值</th><th>示例</th>"
            "</tr></thead>"
            f'<tbody>{"".join(rows)}</tbody></table></div></section>'
        )

    return _PAGE_TEMPLATE.replace("__SOURCE__", source_name).replace(
        "__GENERATED__", generated_at
    ).replace("__TABLE_COUNT__", str(dictionary["table_count"])).replace(
        "__FIELD_TOTAL__", str(field_total)
    ).replace("__NAV__", "\n".join(nav_items)).replace(
        "__OVERVIEW__", "\n".join(overview_cards)
    ).replace("__SECTIONS__", "\n".join(sections))


_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__SOURCE__ 数据字典</title>
  <style>
    :root {
      --bg: #f3efe6;
      --paper: #fffdf8;
      --ink: #1c1915;
      --muted: #6f675c;
      --line: #e5dccf;
      --accent: #0f6b58;
      --accent-soft: #e4f3ee;
      --cinnabar: #9d3b2c;
      --gold: #a97832;
      --sidebar: #17211e;
      --sidebar-muted: #b7c4bc;
      --shadow: 0 16px 40px rgba(42, 32, 20, 0.06);
    }
    * { box-sizing: border-box; }
    [hidden] { display: none !important; }
    html { scroll-behavior: smooth; }
    .sheet, tr, .overview-card { scroll-margin-top: calc(var(--toolbar-h, 76px) + 16px); }
    body {
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(1200px 500px at 100% -10%, rgba(157, 59, 44, 0.08), transparent 55%),
        var(--bg);
      font-family: "Avenir Next", "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", sans-serif;
      font-variant-numeric: tabular-nums;
    }
    a { color: inherit; text-decoration: none; }
    code {
      font-family: "SF Mono", "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace;
      font-size: 0.92em;
    }
    .sidebar {
      position: fixed;
      inset: 0 auto 0 0;
      width: 248px;
      padding: 28px 18px;
      background: var(--sidebar);
      color: #f4f7f5;
      display: flex;
      flex-direction: column;
      gap: 28px;
    }
    .brand { display: flex; gap: 12px; align-items: center; }
    .seal {
      width: 42px;
      height: 42px;
      display: grid;
      place-items: center;
      border: 1.5px solid rgba(244, 247, 245, 0.72);
      color: #f3d2cb;
      font-family: "Songti SC", "STSong", serif;
      font-size: 22px;
    }
    .brand strong { display: block; font-size: 16px; letter-spacing: 0.08em; }
    .brand em {
      display: block;
      margin-top: 2px;
      color: var(--sidebar-muted);
      font-style: normal;
      font-size: 12px;
    }
    .nav { display: flex; flex-direction: column; gap: 4px; }
    .nav-link {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 12px;
      border-radius: 10px;
      color: #d7e2dc;
    }
    .nav-link small {
      color: var(--sidebar-muted);
      font-size: 12px;
    }
    .nav-link:hover, .nav-link.active {
      background: rgba(255, 255, 255, 0.08);
      color: white;
    }
    .search-icon { display: grid; flex: none; color: var(--muted); }
    .sidebar footer {
      margin-top: auto;
      color: var(--sidebar-muted);
      font-size: 12px;
      line-height: 1.6;
    }
    .main { margin-left: 248px; padding: 28px 36px 72px; }
    .hero {
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-end;
      margin-bottom: 22px;
    }
    .kicker, .eyebrow {
      margin: 0 0 8px;
      color: var(--cinnabar);
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
    h1, h2 { margin: 0; font-weight: 600; letter-spacing: -0.03em; }
    h1 { font-size: 40px; font-family: "Iowan Old Style", "Palatino Linotype", "Songti SC", serif; }
    .lede { max-width: 640px; margin: 10px 0 0; color: var(--muted); line-height: 1.7; }
    .toolbar {
      position: sticky;
      top: 0;
      z-index: 4;
      display: flex;
      gap: 14px;
      align-items: center;
      margin: 0 -36px 22px;
      padding: 14px 36px;
      background: rgba(243, 239, 230, 0.9);
      backdrop-filter: blur(14px);
      border-bottom: 1px solid transparent;
    }
    .toolbar.stuck { border-bottom-color: var(--line); }
    .search {
      flex: 1;
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
      padding: 0 14px;
      height: 46px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--paper);
      box-shadow: var(--shadow);
    }
    .search input {
      width: 100%;
      border: 0;
      outline: none;
      background: transparent;
      color: var(--ink);
      font: inherit;
      font-size: 15px;
    }
    .toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      height: 46px;
      padding: 0 14px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--paper);
      color: var(--muted);
      white-space: nowrap;
    }
    .result-count { color: var(--muted); font-size: 13px; white-space: nowrap; }
    .overview {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 28px;
    }
    .overview-card {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 18px 18px 16px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--paper);
      box-shadow: var(--shadow);
    }
    .overview-card strong { font-size: 22px; }
    .overview-meta { color: var(--muted); font-size: 13px; }
    .overview-card:hover { border-color: #c9dcd5; transform: translateY(-1px); }
    .sheet {
      margin-top: 18px;
      padding: 22px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--paper);
      box-shadow: var(--shadow);
    }
    .sheet-head, .sheet-stats, .sheet-stats div {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-end;
    }
    .sheet-stats { margin: 0; }
    .sheet-stats div { flex-direction: column; align-items: flex-end; gap: 2px; }
    .sheet-stats dt { color: var(--muted); font-size: 12px; }
    .sheet-stats dd { margin: 0; font-size: 22px; }
    .of { color: var(--muted); font-size: 14px; }
    .chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 18px 0; }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 8px 6px 7px;
      border-radius: 999px;
      background: #f6f1e8;
      color: var(--ink);
      white-space: nowrap;
    }
    .chip span { color: var(--muted); font-size: 11px; }
    .chip:hover { background: var(--accent-soft); }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: separate; border-spacing: 0; min-width: 1120px; }
    th, td {
      padding: 11px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 13.5px;
    }
    td:nth-child(3) { min-width: 9.5em; }
    td:nth-child(4), td:nth-child(5) { white-space: nowrap; }
    th {
      background: #f7f1e8;
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.04em;
      white-space: nowrap;
    }
    tr:hover td { background: #fbf8f2; }
    .num { text-align: right; white-space: nowrap; }
    .example { max-width: 280px; color: #4d473f; word-break: break-all; }
    .type, .flag {
      display: inline-flex;
      align-items: center;
      height: 22px;
      padding: 0 8px;
      border-radius: 999px;
      font-size: 12px;
      white-space: nowrap;
    }
    .type-int { background: #e7f0ea; color: #0f6b58; }
    .type-float { background: #f3ead8; color: #8a5a12; }
    .type-time { background: #f8e7e3; color: #9d3b2c; }
    .type-text, .type-bool { background: #eeeae3; color: #514b43; }
    .dtype { display: block; margin-top: 4px; color: var(--muted); font-size: 11px; }
    .flag-no { background: var(--accent-soft); color: var(--accent); }
    .flag-yes { background: #f8efe4; color: var(--gold); }
    .meter-cell { white-space: nowrap; }
    .meter {
      display: inline-block;
      width: 72px;
      height: 6px;
      margin-right: 8px;
      border-radius: 99px;
      background: #efe7db;
      vertical-align: middle;
      overflow: hidden;
    }
    .meter i {
      display: block;
      height: 100%;
      width: calc(var(--p) * 1%);
      background: var(--cinnabar);
    }
    .meter.partial i { background: var(--gold); }
    .meter.full i { background: var(--accent); }
    .pct { color: var(--muted); font-size: 12px; }
    .empty {
      display: none;
      margin-top: 28px;
      padding: 28px;
      border: 1px dashed var(--line);
      border-radius: 18px;
      color: var(--muted);
      text-align: center;
      background: rgba(255, 253, 248, 0.7);
    }
    body.is-empty .empty { display: block; }
    @media (max-width: 980px) {
      .sidebar { position: static; width: auto; }
      .main { margin-left: 0; padding: 20px 16px 48px; }
      .nav { flex-direction: row; overflow-x: auto; }
      .nav-link { flex: 0 0 auto; white-space: nowrap; }
      .hero, .toolbar, .sheet-head { flex-direction: column; align-items: stretch; }
      .toolbar { margin: 0 -16px 18px; padding: 12px 16px; }
      .overview { grid-template-columns: 1fr; }
      .sidebar footer { display: none; }
    }
    @media print {
      .sidebar, .toolbar, .chips { display: none; }
      .main { margin: 0; }
      .sheet { break-inside: avoid; box-shadow: none; }
      th { position: static; }
    }
  </style>
</head>
<body>
  <aside class="sidebar">
    <div class="brand">
      <span class="seal">典</span>
      <div><strong>数据字典</strong><em>__SOURCE__</em></div>
    </div>
    <nav class="nav">__NAV__</nav>
    <footer>生成于 __GENERATED__<br>字段说明依据列名整理</footer>
  </aside>
  <main class="main">
    <header class="hero" id="overview">
      <div>
        <p class="kicker">Data Dictionary</p>
        <h1>岗位数据字典</h1>
        <p class="lede">来自 __SOURCE__，共 __TABLE_COUNT__ 张工作表、__FIELD_TOTAL__ 个字段。可按字段名、说明或示例筛选，也可只看存在缺失值的字段。</p>
      </div>
    </header>
    <div class="toolbar">
      <label class="search">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.25" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M10.4 10.4 13.2 13.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
        <input id="query" type="search" placeholder="搜索字段名、说明或示例" autocomplete="off">
      </label>
      <label class="toggle"><input id="only-missing" type="checkbox">只看有缺失</label>
      <div class="result-count" id="result-count">__FIELD_TOTAL__ / __FIELD_TOTAL__ 个字段</div>
    </div>
    <section class="overview">__OVERVIEW__</section>
    __SECTIONS__
    <p class="empty">没有符合当前筛选条件的字段。</p>
  </main>
  <script>
    const query = document.querySelector("#query");
    const onlyMissing = document.querySelector("#only-missing");
    const resultCount = document.querySelector("#result-count");
    const fieldTotal = __FIELD_TOTAL__;
    const toolbar = document.querySelector(".toolbar");

    function applyFilter() {
      const text = query.value.trim().toLowerCase();
      const missingOnly = onlyMissing.checked;
      let visible = 0;
      document.querySelectorAll(".sheet").forEach((section) => {
        let shown = 0;
        section.querySelectorAll("tbody tr, .chip").forEach((node) => {
          const haystack = node.dataset.search || "";
          const nulls = Number(node.dataset.nulls || 0);
          const matched = (!text || haystack.includes(text)) && (!missingOnly || nulls > 0);
          node.hidden = !matched;
          if (matched && node.matches("tr")) shown += 1;
        });
        section.hidden = shown === 0;
        const shownNode = section.querySelector(".shown");
        if (shownNode) shownNode.textContent = String(shown);
        visible += shown;
      });
      document.body.classList.toggle("is-empty", visible === 0);
      document.querySelector(".overview").hidden = Boolean(text || missingOnly);
      resultCount.textContent = visible + " / " + fieldTotal + " 个字段";
    }

    const syncToolbar = () => {
      document.documentElement.style.setProperty("--toolbar-h", toolbar.offsetHeight + "px");
    };
    syncToolbar();
    window.addEventListener("resize", syncToolbar);
    query.addEventListener("input", applyFilter);
    onlyMissing.addEventListener("change", applyFilter);
    document.addEventListener("keydown", (event) => {
      if (event.key === "/" && document.activeElement !== query) {
        event.preventDefault();
        query.focus();
      }
    });
    document.addEventListener("scroll", () => {
      toolbar.classList.toggle("stuck", window.scrollY > 12);
    }, { passive: true });

    const links = [...document.querySelectorAll(".nav-link")];
    const sections = [...document.querySelectorAll(".sheet, #overview")];
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const id = entry.target.id;
        links.forEach((link) => {
          link.classList.toggle("active", link.getAttribute("href") === "#" + id);
        });
      });
    }, { rootMargin: "-20% 0px -70% 0px" });
    sections.forEach((section) => observer.observe(section));
  </script>
</body>
</html>
"""


def main() -> None:
    dictionary = build_dictionary(SOURCE)
    text = json.dumps(dictionary, ensure_ascii=False, indent=2) + "\n"
    OUTPUT.write_text(text, encoding="utf-8")
    saved = json.loads(text)
    HTML_OUTPUT.write_text(render_html(saved), encoding="utf-8")
    print(f"已写入 {OUTPUT.name}")
    print(f"已写入 {HTML_OUTPUT.name}")
    for name, table in saved["tables"].items():
        print(f"  {name}: {table['column_count']} 列, {table['row_count']} 行")


if __name__ == "__main__":
    main()
