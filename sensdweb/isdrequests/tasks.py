from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.db import transaction
from django.utils import timezone

from .models import Request
from .services import execute_optimization


def _mark_failed(request_id, message, solver_status="ERROR"):
    Request.objects.filter(pk=request_id).update(
        status="FAILED",
        solver_status=solver_status,
        solver_message=str(message)[:4000],
        finished_at=timezone.now(),
        updated_at=timezone.now(),
    )


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=3900,
    time_limit=3960,
)
def run_optimization_task(self, request_id):
    # Lock the row while claiming it. A duplicate delivery becomes a no-op.
    with transaction.atomic():
        record = Request.objects.select_for_update().get(pk=request_id)
        if record.status != "QUEUED":
            return {"request_id": request_id, "status": record.status, "skipped": True}
        record.status = "RUNNING"
        record.solver_status = "RUNNING"
        record.solver_message = ""
        record.started_at = timezone.now()
        record.finished_at = None
        record.save(update_fields=[
            "status", "solver_status", "solver_message", "started_at",
            "finished_at", "updated_at",
        ])

    try:
        completed = execute_optimization(record)
        record.refresh_from_db(fields=["status", "solver_status"])
        return {"request_id": request_id, "status": record.status, "completed": completed}
    except SoftTimeLimitExceeded:
        _mark_failed(request_id, "Optimization exceeded the worker time limit.", "TIME_LIMIT")
        raise
    except Exception as exc:
        _mark_failed(request_id, exc)
        raise
