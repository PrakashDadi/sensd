from django.db import models

from encrypted_fields.fields import (
    EncryptedCharField,
    EncryptedTextField,
    EncryptedIntegerField,
    EncryptedFloatField,
    EncryptedBooleanField,
    EncryptedJSONField,
    EncryptedDateTimeField,
)

from sensdweb.fields import CoercedEncryptedBooleanField
# Create your models here.

class Request(models.Model):
    request_id = models.AutoField(primary_key=True)
    user_request_id = models.TextField(null=True)
    final_excel = models.FileField(upload_to='excels/', null=True, blank=True)
    created_by = EncryptedTextField()
    created_on = EncryptedDateTimeField(auto_now_add=True)
    updated_by = EncryptedTextField(null=True, blank=True)
    updated_on = EncryptedDateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class AllNodes(models.Model):
    user_request_id = models.TextField()
    node_id = models.IntegerField()
    node_name = EncryptedTextField()
    probability = EncryptedFloatField()
    cumulative_cost = EncryptedFloatField()
    demand_rate = EncryptedFloatField()
    created_by = EncryptedTextField(null=True, blank=True)
    created_on = EncryptedDateTimeField(auto_now_add=True)
    updated_by = EncryptedTextField(null=True, blank=True)
    updated_on = EncryptedDateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)



class InitialNodes(models.Model):
    user_request_id = models.TextField()
    node_id = models.IntegerField()
    node_name = EncryptedTextField()
    created_by = EncryptedTextField()
    created_on = EncryptedDateTimeField(auto_now_add=True)
    updated_by = EncryptedTextField(null=True, blank=True)
    updated_on = EncryptedDateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class FinishedGoods(models.Model):
    user_request_id = models.TextField()
    node_id = models.IntegerField()
    node_name = EncryptedTextField()
    demand_rate = EncryptedFloatField()
    created_by = EncryptedTextField()
    created_on = EncryptedDateTimeField(auto_now_add=True)
    updated_by = EncryptedTextField(null=True, blank=True)
    updated_on = EncryptedDateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


class Arc(models.Model):
    user_request_id = models.TextField()
    Arc_id = models.IntegerField()
    from_node_id = models.IntegerField()
    from_node_name = EncryptedTextField()
    to_node_id = EncryptedIntegerField()
    to_node_name = EncryptedTextField()
    multiplier = EncryptedFloatField()
    created_by = EncryptedTextField()
    created_on = EncryptedDateTimeField(auto_now_add=True)
    updated_by = EncryptedTextField(null=True, blank=True)
    updated_on = EncryptedDateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


class PathogenTestingMethod(models.Model):
    user_request_id = models.TextField()
    ptm_id = models.IntegerField()
    pathogen_testing_method = EncryptedTextField()
    created_by = EncryptedTextField()
    created_on = EncryptedDateTimeField(auto_now_add=True)
    updated_by = EncryptedTextField(null=True, blank=True)
    updated_on = EncryptedDateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class PathogenTestingMethodFNodes(models.Model):
    node_id = models.IntegerField()
    user_request_id = models.TextField()
    pathogen_testing_method_id = models.TextField()
    sensitivity = EncryptedFloatField()
    direct_cost = EncryptedFloatField()
    lead_time = EncryptedFloatField()
    created_by = EncryptedTextField()
    created_on = EncryptedDateTimeField(auto_now_add=True)
    updated_by = EncryptedTextField(null=True, blank=True)
    updated_on = EncryptedDateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


class DynamicParameters(models.Model):
    user_request_id = models.TextField()
    dynamic_parameter_id = models.IntegerField()
    maxsteps_k = EncryptedIntegerField()
    maxpercentage_alpha = EncryptedFloatField()
    maxbudget_B = EncryptedFloatField()
    created_by = EncryptedTextField(null=True)
    created_on = EncryptedDateTimeField(auto_now_add=True)
    updated_by = EncryptedTextField(null=True, blank=True)
    updated_on = EncryptedDateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class ResultModel(models.Model):
    result_id = models.AutoField(primary_key=True)
    user_result_id = models.TextField(null=True)
    user_request_id = models.TextField(null=True)
    final_excel = models.FileField(upload_to='excels/', null=True, blank=True)
    created_by = EncryptedTextField()
    created_on = EncryptedDateTimeField(auto_now_add=True)
    updated_by = EncryptedTextField(null=True, blank=True)
    updated_on = EncryptedDateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class NodeResult(models.Model):
    result_id = models.TextField()
    request_id = models.TextField()
    node_id = EncryptedTextField()
    direct_cost = EncryptedFloatField(null = True)
    cumulative_cost = EncryptedFloatField(null = True)
    demand_rate = EncryptedFloatField(null = True)
    lead_time = EncryptedFloatField(null = True)
    is_deleted = models.BooleanField(default=False)

class VariableResult(models.Model):
    result_id = models.TextField()
    request_id = models.TextField()
    variable_name = EncryptedTextField()
    value = EncryptedFloatField(null = True)
    is_deleted = models.BooleanField(default=False)

