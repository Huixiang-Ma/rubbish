import json
from pathlib import Path
from typing import Any

from app.services.atomic_writer import AtomicWriter
from app.services.paths import job_dir
from app.services.travel_context_service import TravelContextService


class MarkdownReporter:
    def __init__(self) -> None:
        self.writer = AtomicWriter()

    def render_and_write(self, job_id: str, context: dict[str, Any]) -> str:
        markdown = self.render(context)
        return self.writer.write_text(job_dir(job_id) / "travel_plan.md", markdown)

    def render(self, context: dict[str, Any]) -> str:
        user_input = context["user_input"]
        outputs = context["outputs"]
        itinerary = outputs["Itinerary"]["payload"]["itinerary"]
        validation = outputs["Validator"]["payload"]
        # 预算字段：新管线由 Budget 节点产出；旧任务无 Budget 输出时兜底读 Validator 历史字段
        budget = outputs.get("Budget", {}).get("payload") or {}
        if not budget:
            budget = {
                key: validation[key]
                for key in (
                    "estimated_budget",
                    "budget_breakdown",
                    "approval_required",
                    "economy_total",
                    "travel_advice",
                    "economy_tips",
                )
                if key in validation
            }
        # 翻车预演：时空类（Validator）+ 预算类（Budget）合并，旧任务自动只有一处
        what_if = list(validation.get("what_if", [])) + list(budget.get("what_if", []))
        is_tob = context.get("pipeline") == "tob"
        lines = [
            f"# {user_input['destination']} {user_input['days']} 日智能行程方案",
            "",
            "## 1. 需求摘要",
            "",
            f"- 目的地：{user_input['destination']}",
            f"- 天数：{user_input['days']} 天",
            f"- 人数：{user_input.get('travelers', 2)} 人",
            f"- 预算金额：{user_input['budget']} 元",
            f"- 预估总花费：{budget.get('estimated_budget', validation.get('estimated_budget', 0))} 元（按下方分项口径估算，非下单实价）",
            f"- 偏好：{', '.join(user_input.get('preferences', [])) or '未填写'}",
            f"- 约束：{', '.join(user_input.get('constraints', [])) or '未填写'}",
            "",
            "## 2. 住宿与每日行程",
            "",
        ]
        service = TravelContextService()
        # 2.1 住宿推荐：按预算匹配档位推荐酒店，每日行程直接嵌在推荐酒店条目下
        lines.extend(["### 2.1 住宿推荐", ""])
        hotel_data = service.hotels(user_input["destination"], max(1, user_input["days"] - 1))
        hotels = hotel_data.get("hotels", [])

        def render_days() -> None:
            for day in itinerary:
                lines.extend([f"### Day {day['day']} · {day['theme']}", ""])
                if day.get("weather"):
                    lines.append(f"- 🌤 当日天气：{day['weather']}（和风实时预报）")
                    lines.append("")
                if day.get("fun_tip"):
                    lines.append(f"- 💡 今日建议：{day['fun_tip']}")
                    lines.append("")
                schedule_items = [
                    {"kind": "spot", "time": item["time"], "payload": item}
                    for item in day["items"]
                ] + [
                    {"kind": "meal", "time": meal["time"], "payload": meal}
                    for meal in day.get("meals", [])
                ]
                for schedule_item in sorted(schedule_items, key=lambda item: item["time"]):
                    if schedule_item["kind"] == "meal":
                        meal = schedule_item["payload"]
                        lines.extend(
                            [
                                f"- **{meal['time']}｜{meal['title']}**",
                                f"  - 推荐菜品：{meal['signature']}",
                                f"  - 价格参考：{meal['price_hint']}",
                                f"  - 地理安排：{meal['location_hint']}",
                                f"  - 提醒：{meal['note']}",
                            ]
                        )
                        continue
                    item = schedule_item["payload"]
                    spot = item["spot"]
                    open_time = spot.get("open_time") or "以景区公告为准"
                    open_time_label = "（高德实时）" if spot.get("open_time_realtime") else ""
                    lines.append(f"- **{item['time']}｜{item['title']}**")
                    lines.append(f"  - 推荐理由：{item['reason']}")
                    lines.append(f"  - 交通建议：{item['transport']}")
                    lines.append(f"  - 景点标签：{', '.join(spot.get('tags', [])) or '暂无'}")
                    lines.append(f"  - 开放时间：{open_time}{open_time_label}")
                    if spot.get("list_rank"):
                        lines.append(f"  - 榜单：{spot['list_rank']}（飞猪AI）")
                    if spot.get("booking_url"):
                        lines.append(f"  - 门票预订：[飞猪预订]({spot['booking_url']})（实时票价以预订页为准）")
                    if spot.get("main_pic"):
                        lines.append(f"  ![ {spot.get('name', '景点')}实拍]({spot['main_pic']})")
                    source_urls = spot.get("source_urls") or []
                    if source_urls:
                        rendered = "、".join(
                            f"[高德检索]({url})" if "amap.com" in url else f"[飞猪预订]({url})"
                            for url in source_urls
                        )
                        lines.append(f"  - 信息来源：{rendered}")
                    elif spot.get("source") == "静态演示库":
                        lines.append("  - 信息来源：静态演示数据，无外部来源链接")
                lines.append("")

        anchor_hotel = service.recommend_hotel_poi(
            user_input["destination"],
            budget=user_input["budget"],
            days=user_input["days"],
            origin=user_input.get("origin"),
        )
        if anchor_hotel:
            name = anchor_hotel["name"].replace("<", "&lt;").replace(">", "&gt;")
            position = (anchor_hotel.get("position") or "").replace("<", "&lt;").replace(">", "&gt;")
            lines.extend(["<details open>", f"<summary>🏆 推荐入住：{name}｜{position}</summary>"])
            render_days()
            lines.append("</details>")
            category_order = ["高档酒店", "酒店", "民宿公寓", "商务配套"]
            for category in category_order:
                grouped = [h for h in hotels if h["category"] == category and h["name"] != anchor_hotel["name"]]
                if not grouped:
                    continue
                lines.extend(["<details>", f"<summary>🛏️ {category}·备选（{len(grouped)} 家）</summary>"])
                for hotel_poi in grouped:
                    backup_name = hotel_poi["name"].replace("<", "&lt;").replace(">", "&gt;")
                    backup_position = (hotel_poi.get("position") or "").replace("<", "&lt;").replace(">", "&gt;")
                    lines.extend(["<details>", f"<summary>{backup_name}｜{backup_position}</summary>"])
                    lines.append(f"- 距市中心约 {hotel_poi.get('distance_km', 0)} 公里")
                    lines.append("</details>")
                lines.append("</details>")
            lines.append("- 房价与房态请以各预订平台实时公示为准；本行程书不生成虚拟房价。")
        else:
            lines.append("- 暂未检索到周边住宿，请通过预订平台按住宿分档建议查询。")
            # 无酒店检索结果（如未配置地图密钥）时，每日行程退回独立小节
            lines.extend(["", "### 2.2 每日行程详解（起点：目的地市中心）", ""])
            render_days()
        # 2.3 交通与住宿参考：城际建议 + 天气提示（来源 Validator 的 travel_advice）
        lines.extend(["", "### 2.3 交通与住宿参考", ""])
        travel_advice = budget.get("travel_advice") or {}
        intercity = travel_advice.get("intercity") or {}
        if intercity.get("origin"):
            lines.append(
                f"- 城际交通（{intercity.get('origin', '')} 出发）：高铁约 {intercity.get('high_speed', '视距离而定')}、"
                f"飞行约 {intercity.get('flight', '视距离而定')} —— {intercity.get('recommendation', '')}；"
                f"往返大交通预算参考 {intercity.get('round_trip_cost', 0)} 元/人（估算口径，非实时票价）。"
            )
        else:
            lines.append("- 城际交通：未填写出发地，暂无法给出高铁/飞机对比；可补充出发地后重规划获取精准建议。")
        for note in travel_advice.get("weather_notes", []):
            lines.append(f"- 天气参考：{note}")
        lines.append("- 住宿分档与预算匹配逻辑见上方推荐与费用分项（需求摘要及费用账本），房价以预订平台实时公示为准。")
        # 3. 决策辩论（toC）/ 顾问话术（toB）等后续章节紧随住宿与每日行程
        if is_tob:
            # toB 口径：顾问话术 + 合规审计摘要替代 toC 的辩论/心情章节
            consultant = (outputs.get("Consultant") or {}).get("payload", {})
            compliance = (outputs.get("Compliance") or {}).get("payload", {})
            lines.extend(["", "## 3. 顾问话术（toB）", ""])
            if consultant:
                lines.append(f"- 客户：{consultant.get('customer', '')}")
                for point in consultant.get("talking_points", []):
                    lines.append(f"- {point}")
                lines.append(f"- 跟进建议：{consultant.get('follow_up', '')}")
            else:
                lines.append("- 暂无顾问话术。")
            lines.extend(["", "## 4. 合规审计摘要（toB）", ""])
            if compliance:
                lines.append(f"- 结论：{compliance.get('summary', '')}")
                for risk in compliance.get("risks", []):
                    lines.append(f"- 风险：{risk['scene']} → B 计划：{risk['plan_b']}")
                for declaration in compliance.get("data_declarations", []):
                    lines.append(f"- 口径声明：{declaration}")
                lines.append(f"- 交付建议：{compliance.get('approval_suggestion', '')}")
            else:
                lines.append("- 暂无合规摘要。")
            lines.extend(["", "## 5. 舆情与避坑提示", ""])
            self._render_sentiment(lines, outputs)
            summary_no, index_no = 6, 7
        else:
            lines.extend(["", "## 3. 决策辩论（为何这样安排）", ""])
            debates = (outputs.get("Debate") or {}).get("payload", {}).get("debates", [])
            if debates:
                for index, debate in enumerate(debates, start=1):
                    lines.extend(
                        [
                            f"### 议题 {index}：{debate['topic']}",
                            "",
                            f"- **{debate['plan_side']['role']}**：{debate['plan_side']['point']}",
                            f"- **{debate['traveler_side']['role']}**：{debate['traveler_side']['point']}",
                            f"- **最终取舍**：{debate['verdict']['decision']} —— {debate['verdict']['reason']}",
                            "",
                        ]
                    )
            else:
                lines.extend(["- 暂无辩论内容。", ""])

            # toC 章节编号动态递增：心情剧本为可选章，后面章节的编号不能写死
            chapter_no = 3

            chapter_no += 1
            lines.extend(["", f"## {chapter_no}. 舆情与避坑提示", ""])
            self._render_sentiment(lines, outputs)
            chapter_no += 1
            lines.extend(["", f"## {chapter_no}. 费用账本", ""])
            self._render_budget_ledger(lines, budget, user_input)
            chapter_no += 1
            lines.extend(["", f"## {chapter_no}. 翻车预演（诚实版 B 计划）", ""])
            if what_if:
                for index, item in enumerate(what_if, start=1):
                    lines.extend(
                        [
                            f"### 翻车 {index}：{item['scene']}",
                            f"- 风险：{item['risk']}",
                            f"- B 计划：{item['plan_b']}",
                            "",
                        ]
                    )
            else:
                lines.extend(["- 暂无翻车预警。", ""])

            chapter_no += 1
            mood_payload = (outputs.get("Mood") or {}).get("payload")
            # 标题无条件输出：未选心情词时章节保留并如实说明，避免章节编号断档
            lines.extend(["", f"## {chapter_no}. 心情剧本（情绪弧线）", ""])
            if mood_payload and mood_payload.get("phases"):
                lines.extend(
                    [
                        f"- 心情词：{mood_payload.get('mood', '')}",
                        f"- 剧本主题：{mood_payload.get('theme', '')}",
                        "",
                    ]
                )
                for phase in mood_payload["phases"]:
                    lines.extend(
                        [
                            f"### Day {phase.get('day')} · {phase.get('phase', '')}",
                            f"- 情绪：{phase.get('emotion', '')}",
                            f"- 叙事：{phase.get('narration', '')}",
                            "",
                        ]
                    )
            else:
                lines.extend(["- 未指定心情词，心情导演跳过了本章。", ""])

            chapter_no += 1
            lines.extend(["", f"## {chapter_no}. 出行清单", ""])
            self._render_pack_list(lines, itinerary, budget, user_input)
            chapter_no += 1
            summary_no, index_no = chapter_no, chapter_no + 1

        lines.extend(
            [
                f"## {summary_no}. 工程说明",
                "",
                (
                    "- 本方案由 toB 管线 Agent 协作生成：Researcher、Planner、Itinerary、Validator、Sentiment（舆情过滤）、Consultant（顾问话术）、Compliance（合规审计），最终由 Reporter 节点汇总渲染。"
                    if is_tob
                    else "- 本方案由 toC 管线 Agent 协作生成：Researcher、Planner、Itinerary、Validator、Sentiment（舆情过滤）、Debate（辩论式可解释）、Mood（心情剧本，填写 mood 时才进入管线），最终由 Reporter 节点汇总渲染。"
                ),
                "- 数据来源：景点/餐饮/通勤来自高德实时检索，天气来自和风实时预报（需配置对应密钥，未配置时为本地估算口径）；票务与房价不提供虚拟数据，仅给官方渠道指引。",
                "- `travel_plan.md` 是展示与导出产物，不作为唯一状态源。",
                "",
                f"## {index_no}. Agent 结构化输出索引",
                "",
                "```json",
                json.dumps({name: output.get("status") for name, output in outputs.items()}, ensure_ascii=False, indent=2),
                "```",
            ]
        )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _render_sentiment(lines: list[str], outputs: dict[str, Any]) -> None:
        """渲染"舆情与避坑提示"章节；旧任务无 Sentiment 输出时如实标注。"""
        sentiment = (outputs.get("Sentiment") or {}).get("payload")
        if not sentiment:
            lines.append("- 暂无舆情数据（该任务生成于舆情 Agent 上线前）。")
            return
        lines.append(f"- {sentiment.get('summary', '')}")
        for alert in sentiment.get("risk_alerts", []):
            lines.append(f"- ⚠️ {alert.get('name', '')} [{alert.get('risk_level', '')}]：{alert.get('message', '')} → 建议：{alert.get('suggestion', '')}")
        if not sentiment.get("risk_alerts"):
            lines.append("- 本次行程未命中高风险舆情，整体口碑平稳。")
        for review in sentiment.get("reviews", []):
            highlights = "；".join(review.get("highlights", []))
            warnings = "；".join(review.get("warnings", []))
            parts = [f"{review.get('name', '')}"]
            if highlights:
                parts.append(f"亮点：{highlights}")
            if warnings:
                parts.append(f"提示：{warnings}")
            parts.append(f"（来源：{review.get('source', '')}）")
            lines.append(f"- {'，'.join(parts)}")

    @staticmethod
    def _render_budget_ledger(lines: list[str], budget: dict[str, Any], user_input: dict[str, Any]) -> None:
        """渲染"费用账本"章节：分项对账 + 人均口径 + 经济口径建议；旧任务无 Budget 输出时如实标注。"""
        breakdown = budget.get("budget_breakdown") or {}
        travelers = max(1, int(user_input.get("travelers", 2) or 2))
        estimated = budget.get("estimated_budget", breakdown.get("total", 0))
        if not breakdown or not estimated:
            lines.append("- 暂无预算分项（该任务生成于预算 Agent 拆分前），可重新生成获取完整账本。")
            return
        items = [
            ("城际往返大交通", breakdown.get("intercity")),
            ("住宿（分档口径 × 间夜）", breakdown.get("hotel")),
            ("市内交通（打车按 3 人一车拼算）", breakdown.get("local_transport")),
            ("门票（按人数合计）", breakdown.get("tickets")),
            ("餐饮（按天 × 人数口径）", breakdown.get("meals")),
        ]
        for name, amount in items:
            amount_text = f"{amount} 元" if amount is not None else "未计入"
            lines.append(f"- {name}：{amount_text}")
        lines.append(f"- **小计（总预算口径）：{estimated} 元 / {travelers} 人，人均约 {round(estimated / travelers)} 元**")
        lines.append(f"- 你的预算上限：{user_input.get('budget', 0)} 元 → {'在预算内' if estimated <= user_input.get('budget', 0) else '超出预算，见下方经济口径与翻车预演'}")
        if budget.get("approval_required"):
            lines.append("- 本单触发过预算挂起确认，已在批准后继续生成。")
        economy_total = budget.get("economy_total")
        if economy_total:
            lines.append(f"- 经济口径重估：{economy_total} 元（经济住宿 + 人均 100 元/天餐饮 + 市内交通减半）。")
        for tip in budget.get("economy_tips", []):
            lines.append(f"- 省钱建议：{tip}")
        lines.append("- 口径说明：以上为估算非下单实价；门票与房价以官方/预订平台实时公示为准。")

    @staticmethod
    def _render_pack_list(
        lines: list[str],
        itinerary: list[dict[str, Any]],
        budget: dict[str, Any],
        user_input: dict[str, Any],
    ) -> None:
        """渲染"出行清单"章节：按真实行程与天气建议派生，不虚构数据。"""
        lines.append("- □ 身份证 / 证件（实名购票、入园、住宿登记均需）")
        # 收费景点：需要预约或购票的，逐个列出
        ticket_spots: list[str] = []
        for day in itinerary:
            for item in day.get("items", []):
                spot = item.get("spot") or {}
                name = spot.get("name")
                if name and spot.get("ticket_price", 0) and name not in ticket_spots:
                    ticket_spots.append(name)
        for name in ticket_spots[:6]:
            lines.append(f"- □ {name}：提前在官方公众号/小程序预约或购票（收费景点，建议前一晚确认）")
        if not ticket_spots:
            lines.append("- □ 本行程暂无收费景点，免费点位请按当日开放时间现场预约")
        for note in (budget.get("travel_advice") or {}).get("weather_notes", []):
            if note.endswith("："):
                continue  # 天气小节的标题行，不作为待办项
            lines.append(f"- □ 天气应对：{note}")
        lines.append("- □ 充电宝（全天在外导航、查预约码耗电快）")
        lines.append("- □ 常用药品与创可贴（步行量大，防磨脚）")
        lines.append("- □ 少量现金零钱（部分小馆/摊位只收现金）")
        origin = user_input.get("origin")
        if origin:
            lines.append(f"- □ 从 {origin} 出发的往返大交通票，已按行程日期锁定候补/购票时间")

    def read_result(self, job_id: str) -> tuple[str, str]:
        path = job_dir(job_id) / "travel_plan.md"
        hash_path = Path(str(path) + ".sha256")
        return path.read_text(encoding="utf-8"), hash_path.read_text(encoding="utf-8")
