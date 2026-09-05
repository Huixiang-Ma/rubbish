import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.states import JobStatus
from app.services.atomic_writer import AtomicWriter
from app.services import job_index
from app.services.pg_mirror import pg_mirror
from app.services.paths import agent_output_dir, job_dir
from app.services.pipelines import DEFAULT_PIPELINE, resolve_pipeline


class CheckpointStore:
    def __init__(self) -> None:
        self.writer = AtomicWriter()

    def create(self, job_id: str, user_input: dict[str, Any], request_hash: str) -> dict[str, Any]:
        directory = job_dir(job_id)
        (directory / "agent_outputs").mkdir(parents=True, exist_ok=True)
        pipeline_key, pipeline_nodes = resolve_pipeline(user_input)
        state = {
            "job_id": job_id,
            "request_hash": request_hash,
            "user_input": user_input,
            "pipeline": pipeline_key,
            "pipeline_nodes": pipeline_nodes,
            "status": JobStatus.QUEUED.value,
            "current_node": None,
            "last_success_node": None,
            "resume_from": "Researcher",
            "completed_nodes": [],
            "agent_outputs": {},
            "progress": 0,
            "version": 1,
            "error": None,
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        self.save(job_id, state)
        return state

    def state_path(self, job_id: str) -> Path:
        return job_dir(job_id) / "state.json"

    def exists(self, job_id: str) -> bool:
        return self.state_path(job_id).exists()

    def load(self, job_id: str) -> dict[str, Any]:
        path = self.state_path(job_id)
        if not path.exists():
            raise FileNotFoundError(f"job not found: {job_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, job_id: str, state: dict[str, Any]) -> str:
        state["updated_at"] = self._now()
        digest = self.writer.write_json(self.state_path(job_id), state)
        pg_mirror.record_job(state)
        job_index.invalidate(job_id)
        return digest

    def save_agent_output(self, job_id: str, agent_name: str, output: dict[str, Any]) -> str:
        path = agent_output_dir(job_id) / f"{agent_name.lower()}.json"
        self.writer.write_json(path, output)
        return str(path.relative_to(job_dir(job_id))).replace("\\", "/")

    def mark_running(self, job_id: str, agent_name: str, progress: int) -> dict[str, Any]:
        state = self.load(job_id)
        state["status"] = JobStatus.RUNNING.value
        state["current_node"] = agent_name
        state["resume_from"] = agent_name
        state["progress"] = progress
        self.save(job_id, state)
        return state

    def mark_node_done(self, job_id: str, agent_name: str, output: dict[str, Any], progress: int) -> dict[str, Any]:
        state = self.load(job_id)
        output_path = self.save_agent_output(job_id, agent_name, output)
        completed = state.setdefault("completed_nodes", [])
        if agent_name not in completed:
            completed.append(agent_name)
        state["agent_outputs"][agent_name] = output_path
        state["last_success_node"] = agent_name
        state["resume_from"] = self._next_node(state, agent_name)
        state["progress"] = progress
        self.save(job_id, state)
        return state

    def mark_completed(self, job_id: str, sha256: str) -> dict[str, Any]:
        state = self.load(job_id)
        state["status"] = JobStatus.COMPLETED.value
        state["current_node"] = None
        state["resume_from"] = None
        state["progress"] = 100
        state["result_path"] = "travel_plan.md"
        state["file_hash"] = sha256
        self.save(job_id, state)
        return state

    def mark_failed(self, job_id: str, error: str, status: JobStatus = JobStatus.FAILED) -> dict[str, Any]:
        state = self.load(job_id)
        state["status"] = status.value
        state["error"] = error
        self.save(job_id, state)
        return state

    def append_audit(self, job_id: str, event: dict[str, Any]) -> None:
        path = job_dir(job_id) / "audit.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        event = {"created_at": self._now(), **event}
        with path.open("a", encoding="utf-8", newline="\n") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")
        pg_mirror.record_audit(job_id, event)
        job_index.invalidate(job_id)

    def _next_node(self, state: dict[str, Any], agent_name: str) -> str | None:
        # 管线节点顺序记录在 state 中（toC/toB 分叉）；旧 state 无该字段时回退 toC 顺序
        order = state.get("pipeline_nodes") or DEFAULT_PIPELINE
        try:
            index = order.index(agent_name)
        except ValueError:
            return None
        return order[index + 1] if index + 1 < len(order) else None

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
