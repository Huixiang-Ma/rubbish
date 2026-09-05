import json
import re
from datetime import datetime, timezone
from typing import Any

from app.services.atomic_writer import AtomicWriter
from app.services.llm_client import LLMClient
from app.services.paths import job_dir

SWARM_PERSONAS = [
    {"name": "早起打卡型游客", "style": "赶早避峰，开园即入", "crowd_bias": "低"},
    {"name": "休闲遛娃型游客", "style": "节奏慢，午休后再出发", "crowd_bias": "中"},
    {"name": "拍照出片型游客", "style": "追光线，傍晚出片", "crowd_bias": "高"},
]

GUIDES = [
    {"id": "dufu", "name": "杜甫", "persona": "唐代诗人，偏爱历史古迹与山河气象", "tone": "诗意沉郁", "tags": ["历史", "园林", "地标"]},
    {"id": "foodie", "name": "本地吃货", "persona": "北京土著美食向导，专挑烟火气", "tone": "泼辣亲切", "tags": ["美食", "胡同", "夜游"]},
    {"id": "mom", "name": "亲子妈妈", "persona": "带娃出行专家，最看重体力和安全", "tone": "细致务实", "tags": ["亲子", "动物", "公园"]},
]


class ExperienceService:
    """C3/C4/C5/C6 体验服务：基于已完成任务的结构化输出生成内容。

    LLM real 模式生成真内容，失败自动落确定性模板（引用真实估算数据）。
    """

    def __init__(self) -> None:
        self.llm = LLMClient()
        self.writer = AtomicWriter()

    def load_outputs(self, job_id: str, state: dict[str, Any]) -> dict[str, dict[str, Any]]:
        outputs: dict[str, dict[str, Any]] = {}
        for name, relative in state.get("agent_outputs", {}).items():
            path = job_dir(job_id) / relative
            if not path.exists():
                continue
            try:
                outputs[name] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
        return outputs

    @staticmethod
    def _selected_spots(outputs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            item["spot"]
            for day in outputs.get("Itinerary", {}).get("payload", {}).get("itinerary", [])
            for item in day.get("items", [])
            if item.get("spot", {}).get("lat")
        ]

    def _facts(self, state: dict[str, Any], outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        user_input = state.get("user_input", {})
        selected = self._selected_spots(outputs)
        candidate_names = [s.get("name") for s in outputs.get("Researcher", {}).get("payload", {}).get("spots", [])]
        selected_names = {s.get("name") for s in selected}
        dropped = [name for name in candidate_names if name not in selected_names][:3]
        validation = outputs.get("Validator", {}).get("payload", {})
        legs = outputs.get("Itinerary", {}).get("payload", {}).get("legs", [])
        worst_leg = max(legs, key=lambda leg: leg.get("taxi_minutes", 0)) if legs else None
        return {
            "destination": user_input.get("destination"),
            "days": user_input.get("days"),
            "budget": user_input.get("budget"),
            "preferences": user_input.get("preferences", []),
            "selected_spots": [s.get("name") for s in selected],
            "dropped_candidates": dropped,
            "estimated_budget": validation.get("estimated_budget"),
            "budget_breakdown": validation.get("budget_breakdown", {}),
            "worst_commute": (
                {"from": worst_leg["from"], "to": worst_leg["to"], "taxi_minutes": worst_leg["taxi_minutes"]}
                if worst_leg
                else None
            ),
        }

    # ---------- C4 反事实后悔药 ----------

    def counterfactual(self, job_id: str, state: dict[str, Any]) -> dict[str, Any]:
        outputs = self.load_outputs(job_id, state)
        facts = self._facts(state, outputs)
        cards = self._llm_cards(facts) or self._mock_cards(facts)
        return {"job_id": job_id, "mode": "real" if self.llm.mode == "real" and self.llm.api_key else "mock", "cards": cards}

    def _mock_cards(self, facts: dict[str, Any]) -> list[dict[str, Any]]:
        cards = []
        selected = facts["selected_spots"]
        kept = selected[0] if selected else "核心景点"
        for dropped in facts["dropped_candidates"]:
            cards.append(
                {
                    "gave_up": dropped,
                    "got": kept,
                    "reason": (
                        f"行程只有 {facts['days']} 天，选择「{kept}」保证了与偏好（{', '.join(facts['preferences']) or '通用'}）"
                        f"的匹配度和动线确定性；「{dropped}」列为候选替补，可通过增量重规划换入。"
                    ),
                    "cost_note": (
                        f"当前分项预算合计 {facts['estimated_budget']} 元（用户预算 {facts['budget']} 元），"
                        "换入备选景点对门票与市内交通影响有限。"
                    ),
                }
            )
        if facts.get("worst_commute"):
            worst = facts["worst_commute"]
            cards.append(
                {
                    "gave_up": f"把「{worst['to']}」排进远端行程",
                    "got": f"把「{worst['to']}」就近安排",
                    "reason": f"{worst['from']}→{worst['to']} 打车估算 {worst['taxi_minutes']} 分钟，就近安排省下的通勤时间可多游一个景点。",
                    "cost_note": "市内交通分项已按打车估算上限计，未额外超支。",
                }
            )
        return cards

    def _llm_cards(self, facts: dict[str, Any]) -> list[dict[str, Any]] | None:
        prompt = (
            "基于行程事实生成反事实后悔药对照卡：对放弃的候选景点各生成一条，说明放弃它换来了什么。"
            "输出 JSON：{\"cards\": [{\"gave_up\": str, \"got\": str, \"reason\": str, \"cost_note\": str}]}，"
            "必须引用事实中的景点名称与预算数字。\n行程事实：" + json.dumps(facts, ensure_ascii=False)
        )
        result = self.llm.try_generate_json(prompt)
        cards = result.get("cards") if isinstance(result, dict) else None
        if not isinstance(cards, list) or not cards:
            return None
        valid = [
            card
            for card in cards
            if isinstance(card, dict)
            and all(isinstance(card.get(k), str) and card.get(k, "").strip() for k in ("gave_up", "got", "reason"))
        ]
        return valid or None

    # ---------- C3 虚拟游客 swarm ----------

    def swarm(self, job_id: str, state: dict[str, Any]) -> dict[str, Any]:
        outputs = self.load_outputs(job_id, state)
        itinerary = outputs.get("Itinerary", {}).get("payload", {}).get("itinerary", [])
        reports = []
        for index, persona in enumerate(SWARM_PERSONAS):
            day = itinerary[index % len(itinerary)] if itinerary else None
            if not day:
                continue
            spot_names = [item["spot"].get("name", item["title"]) for item in day["items"]]
            commute = day.get("commute_minutes", 0)
            reports.append(
                {
                    "persona": persona["name"],
                    "style": persona["style"],
                    "day": day["day"],
                    "theme": day["theme"],
                    "verdict": (
                        f"试玩第 {day['day']} 天（{'、'.join(spot_names)}）：全天通勤估算 {commute} 分钟。"
                        + ("对" + persona["style"] + "友好，节奏合适。" if commute <= 120 else "通勤偏长，建议减一个景点或早出发。")
                    ),
                    "tip": persona["style"] + "；热门场馆提前预约，遇拥挤按舒适度演示表错峰。",
                }
            )
        return {"job_id": job_id, "reports": reports}

    # ---------- C5 名导团 ----------

    def guides(self, job_id: str, state: dict[str, Any]) -> dict[str, Any]:
        outputs = self.load_outputs(job_id, state)
        selected = self._selected_spots(outputs)
        reviews = []
        for guide in GUIDES:
            matched = [s for s in selected if any(tag in s.get("tags", []) for tag in guide["tags"])]
            focus = matched[0] if matched else (selected[0] if selected else None)
            focus_text = (
                f"我最推荐「{focus['name']}」（开放 {focus.get('open_time', '暂无')}，门票 {focus.get('ticket_price', 0)} 元）"
                if focus
                else "行程里暂无我偏好的点位"
            )
            extra = "，另一个适合深度慢逛" if len(matched) > 1 else ""
            reviews.append(
                {
                    "id": guide["id"],
                    "name": guide["name"],
                    "persona": guide["persona"],
                    "tone": guide["tone"],
                    "review": f"{focus_text}{extra}。{guide['persona']}——这条线的取舍我认可，细节可以继续问我。",
                }
            )
        return {"job_id": job_id, "reviews": reviews}

    def dialogue(self, job_id: str, state: dict[str, Any], guide_id: str, message: str, history: list[dict[str, str]]) -> dict[str, Any]:
        guide = next((g for g in GUIDES if g["id"] == guide_id), None)
        if not guide:
            return {"job_id": job_id, "reply": "未找到该角色。", "mode": "mock"}
        outputs = self.load_outputs(job_id, state)
        facts = self._facts(state, outputs)
        reply = self._llm_dialogue(guide, facts, message, history) or self._mock_dialogue(guide, facts, message)
        return {"job_id": job_id, "guide": guide["name"], "reply": reply, "mode": "real" if self.llm.mode == "real" and self.llm.api_key else "mock"}

    def _mock_dialogue(self, guide: dict[str, Any], facts: dict[str, Any], message: str) -> str:
        selected = facts["selected_spots"]
        focus = selected[0] if selected else "核心景点"
        worst = facts.get("worst_commute")
        openers = {
            "dufu": f"（捻须）你问「{message[:20]}」——以我看，{focus}自有山河气象，",
            "foodie": f"问得好！关于「{message[:20]}」，本地人告诉你：逛完{focus}别急着走，",
            "mom": f"关于「{message[:20]}」，带娃实操建议：{focus}体力消耗不小，",
        }
        closers = {
            "dufu": "行程取舍已见于决策辩论，安心前行便是。",
            "foodie": f"分项预算 {facts['estimated_budget']} 元里餐饮按每天 150 元算，吃好不贵。",
            "mom": f"最远一段通勤（{worst['from']}→{worst['to']}）打车估算 {worst['taxi_minutes']} 分钟，记得给孩子备点零食。",
        }
        return openers.get(guide["id"], guide["persona"]) + closers.get(guide["id"], "")

    def _llm_dialogue(self, guide: dict[str, Any], facts: dict[str, Any], message: str, history: list[dict[str, str]]) -> str | None:
        prompt = (
            f"你扮演「{guide['name']}」（{guide['persona']}，语气{guide['tone']}）为用户解答行程疑问。"
            "只能基于给定行程事实回答，不要编造数据。"
            "输出 JSON：{\"reply\": str}，回复不超过 120 字。\n"
            f"对话历史：{json.dumps(history[-6:], ensure_ascii=False)}\n"
            f"用户最新问题：{message}\n行程事实：{json.dumps(facts, ensure_ascii=False)}"
        )
        result = self.llm.try_generate_json(prompt)
        reply = result.get("reply") if isinstance(result, dict) else None
        return reply if isinstance(reply, str) and reply.strip() else None

    # ---------- C6 直播辩论 ----------

    def live_rounds(self, job_id: str, state: dict[str, Any]) -> list[dict[str, Any]]:
        outputs = self.load_outputs(job_id, state)
        debates = outputs.get("Debate", {}).get("payload", {}).get("debates", [])
        messages: list[dict[str, Any]] = []
        llm_rounds = self._llm_live_rounds(state, outputs)
        if llm_rounds:
            for index, text in enumerate(llm_rounds):
                messages.append({"seq": index + 1, "side": "规划方" if index % 2 == 0 else "游客方", "text": text})
            return messages
        for round_index, debate in enumerate(debates, start=1):
            messages.append({"seq": len(messages) + 1, "side": "规划方", "text": f"【{debate['topic']}】{debate['plan_side']['point']}"})
            messages.append({"seq": len(messages) + 1, "side": "游客方", "text": f"我不完全同意：{debate['traveler_side']['point']}——这个诉求必须被听到。"})
            messages.append(
                {
                    "seq": len(messages) + 1,
                    "side": "规划方",
                    "text": f"接受你的诉求，但数据在这：{debate['verdict']['reason']}所以最终定为「{debate['verdict']['decision']}」。",
                }
            )
        return messages

    def _llm_live_rounds(self, state: dict[str, Any], outputs: dict[str, dict[str, Any]]) -> list[str] | None:
        facts = self._facts(state, outputs)
        prompt = (
            "基于行程事实写一场规划方与游客方的直播辩论，共 8 句话，双方交替（规划方先手），"
            "每句不超过 60 字，引用具体景点与数字，最后一句规划方总结。"
            "输出 JSON：{\"lines\": [str, ...]}。\n行程事实：" + json.dumps(facts, ensure_ascii=False)
        )
        result = self.llm.try_generate_json(prompt)
        lines = result.get("lines") if isinstance(result, dict) else None
        if not isinstance(lines, list):
            return None
        valid = [line for line in lines if isinstance(line, str) and line.strip()]
        return valid if len(valid) >= 4 else None

    def cast_vote(self, job_id: str, state: dict[str, Any], store: Any, side: str) -> dict[str, Any]:
        votes = state.setdefault("debate_votes", {"规划方": 0, "游客方": 0})
        if side in votes:
            votes[side] += 1
        store.save(job_id, state)
        store.append_audit(job_id, {"action": "debate_vote", "side": side})
        self._rewrite_md_votes(job_id, votes)
        return {"job_id": job_id, "votes": votes}

    def _rewrite_md_votes(self, job_id: str, votes: dict[str, int]) -> None:
        path = job_dir(job_id) / "travel_plan.md"
        if not path.exists():
            return
        markdown = path.read_text(encoding="utf-8")
        markdown = re.sub(r"## 9\. 直播辩论观众投票[\s\S]*?(?=\n## |\Z)", "", markdown).rstrip() + "\n"
        section = (
            "\n## 9. 直播辩论观众投票\n\n"
            f"- 规划方：{votes.get('规划方', 0)} 票\n"
            f"- 游客方：{votes.get('游客方', 0)} 票\n"
            f"- 更新时间：{datetime.now(timezone.utc).isoformat()}\n"
        )
        digest = self.writer.write_text(path, markdown + section)
        state_path = job_dir(job_id) / "state.json"
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state["file_hash"] = digest
                self.writer.write_json(state_path, state)
            except (OSError, json.JSONDecodeError):
                pass
