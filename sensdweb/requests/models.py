from django.db import models

# Create your models here.

class Request(models.Model):
    request_id = models.AutoField(primary_key=True)
    user_request_id = models.TextField(null=True)
    final_excel = models.FileField(upload_to='excels/', null=True, blank=True)
    created_by = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.TextField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class AllNodes(models.Model):
    user_request_id = models.TextField()
    node_id = models.IntegerField()
    node_name = models.TextField()
    probability = models.FloatField()
    cumulative_cost = models.FloatField()
    demand_rate = models.FloatField()
    created_by = models.TextField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.TextField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)



class InitialNodes(models.Model):
    user_request_id = models.TextField()
    node_id = models.IntegerField()
    node_name = models.TextField()
    created_by = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.TextField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class FinishedGoods(models.Model):
    user_request_id = models.TextField()
    node_id = models.IntegerField()
    node_name = models.TextField()
    demand_rate = models.FloatField()
    created_by = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.TextField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


class Arc(models.Model):
    user_request_id = models.TextField()
    Arc_id = models.IntegerField()
    from_node_id = models.IntegerField()
    from_node_name = models.TextField()
    to_node_id = models.IntegerField()
    to_node_name = models.TextField()
    multiplier = models.FloatField()
    created_by = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.TextField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)



class PathogenTestingMethod(models.Model):
    user_request_id = models.TextField()
    ptm_id = models.IntegerField()
    pathogen_testing_method = models.TextField()
    created_by = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.TextField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class PathogenTestingMethodFNodes(models.Model):
    node_id = models.IntegerField()
    user_request_id = models.TextField()
    pathogen_testing_method_id = models.TextField()
    sensitivity = models.FloatField()
    direct_cost = models.FloatField()
    lead_time = models.FloatField()
    created_by = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.TextField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


class DynamicParameters(models.Model):
    user_request_id = models.TextField()
    dynamic_parameter_id = models.IntegerField()
    maxsteps_k = models.IntegerField()
    maxpercentage_alpha = models.FloatField()
    maxbudget_B = models.FloatField()
    created_by = models.TextField(null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.TextField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class ResultModel(models.Model):
    result_id = models.AutoField(primary_key=True)
    user_result_id = models.TextField(null=True)
    user_request_id = models.TextField(null=True)
    final_excel = models.FileField(upload_to='excels/', null=True, blank=True)
    created_by = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.TextField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class NodeResult(models.Model):
    result_id = models.TextField()
    request_id = models.TextField()
    node_id = models.TextField()
    direct_cost = models.FloatField()
    cumulative_cost = models.FloatField()
    demand_rate = models.FloatField()
    lead_time = models.FloatField()
    is_deleted = models.BooleanField(default=False)

class VariableResult(models.Model):
    result_id = models.TextField()
    request_id = models.TextField()
    variable_name = models.TextField()
    value = models.FloatField()
    is_deleted = models.BooleanField(default=False) 
    
