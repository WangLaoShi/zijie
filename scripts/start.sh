#!/bin/zsh
cd "$(dirname "$0")/.."
root="$PWD"

"$root/.venv_zijie/bin/python" -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 &
python_pid=$!
node "$root/node-server/server.js" &
node_pid=$!
(cd "$root/web" && npm run dev -- --host 127.0.0.1 --port 5173) &
web_pid=$!

trap 'kill $python_pid $node_pid $web_pid' INT TERM
echo "分析页：http://127.0.0.1:5173/analysis"
echo "查询表格：http://127.0.0.1:5173/list"
wait
