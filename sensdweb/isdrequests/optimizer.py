"""Current Intelligent Distribution model: SENS-D Midwest v1."""

import math
import time

import gurobipy as gp
from gurobipy import GRB


MODEL_VERSION = "sensd-midwest-v1"


def _unique(values):
    return list(dict.fromkeys(value for value in values if value))


def build_model_data(request_record):
    set_rows = list(request_record.sets_rows.all())
    nodes = _unique(row.col_nodes for row in set_rows)
    sources = _unique(row.col_sources for row in set_rows)
    markets = _unique(row.col_markets for row in set_rows)
    modes = _unique(row.col_modes for row in set_rows)
    products = _unique(row.col_products for row in set_rows)
    check_sal = _unique(row.col_check_sal for row in set_rows)
    nocheck_sal = _unique(row.col_nocheck_sal for row in set_rows)

    arc_groups = [list(request_record.arcs1_rows.all()), list(request_record.arcs2_rows.all()), list(request_record.arcs3_rows.all())]
    precedences = _unique((row.product, row.node_i, row.product_div, row.node_j) for row in arc_groups[0])
    if not all((nodes, sources, markets, modes, products, precedences)):
        raise ValueError("The workbook does not contain all required sets and arcs.")

    market_demand = {(row.product, row.market): float(row.demand) for row in request_record.demand_rows.all()}
    gap_cost = {(row.product, row.market): float(row.gap_cost) for row in request_record.demand_rows.all()}
    supply_values = {}
    for row in request_record.supply_rows.all():
        for product, value in (row.row_values or {}).items():
            supply_values[(row.row_label, product)] = float(value)

    multipliers = {}
    fixed_cost = {}
    unit_cost = {}
    lead_time = {}
    capacity = {}
    for group_index, rows in enumerate(arc_groups):
        for row in rows:
            precedence = (row.product, row.node_i, row.product_div, row.node_j)
            key = (precedence, row.mode)
            if group_index == 0:
                multipliers[precedence] = float(row.multiplier)
            fixed_cost[key] = float(row.fixed_cost)
            unit_cost[key] = float(row.unit_cost)
            lead_time[key] = float(row.lead_time)
            capacity[key] = float(row.capacity)

    sensors = {
        (row.product, row.node): (float(row.sensor_value) if row.has_sensor else None)
        for row in request_record.salmonella_rows.all()
    }
    return {
        "nodes": nodes, "sources": sources, "markets": markets, "modes": modes,
        "products": products, "check_sal": check_sal, "nocheck_sal": nocheck_sal,
        "precedences": precedences, "market_demand": market_demand, "gap_cost": gap_cost,
        "supply": supply_values, "multipliers": multipliers, "fixed_cost": fixed_cost,
        "unit_cost": unit_cost, "lead_time": lead_time, "capacity": capacity, "sensors": sensors,
    }


def solve(request_record):
    data = build_model_data(request_record)
    nodes, sources, markets = data["nodes"], data["sources"], data["markets"]
    modes, products, check_sal = data["modes"], data["products"], data["check_sal"]
    precedences = data["precedences"]
    non_source_market_nodes = [node for node in nodes if node not in sources and node not in markets]
    f_pairs = _unique(
        [(p[0], p[1]) for p in precedences] + [(p[2], p[3]) for p in precedences]
    )

    alpha_values = [0.198, 0.177, 0.171]
    beta_values = [0.079, 0.126, 0.070]
    if len(modes) > len(alpha_values):
        raise ValueError("The SENS-D Midwest v1 model supports at most three transportation modes.")
    alpha = dict(zip(modes, alpha_values))
    beta = dict(zip(modes, beta_values))
    epsilon, threshold, big_m = 10.0, 15.5, 100.0

    model = gp.Model(f"SENS-D-Midwest-v1-{request_record.pk}")
    Y = {(p, mode): model.addVar(vtype=GRB.BINARY, name=f"Y_{p}_{mode}") for p in precedences for mode in modes}
    X = {(p, mode): model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"X_{p}_{mode}") for p in precedences for mode in modes}
    G = {(product, market): model.addVar(lb=0.0, name=f"G_{product}_{market}") for product in products for market in markets}
    E = {(product, market): model.addVar(lb=0.0, name=f"E_{product}_{market}") for product in products for market in markets}
    W = {p: model.addVar(lb=0.0, name=f"W_{p}") for p in precedences}
    F = {pair: model.addVar(lb=0.0, name=f"F_{pair}") for pair in f_pairs}
    T = {(product, market): model.addVar(lb=0.0, name=f"T_{product}_{market}") for product in products for market in markets}
    price = {(product, market): model.addVar(lb=0.0, name=f"pi_{product}_{market}") for product in products for market in markets}
    Z = {(product, node): model.addVar(vtype=GRB.BINARY, name=f"Z_{product}_{node}") for product in check_sal for node in nodes}
    Z_intransit = {(product, node): model.addVar(vtype=GRB.BINARY, name=f"Zin_{product}_{node}") for product in check_sal for node in nodes}
    eta_pairs = [pair for pair in f_pairs if pair[0] in check_sal]
    eta = {pair: model.addVar(lb=0.0, name=f"eta_{pair}") for pair in eta_pairs}

    for p in precedences:
        model.addConstr(gp.quicksum(Y[(p, mode)] for mode in modes) <= 1, name=f"Mode_{p}")
        model.addConstr(W[p] == gp.quicksum(data["lead_time"].get((p, mode), 0.0) * Y[(p, mode)] for mode in modes), name=f"Lead_{p}")
        for mode in modes:
            model.addConstr(X[(p, mode)] <= data["capacity"].get((p, mode), 0.0) * Y[(p, mode)], name=f"Capacity_{p}_{mode}")

    for product in products:
        for market in markets:
            required = data["market_demand"].get((product, market), 0.0)
            delivered = gp.quicksum(X[(p, mode)] for p in precedences for mode in modes if p[2] == product and p[3] == market)
            model.addConstr(delivered + G[(product, market)] - E[(product, market)] == required, name=f"Demand_{product}_{market}")
        for source in sources:
            outgoing = gp.quicksum(
                X[(p, mode)] * data["multipliers"].get(p, 1.0)
                for p in precedences for mode in modes if p[0] == product and p[1] == source
            )
            model.addConstr(outgoing <= data["supply"].get((source, product), 0.0), name=f"Supply_{product}_{source}")
        for node in non_source_market_nodes:
            outgoing = gp.quicksum(X[(p, mode)] for p in precedences for mode in modes if p[0] == product and p[1] == node)
            incoming = gp.quicksum(data["multipliers"].get(p, 1.0) * X[(p, mode)] for p in precedences for mode in modes if p[2] == product and p[3] == node)
            model.addConstr(outgoing == incoming, name=f"Balance_{product}_{node}")

    for p in precedences:
        model.addConstr(F[(p[2], p[3])] - F[(p[0], p[1])] >= W[p], name=f"FlowTime_{p}")
    for product in products:
        for market in markets:
            flow = F.get((product, market))
            if flow is None:
                model.addConstr(T[(product, market)] == 10.0, name=f"Shelf_{product}_{market}")
            else:
                model.addConstr(T[(product, market)] == -0.2 * flow + 10.0, name=f"Shelf_{product}_{market}")
            model.addConstr(price[(product, market)] == 0.5 * T[(product, market)] + 20.0, name=f"Price_{product}_{market}")

    sensors = data["sensors"]
    for p in precedences:
        origin, destination = (p[0], p[1]), (p[2], p[3])
        if origin in eta and destination in eta:
            growth = gp.quicksum(
                (alpha[mode] * data["lead_time"].get((p, mode), 0.0) + beta[mode]) * Y[(p, mode)]
                for mode in modes
            )
            sensor_presence = 1.0 if sensors.get(origin) is not None else 0.0
            model.addConstr(eta[destination] >= eta[origin] + growth - big_m * sensor_presence, name=f"SalGrowth_{p}")
    for pair, variable in eta.items():
        sensor_value = sensors.get(pair)
        if sensor_value is not None:
            model.addConstr(variable >= sensor_value, name=f"Sensor_{pair}")
        model.addConstr(variable <= threshold + big_m * Z_intransit[pair], name=f"TransitUpper_{pair}")
        model.addConstr(variable >= threshold + 1e-3 - big_m * (1 - Z_intransit[pair]), name=f"TransitLower_{pair}")
    for key, variable in Z.items():
        sensor_value = sensors.get(key)
        if sensor_value is None:
            model.addConstr(variable == 0, name=f"NoSensor_{key}")
        else:
            model.addConstr(big_m * variable >= sensor_value - threshold, name=f"NodeFlag_{key}")
    for p in precedences:
        origin = (p[0], p[1])
        for mode in modes:
            if p[0] in check_sal and p[0] == p[2]:
                model.addConstr(X[(p, mode)] <= (1 - Z[origin]) * data["capacity"].get((p, mode), 0.0), name=f"NoContamFlow_{p}_{mode}")
            if origin in Z_intransit:
                model.addConstr(Y[(p, mode)] <= 1 - Z_intransit[origin], name=f"NoContamMode_{p}_{mode}")

    revenue = gp.quicksum(
        1.5 * price[(product, market)] * X[(p, mode)]
        for product in products for market in markets for mode in modes for p in precedences
        if p[3] == market and p[0] == product
    )
    transport_cost = gp.quicksum(
        data["fixed_cost"].get((p, mode), 0.0) * Y[(p, mode)] + data["unit_cost"].get((p, mode), 0.0) * X[(p, mode)]
        for p in precedences for mode in modes
    )
    artificial_cost = epsilon * gp.quicksum(F.values())
    total_gap_cost = gp.quicksum(10.0 * data["gap_cost"].get((product, market), 0.0) * G[(product, market)] for product in products for market in markets)
    total_excess_cost = gp.quicksum(1.1 * price[(product, market)] * E[(product, market)] for product in products for market in markets)
    fixed_diversion_cost = gp.quicksum(data["fixed_cost"].get((p, mode), 0.0) * Y[(p, mode)] for p in precedences for mode in modes if p[0] != p[2])
    variable_diversion_cost = gp.quicksum(data["unit_cost"].get((p, mode), 0.0) * X[(p, mode)] for p in precedences for mode in modes if p[0] != p[2])
    real_profit = revenue - transport_cost
    objective = revenue - transport_cost - artificial_cost - total_gap_cost - total_excess_cost
    model.setObjective(objective, GRB.MAXIMIZE)
    model.setParam("MIPGap", 0.01)
    from django.conf import settings

    model.setParam("TimeLimit", settings.GUROBI_TIME_LIMIT)
    model.setParam("Threads", settings.GUROBI_THREADS)
    model.setParam("OutputFlag", settings.GUROBI_OUTPUT_FLAG)

    metrics = {"start_cpu": time.process_time(), "start_wall": time.perf_counter(), "best_obj": -math.inf, "best_seconds": None}
    def callback(active_model, where):
        if where == GRB.Callback.MIP:
            incumbent = active_model.cbGet(GRB.Callback.MIP_OBJBST)
            if incumbent < GRB.INFINITY and incumbent > metrics["best_obj"] + 1e-9:
                metrics["best_obj"] = incumbent
                metrics["best_seconds"] = time.perf_counter() - metrics["start_wall"]

    model.optimize(callback)
    metrics["cpu_seconds"] = time.process_time() - metrics["start_cpu"]
    metrics["runtime_seconds"] = model.Runtime
    return {
        "model": model, "data": data, "Y": Y, "X": X, "G": G, "E": E, "W": W, "F": F,
        "T": T, "price": price, "Z": Z, "Z_intransit": Z_intransit, "eta": eta,
        "revenue": revenue, "transport_cost": transport_cost, "artificial_cost": artificial_cost,
        "gap_cost": total_gap_cost, "excess_cost": total_excess_cost,
        "fixed_diversion_cost": fixed_diversion_cost, "variable_diversion_cost": variable_diversion_cost,
        "real_profit": real_profit, "metrics": metrics,
    }
