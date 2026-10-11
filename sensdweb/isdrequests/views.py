import io

import pandas as pd
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import Request
from .optimizer import MODEL_VERSION
from .tasks import run_optimization_task
from .workbook import WorkbookValidationError, parse_workbook, persist_workbook


def _owned_request(request, request_id):
    return get_object_or_404(Request, pk=request_id, requested_by=request.user)


@require_http_methods(["GET"])
def home(request):
    return render(request, "isdrequests/isdUploadExcel.html", {"model_version": MODEL_VERSION})


@require_http_methods(["POST"])
def preview_excel(request):
    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"status": "error", "message": "Choose an Excel workbook."}, status=400)
    try:
        parsed = parse_workbook(upload)
        return JsonResponse({"status": "success", "preview_data": parsed.preview(), "model_version": MODEL_VERSION})
    except WorkbookValidationError as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=400)


@require_http_methods(["POST"])
def save_excel(request):
    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"status": "error", "message": "Choose an Excel workbook."}, status=400)
    try:
        parsed = parse_workbook(upload)
        with transaction.atomic():
            record = Request.objects.create(
                requested_by=request.user, title="SENS-D Midwest Distribution Request",
                original_filename=upload.name, status="SAVED", model_version=MODEL_VERSION,
            )
            persist_workbook(parsed, record)
        return JsonResponse({"status": "success", "request_id": record.pk})
    except WorkbookValidationError as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({"status": "error", "message": f"The workbook could not be saved: {exc}"}, status=400)


@require_http_methods(["POST"])
def run_optimization(request):
    request_id = request.POST.get("request_id")
    if not request_id:
        messages.error(request, "Save and validate a workbook before running optimization.")
        return redirect("isdrequests_home")
    with transaction.atomic():
        record = get_object_or_404(
            Request.objects.select_for_update(),
            pk=request_id,
            requested_by=request.user,
        )
        if record.status in {"QUEUED", "RUNNING"}:
            messages.warning(request, f"Request #{record.pk} is already {record.status.lower()}.")
            return redirect("requests_list")
        if record.status not in {"SAVED", "FAILED", "DONE"}:
            messages.error(request, "This request must be saved before it can be optimized.")
            return redirect("requests_list")
        record.status = "QUEUED"
        record.solver_status = "QUEUED"
        record.solver_message = "Waiting for the optimization worker."
        record.queued_at = timezone.now()
        record.started_at = None
        record.finished_at = None
        record.save(update_fields=[
            "status", "solver_status", "solver_message", "queued_at",
            "started_at", "finished_at", "updated_at",
        ])
    try:
        run_optimization_task.delay(record.pk)
    except Exception:
        Request.objects.filter(pk=record.pk, status="QUEUED").update(
            status="FAILED", solver_status="QUEUE_ERROR",
            solver_message="The optimization worker could not be reached. Please try again.",
            finished_at=timezone.now(), updated_at=timezone.now(),
        )
        messages.error(request, "The optimization queue is unavailable. Please try again shortly.")
        return redirect("requests_list")

    messages.success(request, f"Request #{record.pk} was added to the optimization queue.")
    return redirect("requests_list")


@require_http_methods(["GET"])
def optimization_status(request, req_id):
    record = _owned_request(request, req_id)
    payload = {
        "request_id": record.pk,
        "status": record.status,
        "solver_status": record.solver_status,
        "message": record.solver_message or "",
        "terminal": record.status in {"DONE", "FAILED"},
    }
    if record.status == "DONE":
        payload["result_url"] = reverse("results_view", args=[record.pk])
    return JsonResponse(payload)


@require_http_methods(["GET"])
def requests_list(request):
    return render(request, "isdrequests/isdrequests.html", {"rows": Request.objects.filter(requested_by=request.user).order_by("-created_at")})


@require_http_methods(["GET"])
def results_view(request, req_id):
    record = _owned_request(request, req_id)
    return render(request, "isdrequests/isdresults.html", {
        "req": record, "summary": getattr(record, "summary", None), "y_rows": record.y_vars.all(),
        "x_rows": record.x_vars.all(), "gaps": record.gaps.all(), "excess": record.excesses.all(),
        "lead_times": record.lead_times.all(), "flow_times": record.flow_times.all(),
        "shelf_times": record.shelf_times.all(), "prices": record.prices.all(),
        "salmonella_nodes": record.salmonella_nodes.all(),
        "contamination_flags": record.contamination_flags.all(), "intransit_flags": record.intransit_flags.all(),
    })


def _rows(queryset, fields):
    return [{heading: getattr(item, attribute) for heading, attribute in fields.items()} for item in queryset]


@require_http_methods(["GET"])
def results_download_excel(request, req_id):
    record = _owned_request(request, req_id)
    output, summary = io.BytesIO(), getattr(record, "summary", None)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if summary:
            pd.DataFrame([{
                "Solver status": record.solver_status, "Objective": summary.objective_value,
                "Best bound": record.best_bound, "MIP gap": record.mip_gap,
                "Runtime seconds": record.runtime_seconds, "CPU seconds": record.cpu_seconds,
                "Time to best incumbent": record.best_incumbent_seconds, "Real profit": summary.total_profit,
                "Revenue": summary.total_revenue, "Transport cost": summary.total_transport_cost,
                "Artificial cost": summary.artificial_cost, "Gap cost": summary.total_gap_cost,
                "Excess cost": summary.total_excess_cost, "Fixed diversion cost": summary.fixed_diversion_cost,
                "Variable diversion cost": summary.variable_diversion_cost,
            }]).to_excel(writer, sheet_name="Summary", index=False)
        exports = (
            ("Y_modes", record.y_vars.all(), {"product_in": "product", "node_i": "node_i", "product_out": "product_div", "node_j": "node_j", "mode": "mode", "selected": "value"}),
            ("X_flows", record.x_vars.all(), {"product_in": "product", "node_i": "node_i", "product_out": "product_div", "node_j": "node_j", "mode": "mode", "quantity": "quantity"}),
            ("Gap", record.gaps.all(), {"product": "product", "market": "market", "gap": "gap"}),
            ("Excess", record.excesses.all(), {"product": "product", "market": "market", "excess": "excess"}),
            ("W_lead_time", record.lead_times.all(), {"product_in": "product_in", "node_i": "node_i", "product_out": "product_out", "node_j": "node_j", "lead_time": "lead_time"}),
            ("F_flow_time", record.flow_times.all(), {"product": "product", "node": "node", "flow_time": "flow_time"}),
            ("T_shelf_time", record.shelf_times.all(), {"product": "product", "market": "market", "shelf_time": "shelf_time"}),
            ("pi_prices", record.prices.all(), {"product": "product", "market": "market", "price": "price"}),
            ("Salmonella_nodes", record.salmonella_nodes.all(), {"product": "product", "node": "node", "value": "value"}),
            ("Z_node_flags", record.contamination_flags.all(), {"product": "product", "node": "node", "value": "value"}),
            ("Z_intransit_flags", record.intransit_flags.all(), {"product": "product", "node": "node", "value": "value"}),
        )
        for sheet, queryset, fields in exports:
            pd.DataFrame(_rows(queryset, fields), columns=fields.keys()).to_excel(writer, sheet_name=sheet, index=False)
    output.seek(0)
    response = HttpResponse(output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="SENSD_Midwest_v1_request_{record.pk}.xlsx"'
    return response
