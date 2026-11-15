import { Column, Line, Pie } from "@ant-design/plots";
import { PageContainer, StatisticCard } from "@ant-design/pro-components";
import { Alert, Card, Col, Empty, Row, Select, Spin } from "antd";
import { Component, useEffect, useMemo, useState } from "react";
import { fetchAnalysis, fetchMeta, formatRate } from "../services/api";

class ChartBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return <Alert type="error" showIcon message="图表没有渲染出来" description={String(this.state.error)} />;
    }
    return this.props.children;
  }
}

function rangeOf(quarters, rangeKey) {
  const labels = quarters.map((item) => item.label);
  if (rangeKey === "all") {
    return { start: labels[0], end: labels[labels.length - 1] };
  }
  const size = rangeKey === "q4" ? 4 : 8;
  const slice = labels.slice(-size);
  return { start: slice[0], end: slice[slice.length - 1] };
}

export default function Analysis() {
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState("");
  const [l1, setL1] = useState();
  const [rangeKey, setRangeKey] = useState("q8");
  const [focus, setFocus] = useState();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchMeta()
      .then((payload) => {
        setMeta(payload);
        setL1(payload.categories[0]?.l1);
      })
      .catch((reason) => setError(reason.message));
  }, []);

  const range = useMemo(() => (meta ? rangeOf(meta.quarters, rangeKey) : null), [meta, rangeKey]);

  useEffect(() => {
    if (!l1 || !range) return undefined;
    let active = true;
    setLoading(true);
    fetchAnalysis({ l1, start: range.start, end: range.end, focus })
      .then((payload) => {
        if (active) {
          setData(payload);
          setError("");
        }
      })
      .catch((reason) => {
        if (active) setError(reason.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [l1, range, focus]);

  const summary = data?.summary;
  const rate = summary
    ? formatRate({
        rate: summary.qoq_rate,
        prev_count: summary.previous_complete_count,
        count: summary.latest_complete_count,
      })
    : null;
  const pieData = (data?.ranking || []).filter((item) => item.count > 0);

  return (
    <PageContainer
      title="分析页"
      subTitle="每个一级分类下面，按二级分类观察季度岗位数"
      extra={
        <Select
          style={{ width: 220 }}
          value={l1}
          placeholder="选择一级分类"
          options={(meta?.categories || []).map((item) => ({
            label: `${item.l1}（${item.total.toLocaleString()}）`,
            value: item.l1,
          }))}
          onChange={(value) => {
            setL1(value);
            setFocus(undefined);
          }}
        />
      }
      content={meta?.notes?.join("")}
    >
      {error ? <Alert style={{ marginBottom: 16 }} type="error" showIcon message={error} /> : null}
      <Spin spinning={loading && !data}>
        <StatisticCard.Group direction="row" style={{ marginBottom: 16 }}>
          <StatisticCard
            statistic={{
              title: "该一级分类岗位数",
              value: summary?.total_all_time ?? "-",
              description: l1 || "—",
            }}
          />
          <StatisticCard
            statistic={{
              title: "二级分类数",
              value: summary?.l2_count ?? "-",
              description: "同名二级分类单独保留",
            }}
          />
          <StatisticCard
            statistic={{
              title: "最近完整季度岗位数",
              value: summary?.latest_complete_count ?? "-",
              description: summary?.latest_complete_quarter || "—",
            }}
          />
          <StatisticCard
            statistic={{
              title: "较上一完整季度",
              value: rate?.text || "—",
              valueStyle: { color: rate?.color },
              description: summary?.previous_complete_quarter
                ? `${summary.previous_complete_quarter} → ${summary.latest_complete_quarter}`
                : "—",
            }}
          />
        </StatisticCard.Group>

        <Row gutter={[16, 16]}>
          <Col xs={24} xl={16}>
            <Card
              title={`${l1 || ""} 二级分类季度岗位数`}
              extra={
                <div className="sales-extra">
                  {[
                    ["q4", "近4季"],
                    ["q8", "近8季"],
                    ["all", "全部"],
                  ].map(([key, label]) => (
                    <a
                      key={key}
                      className={rangeKey === key ? "active" : ""}
                      onClick={() => {
                        setRangeKey(key);
                        setFocus(undefined);
                      }}
                    >
                      {label}
                    </a>
                  ))}
                </div>
              }
            >
              <ChartBoundary>
                {data ? (
                  <Column
                    height={336}
                    data={data.trend}
                    xField="quarter"
                    yField="count"
                    colorField="l2"
                    stack
                    legend={{ color: { position: "bottom", maxRows: 2, itemSpacing: 8 } }}
                    axis={{ x: { labelAutoHide: true } }}
                  />
                ) : (
                  <Empty />
                )}
              </ChartBoundary>
            </Card>
          </Col>
          <Col xs={24} xl={8}>
            <Card
              title="二级分类排名"
              extra={
                <Select
                  size="small"
                  style={{ width: 140 }}
                  value={data?.focus}
                  options={(data?.quarter_totals || []).map((item) => ({
                    value: item.quarter,
                    label: item.ongoing ? `${item.quarter} 进行中` : item.quarter,
                  }))}
                  onChange={setFocus}
                />
              }
            >
              <ol className="rank-list">
                {(data?.ranking || []).map((item, index) => {
                  const change = formatRate(item);
                  return (
                    <li key={item.l2}>
                      <span className={index < 3 ? "rank-index top" : "rank-index"}>{index + 1}</span>
                      <span className="rank-name">{item.l2}</span>
                      <span className="rank-value">{item.count.toLocaleString()}</span>
                      <span style={{ width: 72, color: change.color, textAlign: "right" }}>{change.text}</span>
                    </li>
                  );
                })}
              </ol>
            </Card>
          </Col>
          <Col xs={24} xl={14}>
            <Card title={`${l1 || ""} 各二级分类数量变化`} loading={loading}>
              <ChartBoundary>
                {data ? (
                  <Line
                    height={320}
                    data={data.trend}
                    xField="quarter"
                    yField="count"
                    colorField="l2"
                    legend={{ color: { position: "bottom", maxRows: 2 } }}
                    axis={{ x: { labelAutoHide: true } }}
                  />
                ) : (
                  <Empty />
                )}
              </ChartBoundary>
            </Card>
          </Col>
          <Col xs={24} xl={10}>
            <Card title={`${data?.focus || ""} 二级分类占比`}>
              <ChartBoundary>
                {pieData.length ? (
                  <Pie
                    height={320}
                    data={pieData}
                    angleField="count"
                    colorField="l2"
                    radius={0.9}
                    innerRadius={0.62}
                    legend={{ color: { position: "bottom", maxRows: 3 } }}
                  />
                ) : (
                  <Empty description="该季度没有岗位" />
                )}
              </ChartBoundary>
            </Card>
          </Col>
        </Row>
      </Spin>
    </PageContainer>
  );
}
