import io
import os
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from gurobipy import GRB

from .models import (
    Request, contamination_flag_result, cumulative_flow_time_result, excess_result,
    gap_result, intransit_flag_result, lead_time_result, objective_summary,
    price_result, salmonella_node_result, shelf_time_result, var_x, var_y,
)
from .services import _solver_value, execute_optimization, persist_optimization_result
from .workbook import WorkbookValidationError, parse_workbook, persist_workbook


def workbook_bytes(include_population=True):
    output = io.BytesIO()
    arc = pd.DataFrame([{
        "p": "Raw", "node_i": "Source", "p'": "Raw", "node_j": "Market",
        "mode": "Truck", "distance_nodes": 10, "mode_capacity": 100,
        "multiplier": 1, "fixed_sending_cost": 5, "unit_sending_cost": 2,
        "leadtime_send": 1, "speed": 50, "travel time": .2,
        "loading + unloading time": .8,
    }])
    demand_columns = {"market": ["Market"], "product": ["Raw"], "demand": [20], "gap_cost": [3]}
    if include_population:
        demand_columns["population"] = [1000]
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame([{
            "nodes": "Source", "sources": "Source", "processor": "", "warehouse": "",
            "retailers": "", "foodbanks": "", "markets": "Market", "tmodes": "Truck",
            "products": "Raw", "salmonella_need": "Raw", "salmonella_noneed": "Cooked",
        }, {"nodes": "Market"}]).to_excel(writer, sheet_name="sets", index=False)
        for name in ("arcs1", "arcs2", "arcs3"):
            arc.to_excel(writer, sheet_name=name, index=False)
        pd.DataFrame(demand_columns).to_excel(writer, sheet_name="demand", index=False)
        pd.DataFrame({"available supply": ["Source"], "Raw": [100], "Total": [100], "Justification": [""]}).to_excel(writer, sheet_name="supply", index=False)
        pd.DataFrame({"node_i": ["Source"], "product": ["Raw"], "salmonella level": [1.5], "fixed_intervention_cost": [25]}).to_excel(writer, sheet_name="salmonella", index=False)
    return output.getvalue()


class WorkbookContractTests(TestCase):
    def test_undefined_solver_values_are_not_persistable(self):
        class Variable:
            X = float("nan")

        self.assertIsNone(_solver_value(Variable()))

    def test_zero_solver_values_are_not_passed_to_encrypted_float_field(self):
        class Variable:
            X = 0.0

        self.assertIsNone(_solver_value(Variable()))

    def test_finite_solver_values_are_persistable(self):
        class Variable:
            X = 1.25

        self.assertEqual(_solver_value(Variable()), 1.25)

    def test_current_workbook_contract_parses(self):
        parsed = parse_workbook(io.BytesIO(workbook_bytes()))
        self.assertEqual(parsed.frames["arcs1"].shape, (1, 14))
        self.assertIn("population", parsed.columns["demand"])

    def test_missing_new_field_is_rejected(self):
        with self.assertRaisesMessage(WorkbookValidationError, "population"):
            parse_workbook(io.BytesIO(workbook_bytes(include_population=False)))


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class RequestWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", "owner@example.com", "password")
        self.other = User.objects.create_user("other", "other@example.com", "password")
        self.client.force_login(self.owner)

    def test_save_persists_new_fields_and_owner(self):
        upload = SimpleUploadedFile("midwest.xlsx", workbook_bytes(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response = self.client.post(reverse("save_excel"), {"file": upload})
        self.assertEqual(response.status_code, 200, response.content)
        record = Request.objects.get(pk=response.json()["request_id"])
        self.assertEqual(record.requested_by, self.owner)
        self.assertEqual(record.model_version, "sensd-midwest-v1")
        arc = record.arcs1_rows.get()
        self.assertEqual(arc.distance, 10)
        self.assertEqual(arc.loading_unloading_time, .8)
        self.assertEqual(record.demand_rows.get().population, 1000)
        sensor = record.salmonella_rows.get()
        self.assertTrue(sensor.has_sensor)
        self.assertEqual(sensor.fixed_intervention_cost, 25)

    def test_nonzero_salmonella_result_survives_encrypted_database_round_trip(self):
        record = Request.objects.create(
            requested_by=self.owner, title="Result", original_filename="result.xlsx",
        )
        row = salmonella_node_result.objects.create(
            request=record, product="Raw", node="Market", value=1.25,
        )
        row.refresh_from_db()
        self.assertEqual(row.value, 1.25)

    def test_complete_result_generation_without_running_solver(self):
        class Variable:
            def __init__(self, value):
                self.X = value

        class Expression:
            def __init__(self, value):
                self.value = value

            def getValue(self):
                return self.value

        class Model:
            Status = GRB.OPTIMAL
            SolCount = 1
            ObjVal = 125.0
            ObjBound = 125.0
            MIPGap = 0.0

        record = Request.objects.create(
            requested_by=self.owner, title="Persistence test",
            original_filename="persistence.xlsx", status="RUNNING",
        )
        arc = ("Raw", "Source", "Raw", "Market")
        result = {
            "model": Model(),
            "Y": {(arc, "Truck"): Variable(1)},
            "X": {(arc, "Truck"): Variable(20)},
            "G": {("Raw", "Market"): Variable(2)},
            "E": {("Raw", "Market"): Variable(3)},
            "W": {arc: Variable(4)},
            "F": {("Raw", "Market"): Variable(5)},
            "T": {("Raw", "Market"): Variable(6)},
            "price": {("Raw", "Market"): Variable(7)},
            "eta": {
                ("Raw", "Source"): Variable(0),
                ("Raw", "Market"): Variable(1.5),
            },
            "Z": {("Raw", "Market"): Variable(1), ("Raw", "Source"): Variable(0)},
            "Z_intransit": {("Raw", "Source"): Variable(1), ("Raw", "Market"): Variable(0)},
            "real_profit": Expression(100), "revenue": Expression(200),
            "transport_cost": Expression(50), "gap_cost": Expression(10),
            "excess_cost": Expression(8), "artificial_cost": Expression(2),
            "fixed_diversion_cost": Expression(4),
            "variable_diversion_cost": Expression(6),
            "metrics": {"runtime_seconds": 12, "cpu_seconds": 10, "best_seconds": 5},
        }

        self.assertTrue(persist_optimization_result(record, result))
        record.refresh_from_db()
        self.assertEqual(record.status, "DONE")
        self.assertEqual(record.solver_status, "OPTIMAL")
        self.assertEqual(var_y.objects.filter(request=record).count(), 1)
        self.assertEqual(var_x.objects.filter(request=record).count(), 1)
        self.assertEqual(gap_result.objects.filter(request=record).count(), 1)
        self.assertEqual(excess_result.objects.filter(request=record).count(), 1)
        self.assertEqual(lead_time_result.objects.filter(request=record).count(), 1)
        self.assertEqual(cumulative_flow_time_result.objects.filter(request=record).count(), 1)
        self.assertEqual(shelf_time_result.objects.filter(request=record).count(), 1)
        self.assertEqual(price_result.objects.filter(request=record).count(), 1)
        self.assertEqual(salmonella_node_result.objects.filter(request=record).count(), 1)
        self.assertEqual(contamination_flag_result.objects.filter(request=record).count(), 1)
        self.assertEqual(intransit_flag_result.objects.filter(request=record).count(), 1)
        self.assertEqual(objective_summary.objects.get(request=record).objective_value, 125.0)

    def test_request_history_is_owner_scoped(self):
        Request.objects.create(requested_by=self.owner, title="Mine", original_filename="mine.xlsx")
        Request.objects.create(requested_by=self.other, title="Not mine", original_filename="other.xlsx")
        response = self.client.get(reverse("requests_list"))
        self.assertContains(response, "Mine")
        self.assertNotContains(response, "Not mine")

    def test_other_users_result_is_not_accessible(self):
        record = Request.objects.create(requested_by=self.other, title="Private", original_filename="private.xlsx")
        self.assertEqual(self.client.get(reverse("results_view", args=[record.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("results_download_excel", args=[record.pk])).status_code, 404)

    @patch("isdrequests.views.run_optimization_task.delay")
    def test_optimization_is_queued_without_running_in_web_request(self, delay):
        record = Request.objects.create(
            requested_by=self.owner, title="Queue me", original_filename="queue.xlsx", status="SAVED",
        )
        response = self.client.post(reverse("run_isdoptimization"), {"request_id": record.pk})
        self.assertRedirects(response, reverse("requests_list"))
        record.refresh_from_db()
        self.assertEqual(record.status, "QUEUED")
        self.assertEqual(record.solver_status, "QUEUED")
        self.assertIsNotNone(record.queued_at)
        delay.assert_called_once_with(record.pk)

    @patch("isdrequests.views.run_optimization_task.delay")
    def test_duplicate_queue_submission_is_ignored(self, delay):
        record = Request.objects.create(
            requested_by=self.owner, title="Already queued", original_filename="queue.xlsx", status="QUEUED",
        )
        response = self.client.post(reverse("run_isdoptimization"), {"request_id": record.pk})
        self.assertRedirects(response, reverse("requests_list"))
        delay.assert_not_called()

    def test_status_endpoint_is_owner_scoped(self):
        mine = Request.objects.create(
            requested_by=self.owner, title="Mine", original_filename="mine.xlsx", status="RUNNING",
        )
        theirs = Request.objects.create(
            requested_by=self.other, title="Theirs", original_filename="theirs.xlsx", status="RUNNING",
        )
        response = self.client.get(reverse("optimization_status", args=[mine.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "RUNNING")
        self.assertEqual(self.client.get(reverse("optimization_status", args=[theirs.pk])).status_code, 404)

    @patch("isdrequests.views.run_optimization_task.delay", side_effect=ConnectionError("Redis unavailable"))
    def test_queue_failure_is_recorded_without_exposing_internal_error(self, _delay):
        record = Request.objects.create(
            requested_by=self.owner, title="Queue failure", original_filename="queue.xlsx", status="SAVED",
        )
        response = self.client.post(reverse("run_isdoptimization"), {"request_id": record.pk})
        self.assertRedirects(response, reverse("requests_list"))
        record.refresh_from_db()
        self.assertEqual(record.status, "FAILED")
        self.assertEqual(record.solver_status, "QUEUE_ERROR")
        self.assertNotIn("Redis", record.solver_message)


REFERENCE_WORKBOOK = Path(__file__).resolve().parents[2] / "updated_Intelligent distribution" / "Sens-D Midwest Case Data v1.xls"


@skipUnless(
    REFERENCE_WORKBOOK.exists() and os.environ.get("RUN_ISD_REFERENCE") == "1",
    "Set RUN_ISD_REFERENCE=1 to run the local golden solver regression",
)
class ReferenceWorkbookSolveTests(TestCase):
    def test_reference_workbook_produces_feasible_solution(self):
        user = get_user_model().objects.create_user("solver", "solver@example.com", "password")
        record = Request.objects.create(
            requested_by=user, title="Reference solve", original_filename=REFERENCE_WORKBOOK.name,
            status="SAVED", model_version="sensd-midwest-v1",
        )
        persist_workbook(parse_workbook(REFERENCE_WORKBOOK), record)
        self.assertTrue(execute_optimization(record))
        record.refresh_from_db()
        self.assertEqual(record.status, "DONE")
        self.assertAlmostEqual(record.summary.objective_value, 353643.959072494, delta=1.0)
