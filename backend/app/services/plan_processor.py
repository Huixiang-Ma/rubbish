import json
import traceback
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Any

from app.agents.budget import BudgetAgent
from app.agents.compliance import ComplianceAgent
from app.agents.consultant import ConsultantAgent
from app.agents.debate import DebateAgent
from app.agents.intake import IntakeAgent
from app.agents.itinerary import ItineraryAgent
from app.agents.mood import MoodAgent
from app.agents.planner import PlannerAgent
from app.agents.researcher import ResearcherAgent
from app.agents.sentiment import SentimentAgent
from app.agents.validator import ValidatorAgent
from app.models.states import JobStatus
from app.services.checkpoint_store import CheckpointStore
from app.services.jsonlog import log_event
from app.services.markdown_reporter import MarkdownReporter
from app.services.metrics import JOB_COMPLETED, JOB_FAILED, SAFETY_BLOCKED
from app.services.notify import notify_hold
from app.services.paths import job_dir
from app.services.pg_mirror import pg_mirror
from app.services.pipelines import resolve_pipeline
from app.services.safety_service import SafetyService


class PlanProcessor:
    def __init__(self) -> None:
        self.store = CheckpointStore()
        self.reporter = MarkdownReporter()
        self.safety = SafetyService()
        # toC/toB 双管线：底层能力共享（Researcher/Planner/Itinerary/Validator），上层 Agent 按方向分叉
        self.pipelines: dict[str, list] = {
            "toc": [
                IntakeAgent(),
                ResearcherAgent(),
                PlannerAgent(),
                ItineraryAgent(),
                BudgetAgent(),
                ValidatorAgent(),
                SentimentAgent(),
                DebateAgent(),
                MoodAgent(),
            ],
            "tob": [
                IntakeAgent(),
                ResearcherAgent(),
                PlannerAgent(),
                ItineraryAgent(),
                BudgetAgent(),
                ValidatorAgent(),
                SentimentAgent(),
                ConsultantAgent(),
                ComplianceAgent(),
            ],
        }
        self._locks: dict[str, Lock] = {}
        self._guard = Lock()

    def process(self, job_id: str) -> None:
        lock = self._get_lock(job_id)
        if not lock.acquire(blocking=False):
            return
        try:
            state = self.store.load(job_id)
            if state["status"] == JobStatus.COMPLETED.value:
                return
            # 旧任务 state 无 pipeline 字段时按 user_input 重新判定方向
            resolved_key, _ = resolve_pipeline(state["user_input"])
            pipeline_key = state.get("pipeline", resolved_key)
            agents = self.pipelines[pipeline_key]
            context: dict[str, Any] = {"user_input": state["user_input"], "outputs": {}, "pipeline": pipeline_key}
            self._load_completed_outputs(job_id, state, context)
            scan = self.safety.scan_user_input(str(state["user_input"]))
            self.store.append_audit(
                job_id,
                {
                    "action": "safety_scan",
                    "risk_level": scan.risk_level,
                    "scan_action": scan.action,
                    "evidence": scan.evidence,
                },
            )
            if scan.action == "block" and not state.get("safety_reviewed"):
                self.store.append_audit(
                    job_id,
                    {
                        "action": "safety_block",
                        "risk_level": scan.risk_level,
                        "evidence": scan.evidence,
                    },
                )
                SAFETY_BLOCKED.inc()
                pg_mirror.record_safety(job_id, scan.risk_level, "block", scan.evidence)
                log_event("safety_block", job_id=job_id, evidence=scan.evidence)
                notify_hold(job_id, "待安全审核", "输入包含高风险 Prompt 注入内容")
                self.store.mark_failed(job_id, "输入包含高风险 Prompt 注入内容。", JobStatus.WAITING_SAFETY_REVIEW)
                return
            start_from = state.get("resume_from") or agents[0].name
            completed_nodes = list(state.get("completed_nodes", []))
            # 尾段 Agent（Debate/Mood/Consultant/Compliance）互不依赖，可并行执行
            tail_agents = [agent for agent in agents if agent.name in self.TAIL_PARALLEL_NAMES]
            core_agents = [agent for agent in agents if agent.name not in self.TAIL_PARALLEL_NAMES]
            should_run = False
            for index, agent in enumerate(core_agents):
                if agent.name == start_from or agent.name not in completed_nodes:
                    should_run = True
                if not should_run:
                    continue
                # 工单 7 · 防脏读：节点边界重读 state，消费运行态干预队列（热替换 user_input）
                latest = self.store.load(job_id)
                pending_interventions = latest.pop("interventions", None)
                if pending_interventions:
                    for iv in pending_interventions:
                        self.store.append_audit(
                            job_id,
                            {
                                "action": "intervention_applied",
                                "field": iv.get("field"),
                                "changes": iv.get("changes"),
                                "operator": iv.get("operator"),
                                "reason": iv.get("reason"),
                            },
                        )
                    if latest["user_input"] != context["user_input"]:
                        context["user_input"] = latest["user_input"]
                        log_event("intervention_consumed", job_id=job_id,
                                  fields=[iv.get("field") for iv in pending_interventions])
                self.store.mark_running(job_id, agent.name, min(index * 15 + 8, 82))
                result = agent.run(context)
                # 外部抓取内容安全过滤：递归扫描 Agent 输出，高风险替换/中风险清洗，全部写审计
                result, safety_events = self.safety.scan_payload(result)
                for event in safety_events:
                    self.store.append_audit(
                        job_id,
                        {
                            "action": event["action"],
                            "risk_level": event["risk_level"],
                            "agent": agent.name,
                            "evidence": event["evidence"],
                        },
                    )
                    if event["action"] == "web_content_block":
                        SAFETY_BLOCKED.inc()
                        pg_mirror.record_safety(job_id, "high", "block", event["evidence"])
                context["outputs"][agent.name] = result
                state = self.store.mark_node_done(job_id, agent.name, result, min(index * 15 + 23, 88))
                if agent.name == "Intake" and result["payload"].get("normalized_input"):
                    context["user_input"] = result["payload"]["normalized_input"]
                if agent.name == "Budget" and result["payload"].get("approval_required"):
                    state["status"] = JobStatus.WAITING_BUDGET_APPROVAL.value
                    state["current_node"] = None
                    self.store.save(job_id, state)
                    self.store.append_audit(
                        job_id,
                        {
                            "action": "budget_approval_required",
                            "estimated_budget": result["payload"].get("estimated_budget"),
                            "budget": context["user_input"].get("budget"),
                        },
                    )
                    log_event("budget_hold", job_id=job_id, estimated_budget=result["payload"].get("estimated_budget"))
                    notify_hold(job_id, "待预算审批", "预估预算超出用户预算")
                    return
            self._run_tail(job_id, tail_agents, start_from, completed_nodes, context)
            self.store.mark_running(job_id, "Reporter", 90)
            digest = self.reporter.render_and_write(job_id, context)
            self.store.mark_node_done(
                job_id,
                "Reporter",
                {"agent": "Reporter", "status": "ok", "payload": {"sha256": digest}},
                95,
            )
            self.store.mark_completed(job_id, digest)
            JOB_COMPLETED.inc()
            log_event("job_completed", job_id=job_id, pipeline=pipeline_key)
        except Exception as exc:
            JOB_FAILED.inc()
            log_event("job_failed", job_id=job_id, error=str(exc), traceback=traceback.format_exc())
            self.store.mark_failed(job_id, str(exc))
        finally:
            lock.release()

    TAIL_PARALLEL_NAMES = {"Debate", "Mood", "Consultant", "Compliance"}

    def _run_tail(
        self,
        job_id: str,
        tail_agents: list,
        start_from: str | None,
        completed_nodes: list[str],
        context: dict[str, Any],
    ) -> None:
        """执行尾段 Agent：全部未完成时并行跑（LLM 调用互不依赖）；部分完成（断点恢复）时顺序补跑。"""
        remaining = [
            agent
            for agent in tail_agents
            if agent.name not in completed_nodes and not (agent.name == "Mood" and not context["user_input"].get("mood"))
        ]
        if not remaining:
            return
        if len(remaining) == len(tail_agents):
            self.store.mark_running(job_id, remaining[0].name, 70)
            with ThreadPoolExecutor(max_workers=len(remaining)) as pool:
                results = list(pool.map(lambda agent: agent.run(context), remaining))
            for agent, result in zip(remaining, results):
                result, safety_events = self.safety.scan_payload(result)
                for event in safety_events:
                    self.store.append_audit(
                        job_id,
                        {
                            "action": event["action"],
                            "risk_level": event["risk_level"],
                            "agent": agent.name,
                            "evidence": event["evidence"],
                        },
                    )
                    if event["action"] == "web_content_block":
                        SAFETY_BLOCKED.inc()
                        pg_mirror.record_safety(job_id, "high", "block", event["evidence"])
                context["outputs"][agent.name] = result
                self.store.mark_node_done(job_id, agent.name, result, 85)
            return
        # 断点恢复：尾段已有部分完成节点，按序补跑剩余
        for agent in remaining:
            self.store.mark_running(job_id, agent.name, 78)
            result = agent.run(context)
            result, safety_events = self.safety.scan_payload(result)
            for event in safety_events:
                self.store.append_audit(
                    job_id,
                    {
                        "action": event["action"],
                        "risk_level": event["risk_level"],
                        "agent": agent.name,
                        "evidence": event["evidence"],
                    },
                )
                if event["action"] == "web_content_block":
                    SAFETY_BLOCKED.inc()
                    pg_mirror.record_safety(job_id, "high", "block", event["evidence"])
            context["outputs"][agent.name] = result
            self.store.mark_node_done(job_id, agent.name, result, 85)

    def _load_completed_outputs(self, job_id: str, state: dict[str, Any], context: dict[str, Any]) -> None:
        for agent_name, relative_path in state.get("agent_outputs", {}).items():
            output_path = job_dir(job_id) / relative_path
            if output_path.exists():
                context["outputs"][agent_name] = json.loads(output_path.read_text(encoding="utf-8"))

    def _get_lock(self, job_id: str) -> Lock:
        with self._guard:
            if job_id not in self._locks:
                self._locks[job_id] = Lock()
            return self._locks[job_id]


plan_processor = PlanProcessor()
