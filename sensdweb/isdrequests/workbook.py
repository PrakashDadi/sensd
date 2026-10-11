"""Validation and persistence for the SENS-D Midwest v1 workbook contract."""

from dataclasses import dataclass

import pandas as pd

from .models import arcs1, arcs2, arcs3, demand, salmonella, sets, supply


MODEL_VERSION = "sensd-midwest-v1"
REQUIRED_SHEETS = ("sets", "arcs1", "arcs2", "arcs3", "demand", "supply", "salmonella")


class WorkbookValidationError(ValueError):
    pass


def _norm(value):
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _column_map(frame, aliases, sheet):
    available = {_norm(column): column for column in frame.columns}
    mapped = {}
    missing = []
    for canonical, choices in aliases.items():
        match = next((available.get(_norm(choice)) for choice in choices if _norm(choice) in available), None)
        if match is None:
            missing.append(canonical)
        else:
            mapped[canonical] = match
    if missing:
        raise WorkbookValidationError(
            f"Sheet '{sheet}' is missing required column(s): {', '.join(missing)}."
        )
    return mapped


def _text(value):
    return "" if pd.isna(value) else str(value).strip()


def _number(value, *, sheet, row, field, default=None):
    if pd.isna(value) or value == "":
        if default is not None:
            return default
        raise WorkbookValidationError(f"Sheet '{sheet}', row {row}: '{field}' is required.")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise WorkbookValidationError(
            f"Sheet '{sheet}', row {row}: '{field}' must be numeric."
        ) from exc


SET_COLUMNS = {
    "nodes": ("nodes",), "sources": ("sources",), "processors": ("processor", "processors"),
    "warehouses": ("warehouse", "warehouses"), "retailers": ("retailers",),
    "foodbanks": ("foodbanks", "food banks"), "markets": ("markets",),
    "modes": ("tmodes", "modes"), "products": ("products",),
    "check_sal": ("salmonella_need", "salmonella need"),
    "nocheck_sal": ("salmonella_noneed", "salmonella noneed"),
}
ARC_COLUMNS = {
    "product": ("p", "product"), "node_i": ("node_i", "node i"),
    "product_div": ("p'", "product_div", "product out"), "node_j": ("node_j", "node j"),
    "mode": ("mode",), "distance": ("distance_nodes", "distance nodes"),
    "capacity": ("mode_capacity", "capacity"), "multiplier": ("multiplier",),
    "fixed_cost": ("fixed_sending_cost", "fixed cost"),
    "unit_cost": ("unit_sending_cost", "unit cost"),
    "lead_time": ("leadtime_send", "lead time"), "speed": ("speed",),
    "travel_time": ("travel time", "travel_time"),
    "loading_unloading_time": ("loading + unloading time", "loading unloading time"),
}
DEMAND_COLUMNS = {
    "market": ("market",), "product": ("product",), "demand": ("demand",),
    "gap_cost": ("gap_cost", "gap cost"), "population": ("population",),
}
SALMONELLA_COLUMNS = {
    "node": ("node_i", "node"), "product": ("product",),
    "sensor_value": ("salmonella level", "salmonella_level"),
    "fixed_intervention_cost": ("fixed_intervention_cost", "fixed intervention cost"),
}


@dataclass
class ParsedWorkbook:
    frames: dict
    columns: dict

    def preview(self, limit=10):
        output = {}
        for name in REQUIRED_SHEETS:
            frame = self.frames[name].head(limit)
            output[name] = {
                str(column): {i: ("" if pd.isna(value) else value) for i, value in enumerate(frame[column])}
                for column in frame.columns
            }
        return output


def parse_workbook(upload):
    try:
        book = pd.read_excel(upload, sheet_name=None)
    except Exception as exc:
        raise WorkbookValidationError(f"The Excel workbook could not be read: {exc}") from exc
    missing = [name for name in REQUIRED_SHEETS if name not in book]
    if missing:
        raise WorkbookValidationError(f"Missing required sheet(s): {', '.join(missing)}.")

    columns = {"sets": _column_map(book["sets"], SET_COLUMNS, "sets")}
    for name in ("arcs1", "arcs2", "arcs3"):
        columns[name] = _column_map(book[name], ARC_COLUMNS, name)
    columns["demand"] = _column_map(book["demand"], DEMAND_COLUMNS, "demand")
    columns["salmonella"] = _column_map(book["salmonella"], SALMONELLA_COLUMNS, "salmonella")
    if book["supply"].shape[1] < 2:
        raise WorkbookValidationError("Sheet 'supply' must contain a source column and product columns.")
    return ParsedWorkbook(book, columns)


def persist_workbook(parsed, request_record):
    frame = parsed.frames["sets"]
    cols = parsed.columns["sets"]
    set_fields = {
        "nodes": "col_nodes", "sources": "col_sources", "processors": "col_processors",
        "warehouses": "col_warehouses", "retailers": "col_retailers", "foodbanks": "col_foodbanks",
        "markets": "col_markets", "modes": "col_modes", "products": "col_products",
        "check_sal": "col_check_sal", "nocheck_sal": "col_nocheck_sal",
    }
    for _, row in frame.iterrows():
        values = {model_field: _text(row[cols[key]]) for key, model_field in set_fields.items()}
        if any(values.values()):
            sets.objects.create(request=request_record, **values)

    for sheet, model in (("arcs1", arcs1), ("arcs2", arcs2), ("arcs3", arcs3)):
        frame, cols = parsed.frames[sheet], parsed.columns[sheet]
        for index, row in frame.iterrows():
            identity = {key: _text(row[cols[key]]) for key in ("product", "node_i", "product_div", "node_j", "mode")}
            if not any(identity.values()):
                continue
            row_number = int(index) + 2
            numeric = {
                key: _number(row[cols[key]], sheet=sheet, row=row_number, field=key, default=default)
                for key, default in (("distance", 0.0), ("capacity", 0.0), ("multiplier", 1.0),
                                     ("fixed_cost", 0.0), ("unit_cost", 0.0), ("lead_time", 0.0),
                                     ("speed", 0.0), ("travel_time", 0.0), ("loading_unloading_time", 0.0))
            }
            model.objects.create(request=request_record, **identity, **numeric)

    frame, cols = parsed.frames["demand"], parsed.columns["demand"]
    for index, row in frame.iterrows():
        market, product = _text(row[cols["market"]]), _text(row[cols["product"]])
        if not (market or product):
            continue
        row_number = int(index) + 2
        demand.objects.create(
            request=request_record, market=market, product=product,
            demand=_number(row[cols["demand"]], sheet="demand", row=row_number, field="demand", default=0.0),
            gap_cost=_number(row[cols["gap_cost"]], sheet="demand", row=row_number, field="gap_cost", default=0.0),
            population=_number(row[cols["population"]], sheet="demand", row=row_number, field="population", default=0.0),
        )

    frame = parsed.frames["supply"]
    source_column = frame.columns[0]
    for _, row in frame.iterrows():
        source_name = _text(row[source_column])
        if not source_name:
            continue
        values = {}
        for product_column in frame.columns[1:]:
            product = _text(product_column)
            if not product or product.lower().startswith("unnamed") or product.lower() in {"total", "justification"}:
                continue
            values[product] = _number(row[product_column], sheet="supply", row=int(row.name) + 2, field=product, default=0.0)
        supply.objects.create(request=request_record, row_label=source_name, row_values=values)

    frame, cols = parsed.frames["salmonella"], parsed.columns["salmonella"]
    for index, row in frame.iterrows():
        node, product = _text(row[cols["node"]]), _text(row[cols["product"]])
        if not (node or product):
            continue
        raw_sensor = row[cols["sensor_value"]]
        has_sensor = not pd.isna(raw_sensor) and _text(raw_sensor).upper() not in {"", "NA"}
        sensor_value = _number(raw_sensor, sheet="salmonella", row=int(index) + 2, field="salmonella level") if has_sensor else None
        salmonella.objects.create(
            request=request_record, node=node, product=product,
            sensor_value=sensor_value, has_sensor=has_sensor,
            fixed_intervention_cost=_number(
                row[cols["fixed_intervention_cost"]], sheet="salmonella", row=int(index) + 2,
                field="fixed intervention cost", default=0.0,
            ),
        )
