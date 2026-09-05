#!/usr/bin/env bash
# 每日备份：data/jobs 任务快照 + PostgreSQL 全量 dump，保留最近 14 天。
# 部署：宿主 crontab 加一行（示例每天 03:10）：
#   10 3 * * * bash /opt/wl/ops/backup.sh >> /var/log/wl_backup.log 2>&1
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${WL_BACKUP_DIR:-$ROOT/backups}"
KEEP_DAYS=14
STAMP="$(date +%Y%m%d-%H%M%S)"
COMPOSE="docker compose -p wl_travel_mvp"

mkdir -p "$BACKUP_DIR"

# 1) 任务文件快照（事实源）
tar -czf "$BACKUP_DIR/data-jobs-$STAMP.tar.gz" -C "$ROOT" data/jobs data/jobs_archive 2>/dev/null || true

# 2) PostgreSQL 镜像库 dump（容器未启动时跳过，不阻断）
if $COMPOSE ps --status running postgres 2>/dev/null | grep -q postgres; then
  $COMPOSE exec -T postgres pg_dump -U wl wl_travel | gzip > "$BACKUP_DIR/pg-wl_travel-$STAMP.sql.gz"
fi

# 3) 过期清理
find "$BACKUP_DIR" -name "data-jobs-*.tar.gz" -mtime +$KEEP_DAYS -delete
find "$BACKUP_DIR" -name "pg-wl_travel-*.sql.gz" -mtime +$KEEP_DAYS -delete

echo "[$(date '+%F %T')] backup done -> $BACKUP_DIR (stamp $STAMP)"
