import math

from django.db import transaction
from django.utils import timezone
from gurobipy import GRB

from .models import (
    Request, contamination_flag_result, cumulative_flow_time_result, excess_result,
    gap_result, intransit_flag_result, lead_time_result, objective_summary,
    price_result, salmonella_node_result, shelf_time_result, var_x, var_y,
)
from .optimizer import solve


RESULT_MODELS = (
    var_y, var_x, gap_result, excess_result, objective_summary, lead_time_result,
    cumulative_flow_time_result, shelf_time_result, price_result,
    salmonella_node_result, contamination_flag_result, intransit_flag_result,
)


def _value(expression):
    return float(expression.getValue())


def _solver_value(variable):
    """Return a nonzero real value that EncryptedFloatField can persist."""
    value = float(variable.X)
    if not math.isfinite(value) or abs(value) >= GRB.INFINITY or abs(value) <= 1e-9:
        return None
    return value


def _clear_results(record):
    for model in RESULT_MODELS:
        model.objects.filter(request=record).delete()


def execute_optimization(record):
    """Solve one saved request and persist the same result rows as the legacy view."""
    result = solve(record)
    model = result["model"]
    status_name = {
        GRB.OPTIMAL: "OPTIMAL", GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INTERRUPTED: "INTERRUPTED", GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD", GRB.UNBOUNDED: "UNBOUNDED",
    }.get(model.Status, f"STATUS_{model.Status}")

    if model.SolCount == 0:
        record.status = "FAILED"
        record.solver_status = status_name
        record.solver_message = "The solver did not produce a feasible solution."
        record.runtime_seconds = result["metrics"]["runtime_seconds"]
        record.cpu_seconds = result["metrics"]["cpu_seconds"]
        record.finished_at = timezone.now()
        record.save()
        return False

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
            value = _solver_value(variable)
            if value is not None:
                salmonella_node_result.objects.create(
                    request=record, product=product, node=node, value=value,
                )
        for (product, node), variable in result["Z"].items():
            contamination_flag_result.objects.create(request=record, product=product, node=node, value=int(round(variable.X)))
        for (product, node), variable in result["Z_intransit"].items():
            intransit_flag_result.objects.create(request=record, product=product, node=node, value=int(round(variable.X)))
        objective_summary.objects.create(
            request=record, objective_value=model.ObjVal,
            total_profit=_value(result["real_profit"]), total_revenue=_value(result["revenue"]),
            total_transport_cost=_value(result["transport_cost"]), total_gap_cost=_value(result["gap_cost"]),
            total_excess_cost=_value(result["excess_cost"]), artificial_cost=_value(result["artificial_cost"]),
            fixed_diversion_cost=_value(result["fixed_diversion_cost"]),
            variable_diversion_cost=_value(result["variable_diversion_cost"]),
        )
        record.status = "DONE"
        record.solver_status = status_name
        record.solver_message = ""
        record.runtime_seconds = result["metrics"]["runtime_seconds"]
        record.cpu_seconds = result["metrics"]["cpu_seconds"]
        record.best_incumbent_seconds = result["metrics"]["best_seconds"]
        record.best_bound = model.ObjBound
        record.mip_gap = model.MIPGap
        record.finished_at = timezone.now()
        record.save()
    return True
