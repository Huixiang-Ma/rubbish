import json
from typing import Any

from app.agents.base import AgentBase

MOOD_THEMES = {
    "治愈": {"theme": "舒缓疗愈之旅", "emotion": "松弛、被安抚"},
    "放松": {"theme": "舒缓疗愈之旅", "emotion": "松弛、自在"},
    "刺激": {"theme": "元气探险之旅", "emotion": "兴奋、跃跃欲试"},
    "文化": {"theme": "文化沉浸之旅", "emotion": "沉浸、敬畏"},
    "历史": {"theme": "文化沉浸之旅", "emotion": "沉浸、怀古"},
    "亲子": {"theme": "亲子陪伴之旅", "emotion": "温暖、惊喜"},
    "浪漫": {"theme": "城市漫游之旅", "emotion": "心动、悠然"},
}


class MoodAgent(AgentBase):
    """C7 输入心情 → 人生剧本：情绪弧线叙事。仅在用户填写 mood 时进入管线。"""

    name = "Mood"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        mood = str(context["user_input"].get("mood") or "").strip()
        days = context["user_input"]["days"]
        plan_days = context["outputs"]["Planner"]["payload"]["days"]
        arc = self._mock_arc(mood, days, plan_days)
        return {
            "agent": self.name,
            "status": "ok",
            "payload": {"mood": mood, "theme": arc["theme"], "phases": arc["phases"]},
        }

    def _mock_arc(self, mood: str, days: int, plan_days: list[dict[str, Any]]) -> dict[str, Any]:
        preset = next((preset for keyword, preset in MOOD_THEMES.items() if keyword in mood), None)
        if preset:
            theme, base_emotion = preset["theme"], preset["emotion"]
        else:
            theme, base_emotion = "心灵共鸣之旅", "期待、被理解"
        phases = []
        structure = ["启程 · 期待", "投入 · 沉浸", "回味 · 安放"]
        for day in plan_days:
            phase = structure[min(day["day"] - 1, len(structure) - 1)]
            spot_names = "、".join(day["spot_names"][:2]) or "城市街巷"
            phases.append(
                {
                    "day": day["day"],
                    "phase": phase,
                    "emotion": base_emotion,
                    "narration": (
                        f"带着「{mood}」的心情走进第 {day['day']} 天的 {day['theme']}——"
                        f"{spot_names}不是终点，而是让心情落地的场景。"
                    ),
                }
            )
        return {"theme": theme, "phases": phases}

    def _llm_arc(self, mood: str, days: int, context: dict[str, Any]) -> dict[str, Any] | None:
        plan_days = context["outputs"]["Planner"]["payload"]["days"]
        outline = [{"day": day["day"], "theme": day["theme"], "spots": day["spot_names"]} for day in plan_days]
        prompt = (
            f"用户带着「{mood}」的心情旅行 {days} 天。基于给定每日安排，写一条情绪弧线人生剧本："
            "输出 JSON：{\"theme\": str, \"phases\": [{\"day\": int, \"phase\": str, \"emotion\": str, \"narration\": str}]}，"
            "phases 每天一条，narration 为第二人称叙事且不超过 60 字，必须引用当日景点名。\n"
            "每日安排：" + json.dumps(outline, ensure_ascii=False)
        )
        result = self.llm.try_generate_json(prompt)
        if not isinstance(result, dict) or not isinstance(result.get("phases"), list) or not result["phases"]:
            return None
        phases = [
            phase
            for phase in result["phases"]
            if isinstance(phase, dict) and isinstance(phase.get("narration"), str) and phase["narration"].strip()
        ]
        if not phases:
            return None
        return {"theme": str(result.get("theme", "心灵共鸣之旅")), "phases": phases}
