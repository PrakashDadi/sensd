import io

import pandas as pd
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from gurobipy import GRB

from .models import (
    Request, contamination_flag_result, cumulative_flow_time_result, excess_result, gap_result,
    intransit_flag_result, lead_time_result, objective_summary, price_result,
    salmonella_node_result, shelf_time_result, var_x, var_y,
)
from .optimizer import MODEL_VERSION, solve
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


def _value(expression):
    return float(expression.getValue())


def _clear_results(record):
    for model in (var_y, var_x, gap_result, excess_result, objective_summary, lead_time_result,
                  cumulative_flow_time_result, shelf_time_result, price_result,
                  salmonella_node_result, contamination_flag_result, intransit_flag_result):
        model.objects.filter(request=record).delete()


@require_http_methods(["POST"])
def run_optimization(request):
    request_id = request.POST.get("request_id")
    if not request_id:
        messages.error(request, "Save and validate a workbook before running optimization.")
        return redirect("isdrequests_home")
    record = _owned_request(request, request_id)
    record.status, record.solver_message = "RUNNING", ""
    record.save(update_fields=["status", "solver_message", "updated_at"])
    try:
        result = solve(record)
        model = result["model"]
        status_name = {GRB.OPTIMAL: "OPTIMAL", GRB.TIME_LIMIT: "TIME_LIMIT", GRB.INTERRUPTED: "INTERRUPTED",
                       GRB.INFEASIBLE: "INFEASIBLE", GRB.INF_OR_UNBD: "INF_OR_UNBD",
                       GRB.UNBOUNDED: "UNBOUNDED"}.get(model.Status, f"STATUS_{model.Status}")
        if model.SolCount == 0:
            record.status, record.solver_status = "FAILED", status_name
            record.solver_message = "The solver did not produce a feasible solution."
            record.runtime_seconds = result["metrics"]["runtime_seconds"]
            record.cpu_seconds = result["metrics"]["cpu_seconds"]
            record.save()
            messages.error(request, record.solver_message)
            return redirect("requests_list")

        with transaction.atomic():
            _clear_results(record)
            for (p, mode), variable in result["Y"].items():
                if variable.X > 0.5:
                    var_y.objects.create(request=record, product=p[0], node_i=p[1], product_div=p[2], node_j=p[3], mode=mode, value=1)
            for (p, mode), variable in result["X"].items():
                if abs(variable.X) > 1e-9:
                    var_x.objects.create(request=record, product=p[0], node_i=p[1], product_div=p[2], node_j=p[3], mode=mode, quantity=variable.X)
            for (product, market), variable in result["G"].items():
                if abs(variable.X) > 1e-9:
                    gap_result.objects.create(request=record, product=product, market=market, gap=variable.X)
            for (product, market), variable in result["E"].items():
                if abs(variable.X) > 1e-9:
                    excess_result.objects.create(request=record, product=product, market=market, excess=variable.X)
            for p, variable in result["W"].items():
                if abs(variable.X) > 1e-9:
                    lead_time_result.objects.create(request=record, product_in=p[0], node_i=p[1], product_out=p[2], node_j=p[3], lead_time=variable.X)
            for (product, node), variable in result["F"].items():
                if abs(variable.X) > 1e-9:
                    cumulative_flow_time_result.objects.create(request=record, product=product, node=node, flow_time=variable.X)
            for (product, market), variable in result["T"].items():
                if abs(variable.X) > 1e-9:
                    shelf_time_result.objects.create(request=record, product=product, market=market, shelf_time=variable.X)
            for (product, market), variable in result["price"].items():
                if abs(variable.X) > 1e-9:
                    price_result.objects.create(request=record, product=product, market=market, price=variable.X)
            for (product, node), variable in result["eta"].items():
                salmonella_node_result.objects.create(request=record, product=product, node=node, value=variable.X)
            for (product, node), variable in result["Z"].items():
                contamination_flag_result.objects.create(request=record, product=product, node=node, value=int(round(variable.X)))
            for (product, node), variable in result["Z_intransit"].items():
                intransit_flag_result.objects.create(request=record, product=product, node=node, value=int(round(variable.X)))
            objective_summary.objects.create(
                request=record, objective_value=model.ObjVal, total_profit=_value(result["real_profit"]),
                total_revenue=_value(result["revenue"]), total_transport_cost=_value(result["transport_cost"]),
                total_gap_cost=_value(result["gap_cost"]), total_excess_cost=_value(result["excess_cost"]),
                artificial_cost=_value(result["artificial_cost"]),
                fixed_diversion_cost=_value(result["fixed_diversion_cost"]),
                variable_diversion_cost=_value(result["variable_diversion_cost"]),
            )
            record.status, record.solver_status = "DONE", status_name
            record.runtime_seconds, record.cpu_seconds = result["metrics"]["runtime_seconds"], result["metrics"]["cpu_seconds"]
            record.best_incumbent_seconds = result["metrics"]["best_seconds"]
            record.best_bound, record.mip_gap = model.ObjBound, model.MIPGap
            record.save()
        messages.success(request, f"Optimization {status_name.lower()} for request #{record.pk}.")
        return redirect(reverse("results_view", args=[record.pk]))
    except Exception as exc:
        record.status, record.solver_status, record.solver_message = "FAILED", "ERROR", str(exc)
        record.save(update_fields=["status", "solver_status", "solver_message", "updated_at"])
        messages.error(request, f"Optimization failed: {exc}")
        return redirect("requests_list")


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
