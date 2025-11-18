from django.db import models
from django.contrib.auth import get_user_model

from encrypted_fields.fields import (
    EncryptedCharField,
    EncryptedTextField,
    EncryptedIntegerField,
    EncryptedFloatField,
    EncryptedBooleanField,
    EncryptedJSONField,
    EncryptedDateTimeField,
)

User = get_user_model()


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Request(TimeStamped):
    STATUS_CHOICES = [
        ("NEW", "New"),
        ("SAVED", "Saved"),
        ("RUNNING", "Running"),
        ("DONE", "Done"),
        ("FAILED", "Failed"),
    ]
    requested_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    title = EncryptedCharField(max_length=200, default="Optimization Request")
    original_filename = EncryptedCharField(max_length=255, blank=True, default="")
    note = EncryptedTextField(blank=True, default="", null=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="NEW")

    def __str__(self):
        return f"Req#{self.pk} {self.title} [{self.status}]"


# -----------------------
# SHEET-SHAPED TABLES
# -----------------------

class sets(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="sets_rows")
    col_nodes = EncryptedCharField(max_length=120, blank=True, default="", null=True)
    col_sources = EncryptedCharField(max_length=120, blank=True, default="", null=True)
    col_processors = EncryptedCharField(max_length=120, blank=True, default="", null=True)
    col_warehouses = EncryptedCharField(max_length=120, blank=True, default="", null=True)
    col_retailers = EncryptedCharField(max_length=120, blank=True, default="", null=True)
    col_foodbanks = EncryptedCharField(max_length=120, blank=True, default="", null=True)
    col_markets = EncryptedCharField(max_length=120, blank=True, default="", null=True)
    col_modes = EncryptedCharField(max_length=120, blank=True, default="", null=True)
    col_products = EncryptedCharField(max_length=120, blank=True, default="", null=True)
    col_check_sal = EncryptedCharField(max_length=120, blank=True, default="", null=True)
    col_nocheck_sal = EncryptedCharField(max_length=120, blank=True, default="", null=True)


class arcs1(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="arcs1_rows")
    product = EncryptedCharField(max_length=120, blank=True, default="")        # col 0
    node_i = EncryptedCharField(max_length=120, blank=True, default="")         # col 1
    product_div = EncryptedCharField(max_length=120, blank=True, default="")    # col 2
    node_j = EncryptedCharField(max_length=120, blank=True, default="")         # col 3
    mode = EncryptedCharField(max_length=120, blank=True, default="")           # col 4
    capacity = EncryptedFloatField(default=0.0)                                  # col 6
    multiplier = EncryptedFloatField(default=1.0)                                # col 7
    fixed_cost = EncryptedFloatField(default=0.0)                                # col 8
    unit_cost = EncryptedFloatField(default=0.0)                                 # col 9
    lead_time = EncryptedFloatField(default=0.0)                                 # col 10


class arcs2(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="arcs2_rows")
    product = EncryptedCharField(max_length=120, blank=True, default="")
    node_i = EncryptedCharField(max_length=120, blank=True, default="")
    product_div = EncryptedCharField(max_length=120, blank=True, default="")
    node_j = EncryptedCharField(max_length=120, blank=True, default="")
    mode = EncryptedCharField(max_length=120, blank=True, default="")
    capacity = EncryptedFloatField(default=0.0)
    multiplier = EncryptedFloatField(default=1.0)
    fixed_cost = EncryptedFloatField(default=0.0)
    unit_cost = EncryptedFloatField(default=0.0)
    lead_time = EncryptedFloatField(default=0.0)


class arcs3(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="arcs3_rows")
    product = EncryptedCharField(max_length=120, blank=True, default="")
    node_i = EncryptedCharField(max_length=120, blank=True, default="")
    product_div = EncryptedCharField(max_length=120, blank=True, default="")
    node_j = EncryptedCharField(max_length=120, blank=True, default="")
    mode = EncryptedCharField(max_length=120, blank=True, default="")
    capacity = EncryptedFloatField(default=0.0)
    multiplier = EncryptedFloatField(default=1.0)
    fixed_cost = EncryptedFloatField(default=0.0)
    unit_cost = EncryptedFloatField(default=0.0)
    lead_time = EncryptedFloatField(default=0.0)


class diversion(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="diversion_rows")
    product = EncryptedCharField(max_length=120, blank=True, default="")
    node_i = EncryptedCharField(max_length=120, blank=True, default="")
    product_div = EncryptedCharField(max_length=120, blank=True, default="")
    node_j = EncryptedCharField(max_length=120, blank=True, default="")
    mode = EncryptedCharField(max_length=120, blank=True, default="")
    capacity = EncryptedFloatField(default=0.0)
    fixed_cost = EncryptedFloatField(default=0.0)
    unit_cost = EncryptedFloatField(default=0.0)
    lead_time = EncryptedFloatField(default=0.0)


class precedence(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="precedence_rows")
    product_in = EncryptedCharField(max_length=120, blank=True, default="")
    node_i = EncryptedCharField(max_length=120, blank=True, default="")
    product_out = EncryptedCharField(max_length=120, blank=True, default="")
    node_j = EncryptedCharField(max_length=120, blank=True, default="")


class demand(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="demand_rows")
    market = EncryptedCharField(max_length=120, blank=True, default="")     # col 0
    product = EncryptedCharField(max_length=120, blank=True, default="")    # col 1
    demand = EncryptedFloatField(default=0.0)                                # col 2
    gap_cost = EncryptedFloatField(default=0.0)                              # col 3


class supply(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="supply_rows")
    row_label = EncryptedCharField(max_length=120, blank=True, default="")   # typically a source name
    row_values = EncryptedJSONField(blank=True, null=True)                   # keys: product headers, values: capacities


class salmonella(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="salmonella_rows")
    node = EncryptedCharField(max_length=120, blank=True, default="")        # col 0
    product = EncryptedCharField(max_length=120, blank=True, default="")     # col 1
    level = EncryptedCharField(max_length=120, blank=True, default="NA")       # col 2 (can be number or 'NA')


# -----------------------
# RESULTS TABLES
# -----------------------

class objective_summary(TimeStamped):
    request = models.OneToOneField(Request, on_delete=models.CASCADE, related_name="summary")
    objective_value = EncryptedFloatField(default=0.0, null=True)  # m.ObjVal (Total_profit)
    total_profit = EncryptedFloatField(default=0.0, null=True)     # Real_profit (no artificial terms)
    total_revenue = EncryptedFloatField(default=0.0, null=True)
    total_transport_cost = EncryptedFloatField(default=0.0, null=True)
    total_gap_cost = EncryptedFloatField(default=0.0, null=True)
    total_excess_cost = EncryptedFloatField(default=0.0, null=True)
    total_intransit_penalty = EncryptedFloatField(default=0.0, null=True)
    fixed_diversion_cost = EncryptedFloatField(default=0.0, null=True)
    variable_diversion_cost = EncryptedFloatField(default=0.0, null=True)


class var_y(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="y_vars")
    product = EncryptedCharField(max_length=120)
    node_i = EncryptedCharField(max_length=120)
    product_div = EncryptedCharField(max_length=120)
    node_j = EncryptedCharField(max_length=120)
    mode = EncryptedCharField(max_length=120)
    value = EncryptedIntegerField(default=0)


class var_x(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="x_vars")
    product = EncryptedCharField(max_length=120)
    node_i = EncryptedCharField(max_length=120)
    product_div = EncryptedCharField(max_length=120)
    node_j = EncryptedCharField(max_length=120)
    mode = EncryptedCharField(max_length=120)
    quantity = EncryptedFloatField(default=0.0)


class gap_result(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="gaps")
    product = EncryptedCharField(max_length=120)
    market = EncryptedCharField(max_length=120)
    gap = EncryptedFloatField(default=0.0)


class excess_result(TimeStamped):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="excesses")
    product = EncryptedCharField(max_length=120)
    market = EncryptedCharField(max_length=120)
    excess = EncryptedFloatField(default=0.0)

class lead_time_result(TimeStamped):
    """
    W: lead time on each precedence arc (p, i, p', j).
    """
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="lead_times")
    product_in = EncryptedCharField(max_length=120)
    node_i = EncryptedCharField(max_length=120)
    product_out = EncryptedCharField(max_length=120)
    node_j = EncryptedCharField(max_length=120)
    lead_time = EncryptedFloatField(default=0.0)


class cumulative_flow_time_result(TimeStamped):
    """
    F: cumulative flow time at each product-node.
    """
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="flow_times")
    product = EncryptedCharField(max_length=120)
    node = EncryptedCharField(max_length=120)
    flow_time = EncryptedFloatField(default=0.0)


class shelf_time_result(TimeStamped):
    """
    T: shelf time of product at market.
    """
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="shelf_times")
    product = EncryptedCharField(max_length=120)
    market = EncryptedCharField(max_length=120)
    shelf_time = EncryptedFloatField(default=0.0)


class price_result(TimeStamped):
    """
    pi: market price of product at market.
    """
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="prices")
    product = EncryptedCharField(max_length=120)
    market = EncryptedCharField(max_length=120)
    price = EncryptedFloatField(default=0.0)


class salmonella_node_result(TimeStamped):
    """
    salmonella_estimation[p, node]: total accumulated salmonella when p' arrives at node j.
    """
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="salmonella_nodes")
    product = EncryptedCharField(max_length=120)
    node = EncryptedCharField(max_length=120)
    value = EncryptedFloatField(default=0.0)


class salmonella_intransit_result(TimeStamped):
    """
    S[precedence, mode]: in-transit salmonella estimation on arc & mode.
    """
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="salmonella_intransit")
    product_in = EncryptedCharField(max_length=120)
    node_i = EncryptedCharField(max_length=120)
    product_out = EncryptedCharField(max_length=120)
    node_j = EncryptedCharField(max_length=120)
    mode = EncryptedCharField(max_length=120)
    value = EncryptedFloatField(default=0.0)

