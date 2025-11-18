import io
import json
import pandas as pd

from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .models import (
    Request,
    sets, arcs1, arcs2, arcs3, diversion, precedence, demand, supply, salmonella,
    objective_summary, var_y, var_x, gap_result, excess_result,
    lead_time_result, cumulative_flow_time_result,
    shelf_time_result, price_result,
    salmonella_node_result, salmonella_intransit_result,
)


def _head_preview(df: pd.DataFrame, n=10):
    df2 = df.head(n).copy()
    cols = {}
    for col in df2.columns:
        vals = df2[col].tolist()
        cols[str(col)] = {i: ("" if pd.isna(v) else v) for i, v in enumerate(vals)}
    return cols


def _preview_payload(xf):
    book = pd.read_excel(xf, sheet_name=None)
    out = {}
    for name in ["sets", "arcs1", "arcs2", "arcs3", "precedence", "demand", "supply", "salmonella"]:
        if name in book:
            out[name] = _head_preview(book[name])
    return out


@require_http_methods(["GET"])
def home(request):
    return render(request, "isdrequests/isdUploadExcel.html")


@require_http_methods(["POST"])
def preview_excel(request):
    if "file" not in request.FILES:
        return JsonResponse({"status": "error", "message": "No file"}, status=400)
    xfile = request.FILES["file"]
    try:
        p = _preview_payload(xfile)
        return JsonResponse({"status": "success", "preview_data": p})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


def _safe_str(v):
    if pd.isna(v):
        return ""
    return str(v).strip()


def _safe_float(v):
    if pd.isna(v) or v == "":
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


@require_http_methods(["POST"])
@transaction.atomic
def save_excel(request):
    """
    Reads the uploaded Excel file, writes everything into the encrypted DB tables,
    and returns JSON {status, request_id}.
    """
    if "file" not in request.FILES:
        return JsonResponse({"status": "error", "message": "No file"}, status=400)

    xf = request.FILES["file"]
    req = Request.objects.create(
        requested_by=request.user if request.user.is_authenticated else None,
        title="Distribution Request",
        original_filename=xf.name,
        note="",
        status="SAVED",
    )
    book = pd.read_excel(xf, sheet_name=None)

    # ------------- sets -------------
    if "sets" in book:
        sdf = book["sets"]
        for i in range(len(sdf.index)):
            row_series = sdf.iloc[i]
            # skip completely empty rows
            if row_series.isna().all():
                continue

            row = sets(
                request=req,
                col_nodes=_safe_str(sdf.iat[i, 0]) if 0 < sdf.shape[1] else "",
                col_sources=_safe_str(sdf.iat[i, 1]) if 1 < sdf.shape[1] else "",
                col_processors=_safe_str(sdf.iat[i, 2]) if 2 < sdf.shape[1] else "",
                col_warehouses=_safe_str(sdf.iat[i, 3]) if 3 < sdf.shape[1] else "",
                col_retailers=_safe_str(sdf.iat[i, 4]) if 4 < sdf.shape[1] else "",
                col_foodbanks=_safe_str(sdf.iat[i, 5]) if 5 < sdf.shape[1] else "",
                col_markets=_safe_str(sdf.iat[i, 6]) if 6 < sdf.shape[1] else "",
                col_modes=_safe_str(sdf.iat[i, 7]) if 7 < sdf.shape[1] else "",
                col_products=_safe_str(sdf.iat[i, 8]) if 8 < sdf.shape[1] else "",
                col_check_sal=_safe_str(sdf.iat[i, 9]) if 9 < sdf.shape[1] else "",
                col_nocheck_sal=_safe_str(sdf.iat[i, 10]) if 10 < sdf.shape[1] else "",
            )
            row.save()

    # ------------- arcs1/2/3 -------------
    def _save_arcs(df, Model):
        # map "product", "node_i", etc. to their column indexes (case-insensitive)
        colmap = {str(c).strip().lower(): idx for idx, c in enumerate(df.columns)}

        def get_str(row_idx, col_key, fallback_idx=None):
            """
            Get a string from the column named col_key (case-insensitive),
            or from fallback_idx if header not found.
            """
            idx = colmap.get(col_key.lower())
            if idx is None:
                if fallback_idx is None:
                    return ""
                idx = fallback_idx
            return _safe_str(df.iat[row_idx, idx])

        def get_num(row_idx, col_key, fallback_idx=None, default=0.0):
            """
            Get a numeric value from the column named col_key.
            If header is missing or value is NaN/empty, returns default.
            """
            idx = colmap.get(col_key.lower())
            if idx is None:
                if fallback_idx is None:
                    return default
                idx = fallback_idx

            val = df.iat[row_idx, idx]
            return _safe_float(val) if not pd.isna(val) else default

        # ✅ START FROM 0: first DataFrame row = first real data row
        for i in range(len(df.index)):
            row_series = df.iloc[i]
            if row_series.isna().all():
                continue

            product     = get_str(i, "product",     fallback_idx=0)
            node_i      = get_str(i, "node_i",      fallback_idx=1)
            product_div = get_str(i, "product_div", fallback_idx=2)
            node_j      = get_str(i, "node_j",      fallback_idx=3)
            mode        = get_str(i, "mode",        fallback_idx=4)

            # skip ghost rows with no key data
            if not (product or node_i or product_div or node_j or mode):
                continue

            capacity   = get_num(i, "capacity",   fallback_idx=6, default=0.0)
            multiplier = get_num(i, "multiplier", fallback_idx=7, default=1.0)
            fixed_cost = get_num(i, "fixed_cost", fallback_idx=8, default=0.0)
            unit_cost  = get_num(i, "unit_cost",  fallback_idx=9, default=0.0)
            lead_time  = get_num(i, "lead_time",  fallback_idx=10, default=0.0)

            # 🔒 ensure we NEVER send None to the DB (Postgres hates that for NOT NULL fields)
            Model.objects.create(
                request=req,
                product=product,
                node_i=node_i,
                product_div=product_div,
                node_j=node_j,
                mode=mode,
                capacity=capacity if capacity is not None else 0.0,
                multiplier=multiplier if multiplier is not None else 1.0,
                fixed_cost=fixed_cost if fixed_cost is not None else 0.0,
                unit_cost=unit_cost if unit_cost is not None else 0.0,
                lead_time=lead_time if lead_time is not None else 0.0,
            )



    if "arcs1" in book:
        _save_arcs(book["arcs1"], arcs1)
    if "arcs2" in book:
        _save_arcs(book["arcs2"], arcs2)
    if "arcs3" in book:
        _save_arcs(book["arcs3"], arcs3)

    # ------------- precedence -------------
    if "precedence" in book:
        pdf = book["precedence"]
        for i in range(len(pdf.index)):
            row_series = pdf.iloc[i]
            if row_series.isna().all():
                continue
            product_in = _safe_str(pdf.iat[i, 0])
            node_i = _safe_str(pdf.iat[i, 1])
            product_out = _safe_str(pdf.iat[i, 2])
            node_j = _safe_str(pdf.iat[i, 3])
            if not (product_in or node_i or product_out or node_j):
                continue

            precedence.objects.create(
                request=req,
                product_in=product_in,
                node_i=node_i,
                product_out=product_out,
                node_j=node_j,
            )

    # ------------- demand -------------
    if "demand" in book:
        ddf = book["demand"]
        for i in range(len(ddf.index)):
            row_series = ddf.iloc[i]
            if row_series.isna().all():
                continue
            market = _safe_str(ddf.iat[i, 0])
            product = _safe_str(ddf.iat[i, 1])
            if not (market or product):
                continue
            demand.objects.create(
                request=req,
                market=market,
                product=product,
                demand=_safe_float(ddf.iat[i, 2]),
                gap_cost=_safe_float(ddf.iat[i, 3]),
            )

    # ------------- supply -------------
    # supply (matrix). Store each row label and a JSON mapping column header -> value
    if "supply" in book:
        sdf = book["supply"]
        headers = [str(h).strip() for h in list(sdf.columns)]
        for i in range(len(sdf.index)):
            row_series = sdf.iloc[i]
            if row_series.isna().all():
                continue
            label = _safe_str(sdf.iat[i, 0]) if len(headers) > 0 else ""
            if not label:
                # no row label = useless supply row
                continue
            values = {}
            for j in range(1, len(headers)):
                values[headers[j]] = _safe_float(sdf.iat[i, j])
            supply.objects.create(request=req, row_label=label, row_values=values)

    # ------------- salmonella -------------
    if "salmonella" in book:
        smdf = book["salmonella"]
        for i in range(len(smdf.index)):
            row_series = smdf.iloc[i]
            if row_series.isna().all():
                continue
            node = _safe_str(smdf.iat[i, 0])
            product = _safe_str(smdf.iat[i, 1])
            level = _safe_str(smdf.iat[i, 2])
            if not (node or product or level):
                continue
            salmonella.objects.create(
                request=req,
                node=node,
                product=product,
                level=level or "NA",
            )

    messages.success(request, f"Saved data for request #{req.id}.")
    return JsonResponse({"status": "success", "request_id": req.id})


@require_http_methods(["POST"])
@transaction.atomic
def run_optimization(request):
    """
    Build and solve the full SENS-D model (same logic as the original .py script)
    using data stored in the DB for a given Request, then save all results
    into the result models so results.html shows the same numbers.
    """
    import gurobipy as gp
    from gurobipy import GRB

    # -----------------------
    # 1. Resolve request_id / upload+run
    # -----------------------
    req_id = request.POST.get("request_id")

    if not req_id and "file" in request.FILES:
        # reuse save_excel to create Request + DB rows
        save_resp = save_excel(request)
        data = json.loads(save_resp.content.decode("utf-8"))
        if data.get("status") != "success":
            return HttpResponseBadRequest(data.get("message", "Failed to save"))
        req_id = data["request_id"]

    req = get_object_or_404(Request, pk=req_id)
    req.status = "RUNNING"
    req.save(update_fields=["status"])

    # -----------------------
    # 2. Build data from DB (mirror original xlrd-based script)
    # -----------------------

    # ---- Sets (from "sets" sheet) ----
    sets_qs = req.sets_rows.all()

    nodes = [r.col_nodes for r in sets_qs if r.col_nodes]
    sources = [r.col_sources for r in sets_qs if r.col_sources]
    markets = [r.col_markets for r in sets_qs if r.col_markets]
    modes = [r.col_modes for r in sets_qs if r.col_modes]
    products = [r.col_products for r in sets_qs if r.col_products]
    check_sal = [r.col_check_sal for r in sets_qs if r.col_check_sal]
    nocheck_sal = [r.col_nocheck_sal for r in sets_qs if r.col_nocheck_sal]

    def _dedupe(seq):
        seen = set()
        out = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    nodes = _dedupe(nodes)
    sources = _dedupe(sources)
    markets = _dedupe(markets)
    modes = _dedupe(modes)
    products = _dedupe(products)
    check_sal = _dedupe(check_sal)
    nocheck_sal = _dedupe(nocheck_sal)

    # Non-source / non-market nodes
    non_source_market_nodes = [n for n in nodes if n not in sources and n not in markets]

    # ---- Precedences (same as original: from arcs1 only) ----
    precedences = []
    for a in req.arcs1_rows.all():
        if not (a.product and a.node_i and a.product_div and a.node_j):
            continue
        p = (a.product, a.node_i, a.product_div, a.node_j)
        if p not in precedences:
            precedences.append(p)

    # Make sure products and nodes cover everything referenced in precedences
    prod_from_precs = {p[0] for p in precedences} | {p[2] for p in precedences}
    node_from_precs = {p[1] for p in precedences} | {p[3] for p in precedences}

    products = _dedupe(products + list(prod_from_precs))
    nodes = _dedupe(nodes + list(node_from_precs))

    # Recompute non_source_market_nodes with updated nodes
    non_source_market_nodes = [n for n in nodes if n not in sources and n not in markets]


    # ---- Demand & gap cost ----
    market_demand = {}
    gap_cost = {}
    for d in req.demand_rows.all():
        if not (d.market and d.product):
            continue
        key = (d.product, d.market)
        market_demand[key] = float(d.demand) * 0.6  # same 0.6 scaling
        gap_cost[key] = float(d.gap_cost)
    
    # Ensure all markets referenced in demand are in the markets set
    markets_from_demand = {mk for (_, mk) in market_demand.keys()}
    markets = _dedupe(markets + list(markets_from_demand))

    # ---- Supply matrix ----
    supply_dict = {}   # (source, product) -> capacity
    for srow in req.supply_rows.all():
        src = srow.row_label
        if not src:
            continue
        for prod, val in (srow.row_values or {}).items():
            supply_dict[(src, str(prod).strip())] = float(val)

    # ---- Multipliers, costs, lead times, capacities from arcs1/2/3 ----
    multipliers = {}       # precedence -> multiplier
    c_fixed_send = {}      # (precedence, mode) -> fixed cost
    c_unit_send = {}       # (precedence, mode) -> unit cost
    leadtime_send = {}     # (precedence, mode) -> lead time
    mode_capacity = {}     # (precedence, mode) -> capacity

    # Multipliers only from arcs1 (like original)
    for r in req.arcs1_rows.all():
        key = (r.product, r.node_i, r.product_div, r.node_j)
        multipliers[key] = float(r.multiplier)

    def _collect_arcs(qs):
        for r in qs:
            if not (r.product and r.node_i and r.product_div and r.node_j and r.mode):
                continue
            key = (r.product, r.node_i, r.product_div, r.node_j)
            md = r.mode
            c_fixed_send[(key, md)] = float(r.fixed_cost)
            c_unit_send[(key, md)] = float(r.unit_cost)
            leadtime_send[(key, md)] = float(r.lead_time)
            mode_capacity[(key, md)] = float(r.capacity)

    _collect_arcs(req.arcs1_rows.all())
    _collect_arcs(req.arcs2_rows.all())
    _collect_arcs(req.arcs3_rows.all())

    # ---- Salmonella levels ----
    # Read ALL numeric salmonella readings from the sheet.
    # We will later only link them to model variables where those variables exist.
    salmonella_level = {}  # (product, node) -> numeric level
    for s in req.salmonella_rows.all():
        prod = (s.product or "").strip()
        node = (s.node or "").strip()
        lvl_str = (s.level or "").strip()

        if not lvl_str or lvl_str.upper() == "NA":
            continue  # skip NA / empty

        try:
            val = float(lvl_str)
        except ValueError:
            continue  # skip weird text

        salmonella_level[(prod, node)] = val


    # -----------------------
    # 3. Build SENS-D model (same as script)
    # -----------------------

    # Parameters
    epsilon = 10
    max_salmonella_level = 6          # initial printed value
    zeta_0 = max_salmonella_level
    Gamma = 1000                      # big-M for salmonella at nodes
    delta_penalty = 500               # penalty for in-transit contamination

    # alpha/beta per mode (assume exactly 3 modes in this dataset)
    alpha_values = [0.98, 0.77, 0.71]
    beta_values = [0.79, 1.26, 0.70]
    alpha = {}
    beta = {}
    for idx, md in enumerate(modes):
        if idx < len(alpha_values):
            alpha[md] = alpha_values[idx]
            beta[md] = beta_values[idx]

    intransit_threshold = 25
    Gamma_intransit = 20

    # Create model
    m = gp.Model(f"SENS-D-{req.id}")

    # --- Decision variables ---

    # Y[p,md], X[p,md]
    Y = {}
    X = {}
    for p in precedences:
        for md in modes:
            Y[(p, md)] = m.addVar(vtype=GRB.BINARY, name=f"Y_{p}_{md}")
            X[(p, md)] = m.addVar(vtype=GRB.CONTINUOUS, name=f"X_{p}_{md}")

    # G, E
    G = {}
    E = {}
    for pr in products:
        for mk in markets:
            G[(pr, mk)] = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"G_{pr}_{mk}")
            E[(pr, mk)] = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"E_{pr}_{mk}")

    # W[precedence]
    W = {}
    for p in precedences:
        W[p] = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"W_{p}")

    # F[product,node]
    F = {}
    for pr in products:
        for nd in nodes:
            F[(pr, nd)] = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"F_{pr}_{nd}")

    # T[product,market]
    T = {}
    for pr in products:
        for mk in markets:
            T[(pr, mk)] = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"T_{pr}_{mk}")

    # pi[product,market]
    pi = {}
    for pr in products:
        for mk in markets:
            pi[(pr, mk)] = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"pi_{pr}_{mk}")

    # Z[product,node] for check_sal products
    Z = {}
    for pr in check_sal:
        for nd in nodes:
            Z[(pr, nd)] = m.addVar(vtype=GRB.BINARY, name=f"Z_{pr}_{nd}")

    # Z_intransit[product,node]
    Z_intransit = {}
    for pr in check_sal:
        for nd in nodes:
            Z_intransit[(pr, nd)] = m.addVar(vtype=GRB.BINARY, name=f"Z_intransit_{pr}_{nd}")

    # S[precedence,mode]
    S = {}
    for p in precedences:
        for md in modes:
            S[(p, md)] = m.addVar(vtype=GRB.CONTINUOUS, name=f"S_{p}_{md}")

    # salmonella_estimation[product,node] (η)
    salmonella_estimation = {}
    for pr in check_sal:
        for nd in nodes:
            salmonella_estimation[(pr, nd)] = m.addVar(
                vtype=GRB.CONTINUOUS,
                name=f"salmonella_estimation_{pr}_{nd}",
            )

    # --- Constraints ---

    # (1) Mode selection: at most 1 mode per precedence
    for p in precedences:
        m.addConstr(
            gp.quicksum(Y[(p, md)] for md in modes) <= 1,
            name=f"ModeSel_{p}",
        )

    # (2) W = leadtime_send * Y
    for p in precedences:
        m.addConstr(
            W[p] == gp.quicksum(
                leadtime_send.get((p, md), 0.0) * Y[(p, md)] for md in modes
            ),
            name=f"LeadTime_{p}",
        )

    # (3) Capacity: X <= cap * Y
    for p in precedences:
        for md in modes:
            cap = mode_capacity.get((p, md), 0.0)
            m.addConstr(
                X[(p, md)] <= cap * Y[(p, md)],
                name=f"Cap_{p}_{md}",
            )

    # (4) Market demand balance
    for pr in products:
        for mk in markets:
            demand_val = market_demand.get((pr, mk), 0.0)
            inbound = gp.quicksum(
                X[(p, md)]
                for p in precedences
                for md in modes
                if p[2] == pr and p[3] == mk
            )
            m.addConstr(
                inbound + G[(pr, mk)] - E[(pr, mk)] == demand_val,
                name=f"Demand_{pr}_{mk}",
            )

    # (5) Supply capacity at sources (with multipliers)
    for pr in products:
        for src in sources:
            outflow = gp.quicksum(
                multipliers.get(p, 1.0) * X[(p, md)]
                for p in precedences
                for md in modes
                if p[0] == pr and p[1] == src
            )
            m.addConstr(
                outflow <= supply_dict.get((src, pr), 0.0),
                name=f"Supply_{src}_{pr}",
            )

    # (6) Flow balance at internal nodes (no diversion in this version)
    for pr in products:
        for nd in non_source_market_nodes:
            outflow = gp.quicksum(
                X[(p, md)]
                for p in precedences
                for md in modes
                if p[0] == pr and p[1] == nd
            )
            inflow = gp.quicksum(
                multipliers.get(p, 1.0) * X[(p, md)]
                for p in precedences
                for md in modes
                if p[2] == pr and p[3] == nd
            )
            m.addConstr(
                outflow == inflow,
                name=f"FlowBal_{pr}_{nd}",
            )

    # (7) Cumulative flow time: F[product_out,node_j] - F[product_in,node_i] >= W
    for p in precedences:
        prod_in, node_i, prod_out, node_j = p
        m.addConstr(
            F[(prod_out, node_j)] - F[(prod_in, node_i)] >= W[p],
            name=f"CumFlow_{p}",
        )

    # (8) Shelf time vs flow time
    for pr in products:
        for mk in markets:
            m.addConstr(
                T[(pr, mk)] == -0.3 * F[(pr, mk)] + 20,
                name=f"ShelfTime_{pr}_{mk}",
            )

    # (9) Price vs shelf time
    for pr in products:
        for mk in markets:
            m.addConstr(
                pi[(pr, mk)] == -0.3 * T[(pr, mk)] + 100,
                name=f"Price_{pr}_{mk}",
            )

    # (10) In-transit salmonella growth S = alpha*leadtime + beta
    for p in precedences:
        prod, node_i, prod_div, node_j = p
        if prod in check_sal:
            for md in modes:
                if (p, md) in leadtime_send and md in alpha:
                    m.addConstr(
                        S[(p, md)]
                        == alpha[md] * leadtime_send[(p, md)] + beta[md],
                        name=f"InTransitGrowth_{prod}_{node_i}_{prod_div}_{node_j}_{md}",
                    )

    # (11) Max aggregation of salmonella at arrival node
    for prod_div in check_sal:
        for node_j in nodes:
            incoming_exprs = []
            for p in precedences:
                prod, node_i, p_div, j = p
                if p_div == prod_div and j == node_j:
                    for md in modes:
                        if (p, md) in leadtime_send and (prod, node_i) in salmonella_estimation:
                            prev_eta = salmonella_estimation[(prod, node_i)]
                            expr = prev_eta + S[(p, md)] * Y[(p, md)]
                            incoming_exprs.append(expr)
            for expr in incoming_exprs:
                m.addConstr(
                    salmonella_estimation[(prod_div, node_j)] >= expr,
                    name=f"MaxEta_{prod_div}_{node_j}",
                )

    # (12) Sensor readings: only where we actually have an η variable
    for (prod, nd), sensor_val in salmonella_level.items():
        key = (prod, nd)
        if key in salmonella_estimation:  # only products in check_sal have η variables
            m.addConstr(
                salmonella_estimation[key] == sensor_val,
                name=f"Sensor_{prod}_{nd}",
            )


    # (13) In-transit threshold flags Z_intransit
    for (prod, nd), eta_var in salmonella_estimation.items():
        if (prod, nd) in Z_intransit:
            m.addConstr(
                Gamma_intransit * Z_intransit[(prod, nd)]
                >= eta_var - intransit_threshold,
                name=f"InTransitFlag_{prod}_{nd}",
            )

    # adjust max level like script does
    max_salmonella_level = 18

    # (14) Node salmonella threshold flags Z
    for (prod, nd), sensor_val in salmonella_level.items():
        key = (prod, nd)
        if key not in Z:
            continue  # only products in check_sal have Z variables

        m.addConstr(
            sensor_val - max_salmonella_level <= Gamma * Z[key],
            name=f"SalLB_{prod}_{nd}",
        )
        m.addConstr(
            sensor_val - max_salmonella_level >= -Gamma * (1 - Z[key]),
            name=f"SalUB_{prod}_{nd}",
        )


    # (15) Block flows if contaminated at origin (no Salmonella flow)
    for p in precedences:
        prod, node_i, prod_div, node_j = p
        if prod in check_sal and prod == prod_div:
            for md in modes:
                cap = mode_capacity.get((p, md), 0.0)
                if (prod, node_i) in Z:
                    m.addConstr(
                        (1 - Z[(prod, node_i)]) * cap >= X[(p, md)],
                        name=f"NoFlowIfZ_{p}_{md}",
                    )

    # (16) Prevent contaminated arrival at node (per route)
    for p in precedences:
        prod, node_i, prod_div, node_j = p
        if prod not in check_sal:
            continue
        for md in modes:
            if (p, md) in leadtime_send and md in alpha:
                eta_i = salmonella_estimation[(prod, node_i)]
                travel_growth = alpha[md] * leadtime_send[(p, md)] + beta[md]
                m.addConstr(
                    eta_i + travel_growth
                    <= max_salmonella_level + Gamma * (1 - Y[(p, md)]),
                    name=f"PreventCont_{prod}_{node_i}_{node_j}_{md}",
                )

    # -----------------------
    # 4. Objective (Total_profit) – same formula as script
    # -----------------------

    # Revenue
    total_revenue = gp.LinExpr(0.0)
    for pr in products:
        for mk in markets:
            for md in modes:
                for p in precedences:
                    if p[0] == pr and p[3] == mk:
                        total_revenue += pi[(pr, mk)] * X[(p, md)]

    # Transport cost
    total_transportation_cost = gp.quicksum(
        c_fixed_send.get((p, md), 0.0) * Y[(p, md)]
        + c_unit_send.get((p, md), 0.0) * X[(p, md)]
        for p in precedences
        for md in modes
    )

    # Artificial term
    artificial_term = epsilon * gp.quicksum(
        F[(pr, nd)] for pr in products for nd in nodes
    )

    # Gap & excess costs
    total_gap_cost = gp.quicksum(
        (gap_cost.get((pr, mk), 0.0) + 10) * 10 * G[(pr, mk)]
        for pr in products
        for mk in markets
    )
    total_excess_cost = gp.quicksum(
        10 * E[(pr, mk)] for pr in products for mk in markets
    )

    # In-transit penalty
    total_intransit_penalty = gp.quicksum(
        delta_penalty * Z_intransit[(pr, nd)] for (pr, nd) in Z_intransit.keys()
    )

    # Diversion costs (where product_in != product_out)
    fixed_diversion_cost = gp.LinExpr(0.0)
    variable_diversion_cost = gp.LinExpr(0.0)
    for p in precedences:
        if p[0] != p[2]:
            for md in modes:
                if (p, md) in c_fixed_send:
                    fixed_diversion_cost += c_fixed_send[(p, md)] * Y[(p, md)]
                if (p, md) in c_unit_send:
                    variable_diversion_cost += c_unit_send[(p, md)] * X[(p, md)]

    # Real profit (no artificial, no in-transit penalty)
    Real_profit = total_revenue - total_transportation_cost - total_gap_cost - total_excess_cost

    # Total profit (objective, same as script)
    Total_profit = (
        total_revenue
        - total_transportation_cost
        - artificial_term
        - total_gap_cost
        - total_excess_cost
        - total_intransit_penalty
    )

    m.setObjective(Total_profit, GRB.MAXIMIZE)
    m.setParam("MIPGap", 0.001)
    m.setParam("TimeLimit", 36000)
    m.optimize()

    # -----------------------
    # 5. Save results to DB
    # -----------------------

    # Clear previous results for this request
    var_y.objects.filter(request=req).delete()
    var_x.objects.filter(request=req).delete()
    gap_result.objects.filter(request=req).delete()
    excess_result.objects.filter(request=req).delete()
    objective_summary.objects.filter(request=req).delete()
    lead_time_result.objects.filter(request=req).delete()
    cumulative_flow_time_result.objects.filter(request=req).delete()
    shelf_time_result.objects.filter(request=req).delete()
    price_result.objects.filter(request=req).delete()
    salmonella_node_result.objects.filter(request=req).delete()
    salmonella_intransit_result.objects.filter(request=req).delete()

    if m.status in [GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.INTERRUPTED]:
        # Y / X
        for p in precedences:
            for md in modes:
                yv = Y[(p, md)].X
                xv = X[(p, md)].X
                if int(round(yv)) == 1:
                    var_y.objects.create(
                        request=req,
                        product=p[0],
                        node_i=p[1],
                        product_div=p[2],
                        node_j=p[3],
                        mode=md,
                        value=1,
                    )
                if abs(xv) > 1e-9:
                    var_x.objects.create(
                        request=req,
                        product=p[0],
                        node_i=p[1],
                        product_div=p[2],
                        node_j=p[3],
                        mode=md,
                        quantity=xv,
                    )

        # G / E
        for pr in products:
            for mk in markets:
                gv = G[(pr, mk)].X
                ev = E[(pr, mk)].X
                if abs(gv) > 1e-9:
                    gap_result.objects.create(
                        request=req, product=pr, market=mk, gap=gv
                    )
                if abs(ev) > 1e-9:
                    excess_result.objects.create(
                        request=req, product=pr, market=mk, excess=ev
                    )

        # W results
        for p in precedences:
            w_val = W[p].X
            if abs(w_val) > 1e-9:
                lead_time_result.objects.create(
                    request=req,
                    product_in=p[0],
                    node_i=p[1],
                    product_out=p[2],
                    node_j=p[3],
                    lead_time=w_val,
                )

        # F results
        for pr in products:
            for nd in nodes:
                f_val = F[(pr, nd)].X
                if abs(f_val) > 1e-9:
                    cumulative_flow_time_result.objects.create(
                        request=req,
                        product=pr,
                        node=nd,
                        flow_time=f_val,
                    )

        # T, pi
        for pr in products:
            for mk in markets:
                t_val = T[(pr, mk)].X
                if abs(t_val) > 1e-9:
                    shelf_time_result.objects.create(
                        request=req,
                        product=pr,
                        market=mk,
                        shelf_time=t_val,
                    )
                pi_val = pi[(pr, mk)].X
                if abs(pi_val) > 1e-9:
                    price_result.objects.create(
                        request=req,
                        product=pr,
                        market=mk,
                        price=pi_val,
                    )

        # salmonella node values
        for (pr, nd), var in salmonella_estimation.items():
            val = var.X
            if abs(val) > 1e-9:
                salmonella_node_result.objects.create(
                    request=req,
                    product=pr,
                    node=nd,
                    value=val,
                )

        # in-transit salmonella S
        for p in precedences:
            for md in modes:
                sval = S[(p, md)].X
                if abs(sval) > 1e-9:
                    salmonella_intransit_result.objects.create(
                        request=req,
                        product_in=p[0],
                        node_i=p[1],
                        product_out=p[2],
                        node_j=p[3],
                        mode=md,
                        value=sval,
                    )

        # Objective summary (cards at top of results.html)
        objective_summary.objects.create(
            request=req,
            objective_value=float(m.ObjVal) if m.SolCount > 0 else 0.0,
            total_profit=float(Real_profit.getValue()) if m.SolCount > 0 else 0.0,
            total_revenue=float(total_revenue.getValue()) if m.SolCount > 0 else 0.0,
            total_transport_cost=float(total_transportation_cost.getValue())
            if m.SolCount > 0
            else 0.0,
            total_gap_cost=float(total_gap_cost.getValue()) if m.SolCount > 0 else 0.0,
            total_excess_cost=float(total_excess_cost.getValue())
            if m.SolCount > 0
            else 0.0,
            total_intransit_penalty=float(total_intransit_penalty.getValue())
            if m.SolCount > 0
            else 0.0,
            fixed_diversion_cost=float(fixed_diversion_cost.getValue())
            if m.SolCount > 0
            else 0.0,
            variable_diversion_cost=float(variable_diversion_cost.getValue())
            if m.SolCount > 0
            else 0.0,
        )

        req.status = "DONE"
    else:
        req.status = "FAILED"

    req.save(update_fields=["status"])
    messages.success(request, f"Optimization {req.status.lower()} for request #{req.id}.")
    return redirect(reverse("requests_list"))


@require_http_methods(["GET"])
def requests_list(request):
    rows = Request.objects.order_by("-created_at")
    return render(request, "isdrequests/isdrequests.html", {"rows": rows})


@require_http_methods(["GET"])
def results_view(request, req_id: int):
    req = get_object_or_404(Request, pk=req_id)
    return render(request, "isdrequests/isdresults.html", {
        "req": req,
        "summary": getattr(req, "summary", None),
        "y_rows": req.y_vars.all(),
        "x_rows": req.x_vars.all(),
        "gaps": req.gaps.all(),
        "excess": req.excesses.all(),
        "lead_times": req.lead_times.all(),
        "flow_times": req.flow_times.all(),
        "shelf_times": req.shelf_times.all(),
        "prices": req.prices.all(),
        "salmonella_nodes": req.salmonella_nodes.all(),
        "salmonella_intransit": req.salmonella_intransit.all(),
    })



import io
import pandas as pd
from django.http import HttpResponse

@require_http_methods(["GET"])
def results_download_excel(request, req_id: int):
    req = get_object_or_404(Request, pk=req_id)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        if hasattr(req, "summary"):
            s = req.summary
            summary_df = pd.DataFrame([{
                "Objective (Total Profit)": s.objective_value,
                "Real Profit": s.total_profit,
                "Revenue": s.total_revenue,
                "Transport Cost": s.total_transport_cost,
                "Gap Cost": s.total_gap_cost,
                "Excess Cost": s.total_excess_cost,
                "In-Transit Penalty": s.total_intransit_penalty,
                "Fixed Diversion Cost": s.fixed_diversion_cost,
                "Variable Diversion Cost": s.variable_diversion_cost,
            }])
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

        # Y
        y_df = pd.DataFrame([
            {
                "product_in": y.product,
                "node_i": y.node_i,
                "product_out": y.product_div,
                "node_j": y.node_j,
                "mode": y.mode,
                "selected": y.value,
            }
            for y in req.y_vars.all()
        ])
        if not y_df.empty:
            y_df.to_excel(writer, sheet_name="Y_modes", index=False)

        # X
        x_df = pd.DataFrame([
            {
                "product_in": x.product,
                "node_i": x.node_i,
                "product_out": x.product_div,
                "node_j": x.node_j,
                "mode": x.mode,
                "quantity": x.quantity,
            }
            for x in req.x_vars.all()
        ])
        if not x_df.empty:
            x_df.to_excel(writer, sheet_name="X_flows", index=False)

        # G & E
        g_df = pd.DataFrame([
            {"product": g.product, "market": g.market, "gap": g.gap}
            for g in req.gaps.all()
        ])
        if not g_df.empty:
            g_df.to_excel(writer, sheet_name="Gap", index=False)

        e_df = pd.DataFrame([
            {"product": e.product, "market": e.market, "excess": e.excess}
            for e in req.excesses.all()
        ])
        if not e_df.empty:
            e_df.to_excel(writer, sheet_name="Excess", index=False)

        # W, F, T, pi, salmonella
        w_df = pd.DataFrame([
            {
                "product_in": w.product_in,
                "node_i": w.node_i,
                "product_out": w.product_out,
                "node_j": w.node_j,
                "lead_time": w.lead_time,
            }
            for w in req.lead_times.all()
        ])
        if not w_df.empty:
            w_df.to_excel(writer, sheet_name="W_lead_time", index=False)

        f_df = pd.DataFrame([
            {"product": f.product, "node": f.node, "flow_time": f.flow_time}
            for f in req.flow_times.all()
        ])
        if not f_df.empty:
            f_df.to_excel(writer, sheet_name="F_flow_time", index=False)

        t_df = pd.DataFrame([
            {"product": t.product, "market": t.market, "shelf_time": t.shelf_time}
            for t in req.shelf_times.all()
        ])
        if not t_df.empty:
            t_df.to_excel(writer, sheet_name="T_shelf_time", index=False)

        pi_df = pd.DataFrame([
            {"product": p.product, "market": p.market, "price": p.price}
            for p in req.prices.all()
        ])
        if not pi_df.empty:
            pi_df.to_excel(writer, sheet_name="pi_prices", index=False)

        sal_node_df = pd.DataFrame([
            {"product": s.product, "node": s.node, "value": s.value}
            for s in req.salmonella_nodes.all()
        ])
        if not sal_node_df.empty:
            sal_node_df.to_excel(writer, sheet_name="Salmonella_nodes", index=False)

        sal_intransit_df = pd.DataFrame([
            {
                "product_in": s.product_in,
                "node_i": s.node_i,
                "product_out": s.product_out,
                "node_j": s.node_j,
                "mode": s.mode,
                "value": s.value,
            }
            for s in req.salmonella_intransit.all()
        ])
        if not sal_intransit_df.empty:
            sal_intransit_df.to_excel(writer, sheet_name="Salmonella_intransit", index=False)

    output.seek(0)
    filename = f"SENSD_results_req_{req.id}.xlsx"
    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
