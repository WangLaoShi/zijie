async function request(path) {
  const response = await fetch(path);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "请求失败");
  }
  return payload;
}

export function fetchMeta() {
  return request("/api/meta");
}

export function fetchAnalysis(params) {
  const query = new URLSearchParams();
  query.set("l1", params.l1);
  if (params.start) query.set("start", params.start);
  if (params.end) query.set("end", params.end);
  if (params.focus) query.set("focus", params.focus);
  return request(`/api/analysis?${query.toString()}`);
}

export function fetchRecords(params) {
  const query = new URLSearchParams();
  ["l1", "l2", "start", "end"].forEach((key) => {
    if (params[key]) query.set(key, params[key]);
  });
  query.set("page", params.current || 1);
  query.set("page_size", params.pageSize || 10);
  return request(`/api/records?${query.toString()}`);
}

export function formatRate(row) {
  if (row.prev_count === 0 && row.count > 0) {
    return { text: "新增", color: "#cf1322" };
  }
  if (row.rate === null || row.rate === undefined) {
    return { text: "—", color: "rgba(0,0,0,0.45)" };
  }
  const text = `${row.rate > 0 ? "+" : ""}${(row.rate * 100).toFixed(1)}%`;
  const color = row.rate > 0 ? "#cf1322" : row.rate < 0 ? "#3f8600" : "rgba(0,0,0,0.65)";
  return { text, color };
}
