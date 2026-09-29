"""APScheduler wiring.

Every job runs through run_job so it lands in job_runs and never crashes the scheduler.
"""

import logging
from collections.abc import Callable
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.time import utcnow
from app.models.audit import JobRun
from app.models.org import RefreshToken

log = logging.getLogger("floorpulse.jobs")

JobFn = Callable[[Session], str | None]


def run_job(name: str, fn: JobFn) -> None:
    with SessionLocal() as db:
        run = JobRun(job_name=name)
        db.add(run)
        db.commit()
        try:
            detail = fn(db)
            db.commit()
            run.status, run.detail = "ok", detail
        except Exception as e:
            db.rollback()
            log.exception("job failed", extra={"job": name})
            run.status, run.detail = "error", repr(e)[:2000]
        run.finished_at = utcnow()
        db.add(run)
        db.commit()


def purge_expired_refresh_tokens(db: Session) -> str:
    cutoff = utcnow() - timedelta(days=7)
    res = db.execute(delete(RefreshToken).where(RefreshToken.expires_at < cutoff))
    return f"deleted {res.rowcount}"  # type: ignore[attr-defined]


# (name, fn, trigger kwargs). Later phases append here.
JOBS: list[tuple[str, JobFn, dict[str, object]]] = [
    ("purge_refresh_tokens", purge_expired_refresh_tokens, {"trigger": "cron", "hour": 3, "minute": 17}),
]


def start_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone="UTC", job_defaults={"coalesce": True, "max_instances": 1})
    for name, fn, trig in JOBS:
        sched.add_job(run_job, args=[name, fn], id=name, replace_existing=True, **trig)
    sched.start()
    return sched
