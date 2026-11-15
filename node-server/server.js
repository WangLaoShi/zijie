/**
 * Node 服务只负责接收前端请求，并转发给 Python API。
 * 分类统计和筛选都在 Python 中执行。
 */
import express from "express";

const app = express();
const port = Number(process.env.PORT || 4000);
const pythonApi = process.env.PYTHON_API || "http://127.0.0.1:8000";

app.use("/api", async (request, response) => {
  const target = pythonApi + request.originalUrl;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    const upstream = await fetch(target, { signal: controller.signal });
    const body = await upstream.text();
    response.status(upstream.status);
    response.set(
      "content-type",
      upstream.headers.get("content-type") || "application/json; charset=utf-8",
    );
    response.send(body);
  } catch (error) {
    response.status(502).json({
      detail: "Python 分析服务不可用",
      error: error instanceof Error ? error.message : String(error),
    });
  } finally {
    clearTimeout(timer);
  }
});

app.listen(port, "127.0.0.1", () => {
  console.log(`Node 服务已启动：http://127.0.0.1:${port} -> ${pythonApi}`);
});
