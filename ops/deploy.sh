#!/usr/bin/env bash
# P3.3 发布流程：备份 → 拉镜像 → 滚动更新 → 探活 → 失败回滚。
# 用法（生产主机上）：bash ops/deploy.sh [镜像tag，默认 latest]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAG="${1:-latest}"
COMPOSE="docker compose -p wl_travel_mvp"
HEALTH_URL="http://127.0.0.1:8000/health"
PREV_IMAGE="$($COMPOSE images backend -q 2>/dev/null || true)"

echo "== 1/4 发布前备份 =="
bash "$ROOT/ops/backup.sh"

echo "== 2/4 拉取镜像 ($TAG) =="
$COMPOSE pull backend

echo "== 3/4 滚动更新 =="
$COMPOSE up -d backend

echo "== 4/4 探活（最多 60s）=="
ok=""
for i in $(seq 1 12); do
  sleep 5
  if curl -sf -m 5 "$HEALTH_URL" >/dev/null; then ok=1; break; fi
  echo "  等待后端就绪... ($i)"
done

if [ -n "$ok" ]; then
  echo "✅ 发布成功（tag=$TAG）"
else
  echo "❌ 探活失败，回滚到上一镜像"
  if [ -n "$PREV_IMAGE" ]; then
    $COMPOSE up -d --no-deps --force-recreate backend
  fi
  echo "已回滚，请人工检查日志：$COMPOSE logs backend --tail 100"
  exit 1
fi
