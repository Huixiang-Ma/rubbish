# API 密钥接入文档

> 用途：指导外部 API 密钥的**申请、填写、启用、替换（轮换）**。真实化改造时照此文档操作即可。
> 配套：接口清单见《[接口文档.md](接口文档.md)》；配置声明代码见 `backend/app/api_registry.py`。

## 1. 密钥总览

所有密钥**只配置在项目根 `.env` 一个文件里**（从 `.env.example` 复制），由 `backend/app/api_registry.py` 统一加载生效：

- 后端启动时自动**向上查找项目根 `.env`** 并加载（在 `backend/` 目录启动也能找到）
- docker compose 原生读取项目根 `.env`，注入的环境变量优先于 `.env` 文件内容
- **密钥就绪（环境变量非空）即自动启用**；未配置的 API 自动回退现有 mock 演示口径，断网可演示

| API（registry 名称） | 能力 | 密钥环境变量 | 申请入口 | 门槛 | 未配置时的行为 |
|---|---|---|---|---|---|
| `llm` | 6 Agent 真实生成 | `LLM_API_KEY`（另需 `LLM_MODE=real`、`LLM_BASE_URL`、`LLM_MODEL`） | [阿里云百炼](https://bailian.console.aliyun.com/) / [DeepSeek](https://platform.deepseek.com/) | 免费注册，充值拿 key | mock 模板生成 |
| `amap` | 景点/餐饮 POI、路径规划、地理编码 | `AMAP_API_KEY` | [高德开放平台](https://console.amap.com/) | 免费注册，个人开发者即可 | 静态北京 12 景点 + haversine 估算 |
| `qweather` | 实时天气+逐日预报 | `QWEATHER_API_KEY` | [和风天气](https://console.qweather.com/) | 免费注册 | 四季演示样例文案 |
| `fliggy` | 酒店查询/房价（`taobao.xhotel.*`）、门票商品（`alitrip.ticket.*`） | `TAOBAO_APP_KEY` + `TAOBAO_APP_SECRET` | [淘宝开放平台](https://open.taobao.com/)（应用 → 获取 AppKey/Secret） | 需入驻（个人/企业权限不同） | 三档演示酒店 + 静态票价 |
| `aliyun_content_safety` | 文本审核（增强注入检测） | `ALIYUN_ACCESS_KEY_ID` + `ALIYUN_ACCESS_KEY_SECRET` | [阿里云内容安全](https://www.aliyun.com/product/green) | 可选增强 | 正则注入检测（演示够用） |
| `flyai-mcp` | 真实机票/火车/酒店/景点语义搜索 | **无需密钥**（会话级 MCP，已启动） | — | 已就绪 | 已在运行，见《接口文档.md》§8 |

> 火车票/机票搜索报价全行业无合规开放 API：不设密钥项，行程书中保留演示口径并引导 12306/航司官方渠道。

## 2. 接入步骤（本地裸跑 uvicorn）

```bash
# 1) 复制模板（仅首次）
cp .env.example .env

# 2) 编辑 .env，填入密钥（示例：启用高德 + 和风 + LLM）
#    AMAP_API_KEY=你的高德key
#    QWEATHER_API_KEY=你的和风key
#    LLM_MODE=real
#    LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
#    LLM_API_KEY=sk-xxx
#    LLM_MODEL=qwen-plus

# 3) 重启后端使密钥生效
#    本地：Ctrl+C 后重新 uvicorn app.main:app --reload
#    Docker：docker compose -p wl_travel_mvp restart backend
```

## 3. Docker 接入

- 项目根 `.env` 会被 `docker compose` **自动读取**并注入容器，无需改 `docker-compose.yml`
- 换端口/密钥后执行 `docker compose -p wl_travel_mvp up -d --force-recreate backend` 重建生效
- CI/生产环境建议不用 `.env` 文件，直接注入进程环境变量（优先级更高，见 §6）

## 4. 验证密钥是否生效

```bash
# 方式一：命令行查看全部 provider 的 ready 状态
cd backend && python -c "from app.api_registry import list_apis; [print(r['name'], r['ready']) for r in list_apis()]"

# 方式二：运行中服务查看集成状态
curl http://127.0.0.1:8000/api/integrations/status
```

`ready=true` 即密钥已启用；对应业务模块（行程书章节、服务大厅）会自动改用真实数据源。

## 5. 密钥替换 / 轮换

1. 打开项目根 `.env`，只改对应 API 的那一行（如 `AMAP_API_KEY=新key`）
2. 重启后端（本地）或 `docker compose -p wl_travel_mvp restart backend`（Docker）
3. 用 §4 的命令确认新 key 生效

**更换供应商**（如高德换其他地图）：

1. 在 `backend/app/api_registry.py` 的 `_API_DECLARATIONS` 中替换该条目（name / key_envs / base_url / docs_url）
2. 同步 `.env.example` 的变量名
3. 跑 `cd backend && python -m pytest tests/test_api_registry.py -q`（含"同一能力不允许重复 provider"防回归测试）

## 6. 优先级与生效规则

```
进程环境变量（compose 注入 / 手工 export）  >  项目根 .env 文件  >  registry 默认值
```

- `load_dotenv(override=False)`：已存在的进程变量不会被 `.env` 覆盖
- LLM 特例：必须 `LLM_MODE=real` **且** `LLM_API_KEY` 非空才启用，二者缺一走 mock
- 密钥为空串视为未配置（`.env` 里留空 = 关闭该 API）

## 7. 新增一个 API 的标准步骤

1. `backend/app/api_registry.py` → `_API_DECLARATIONS` 加一个条目：

```python
{
    "name": "new_provider",
    "category": "map",  # llm|map|weather|ticket|hotel|dining|safety|payment
    "description": "一句话用途（写明覆盖哪些业务模块）",
    "base_url": "https://api.example.com",
    "key_envs": ("NEW_API_KEY",),   # 就绪所需全部变量
    "docs_url": "https://...",
},
```

2. `.env.example` 增加对应变量（注释说明申请入口与门槛）
3. 若与现有 provider 同类目（map/weather），先删除旧条目——配置中心有防重复测试
4. 业务代码统一走 `get_api_config("new_provider")` / `is_ready("new_provider")` 接入，**调用失败回退 mock 演示口径**
5. 在 `backend/tests/test_api_registry.py` 补充声明断言

## 8. 安全须知

- `.env` 包含真实密钥，**不要提交到 git**（`.gitignore` 应包含 `.env`；当前项目尚未 git 初始化，建库时注意）
- 密钥只存在服务端环境变量，**不下发前端**；前端一律通过后端 API 代理调用
- 密钥泄露时：在对应平台吊销旧 key → 按本文档 §5 更换 → 重启服务
- 演示/截屏前检查 `.env` 未被打印到终端或日志（后端日志不输出密钥）

## 9. 与 flyai-mcp 的关系

`flyai-mcp` 是会话级 MCP 工具（已启动），**不占密钥配置**：它走 AI 语义搜索（`ai_search` / `search_flight` / `search_train` / `search_hotel` / `search_poi` 等），返回真实供应商数据。真实化改造时两类来源并存：

- 长期稳定数据源 → 按 §1 表格申请密钥接入（行程书生成主链路）
- 快速拿真实报价/语义搜索 → 直接调 flyai-mcp 工具（见《接口文档.md》§8），无需任何配置
