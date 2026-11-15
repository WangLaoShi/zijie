import { BarChartOutlined, TableOutlined } from "@ant-design/icons";
import { ProLayout } from "@ant-design/pro-components";
import { Link, Outlet, useLocation } from "react-router-dom";

const route = {
  path: "/",
  routes: [
    { path: "/analysis", name: "分析页", icon: <BarChartOutlined /> },
    { path: "/list", name: "查询表格", icon: <TableOutlined /> },
  ],
};

export default function BasicLayout() {
  const location = useLocation();
  return (
    <ProLayout
      title="岗位季度分析"
      logo={<BarChartOutlined style={{ fontSize: 22, color: "#1677ff" }} />}
      layout="mix"
      fixSiderbar
      fixedHeader
      location={{ pathname: location.pathname }}
      route={route}
      menuItemRender={(item, dom) => (item.path ? <Link to={item.path}>{dom}</Link> : dom)}
      token={{
        header: { colorBgHeader: "#fff" },
        sider: { colorMenuBackground: "#fff" },
      }}
    >
      <Outlet />
    </ProLayout>
  );
}
