from pathlib import Path

from app.config import get_settings

settings = get_settings()
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = Path(settings.data_root) if settings.data_root else PROJECT_ROOT / "data" / "jobs"
STATIC_DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


def job_dir(job_id: str) -> Path:
    return DATA_ROOT / job_id


def agent_output_dir(job_id: str) -> Path:
    return job_dir(job_id) / "agent_outputs"
