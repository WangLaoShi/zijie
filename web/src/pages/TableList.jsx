import { PageContainer, ProDescriptions, ProTable } from "@ant-design/pro-components";
import { Drawer, Tag } from "antd";
import { useEffect, useMemo, useState } from "react";
import { fetchMeta, fetchRecords, formatRate } from "../services/api";

export default function TableList() {
  const [meta, setMeta] = useState(null);
  const [current, setCurrent] = useState();

  useEffect(() => {
    fetchMeta().then(setMeta).catch(() => setMeta(null));
  }, []);

  const quarterOptions = useMemo(
    () =>
      (meta?.quarters || []).map((item) => ({
        label: item.ongoing ? `${item.label}（进行中）` : item.label,
        value: item.label,
      })),
    [meta],
  );

  const columns = useMemo(
    () => [
      {
        title: "一级分类",
        dataIndex: "l1",
        valueType: "select",
        fieldProps: {
          showSearch: true,
          options: (meta?.categories || []).map((item) => ({ label: item.l1, value: item.l1 })),
        },
      },
      {
        title: "二级分类",
        dataIndex: "l2",
        dependencies: ["l1"],
        valueType: "select",
        request: async (params) => {
          const matched = meta?.categories?.find((item) => item.l1 === params.l1);
          const names = matched
            ? matched.l2
            : [...new Set((meta?.categories || []).flatMap((item) => item.l2))];
          return names.map((name) => ({ label: name, value: name }));
        },
        fieldProps: { showSearch: true },
      },
      {
        title: "开始季度",
        dataIndex: "start",
        valueType: "select",
        hideInTable: true,
        fieldProps: { showSearch: true, options: quarterOptions },
      },
      {
        title: "结束季度",
        dataIndex: "end",
        valueType: "select",
        hideInTable: true,
        fieldProps: { showSearch: true, options: quarterOptions },
      },
      {
        title: "季度",
        dataIndex: "quarter_label",
        search: false,
        render: (dom, row) => <a onClick={() => setCurrent(row)}>{dom}</a>,
      },
      {
        title: "岗位数",
        dataIndex: "count",
        search: false,
        render: (value) => Number(value).toLocaleString(),
      },
      {
        title: "上季岗位数",
        dataIndex: "prev_count",
        search: false,
        render: (value) => (value === null || value === undefined ? "—" : Number(value).toLocaleString()),
      },
      {
        title: "环比增减",
        dataIndex: "delta",
        search: false,
        render: (_, row) => {
          if (row.delta === null || row.delta === undefined) return "—";
          const color = row.delta > 0 ? "#cf1322" : row.delta < 0 ? "#3f8600" : "inherit";
          const text = `${row.delta > 0 ? "+" : ""}${row.delta.toLocaleString()}`;
          return <span style={{ color }}>{text}</span>;
        },
      },
      {
        title: "环比",
        dataIndex: "rate",
        search: false,
        render: (_, row) => {
          const change = formatRate(row);
          return <span style={{ color: change.color }}>{change.text}</span>;
        },
      },
      {
        title: "季度状态",
        dataIndex: "ongoing",
        search: false,
        render: (_, row) => (row.ongoing ? <Tag color="processing">进行中</Tag> : <Tag>完整</Tag>),
      },
    ],
    [meta, quarterOptions],
  );

  return (
    <PageContainer
      title="查询表格"
      subTitle="按一级分类、二级分类和季度查询岗位数变化"
      content="查询条件会交给 Python 过滤和分页，表格按季度从近到远排列。"
    >
      <ProTable
        rowKey="key"
        headerTitle="二级分类季度明细"
        columns={columns}
        search={{ labelWidth: 80, defaultCollapsed: false, span: 6 }}
        pagination={{ defaultPageSize: 10, showSizeChanger: true }}
        request={async (params) => {
          const payload = await fetchRecords(params);
          return { data: payload.items, success: true, total: payload.total };
        }}
      />
      <Drawer width={420} open={Boolean(current)} title="季度明细" onClose={() => setCurrent(undefined)}>
        {current ? (
          <ProDescriptions
            column={1}
            dataSource={current}
            columns={[
              { title: "一级分类", dataIndex: "l1" },
              { title: "二级分类", dataIndex: "l2" },
              { title: "季度", dataIndex: "quarter_label" },
              { title: "岗位数", dataIndex: "count" },
              { title: "上季岗位数", dataIndex: "prev_count" },
              { title: "环比增减", dataIndex: "delta" },
              {
                title: "环比",
                dataIndex: "rate",
                render: (_, row) => formatRate(row).text,
              },
              {
                title: "季度状态",
                dataIndex: "ongoing",
                render: (_, row) => (row.ongoing ? "进行中" : "完整"),
              },
            ]}
          />
        ) : null}
      </Drawer>
    </PageContainer>
  );
}
