import { Navigate, Route, Routes } from "react-router-dom";
import BasicLayout from "./layouts/BasicLayout";
import Analysis from "./pages/Analysis";
import TableList from "./pages/TableList";

export default function App() {
  return (
    <Routes>
      <Route element={<BasicLayout />}>
        <Route path="/" element={<Navigate to="/analysis" replace />} />
        <Route path="/analysis" element={<Analysis />} />
        <Route path="/list" element={<TableList />} />
      </Route>
    </Routes>
  );
}
