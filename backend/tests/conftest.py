"""pytest 全局环境：配额限流会拦截测试建单（TestClient 全部来自 127.0.0.1），
测试进程内放宽 FREE_PLAN_PER_DAY；必须在 app 模块首次导入前设置。"""
from __future__ import annotations

import os

os.environ["FREE_PLAN_PER_DAY"] = "100000"
