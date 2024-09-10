from django.db import models

# Create your models here.

class Request(models.Model):
    request_id = models.AutoField(primary_key=True)
    user_request_id = models.CharField(max_length=500, null= True)
    final_excel = models.FileField(upload_to='excels/', null=True, blank=True)
    created_by = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class AllNodes(models.Model):
    user_request_id = models.CharField(max_length=500)
    node_id = models.IntegerField()
    node_name = models.CharField(max_length=100)
    probability = models.FloatField()
    cumulative_cost = models.FloatField()
    demand_rate = models.FloatField()
    created_by = models.CharField(max_length=100, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


class InitialNodes(models.Model):
    user_request_id = models.CharField(max_length=500)
    node_id = models.IntegerField()
    node_name = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class FinishedGoods(models.Model):
    user_request_id = models.CharField(max_length=500)
    node_id = models.IntegerField()
    node_name = models.CharField(max_length=100)
    demand_rate = models.FloatField()
    created_by = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


class Arc(models.Model):
    user_request_id = models.CharField(max_length=500)
    Arc_id = models.IntegerField()
    from_node_id = models.IntegerField()
    from_node_name = models.CharField(max_length=500)
    to_node_id = models.IntegerField()
    to_node_name = models.CharField(max_length=500)
    multiplier = models.FloatField()
    created_by = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)



class PathogenTestingMethod(models.Model):
    user_request_id = models.CharField(max_length=500)
    ptm_id = models.IntegerField()
    user_request_id = models.CharField(max_length=500)
    pathogen_testing_method = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

class PathogenTestingMethodFNodes(models.Model):
    node_id = models.IntegerField()
    user_request_id = models.CharField(max_length=500)
    pathogen_testing_method_id = models.CharField(max_length=500)
    sensitivity = models.FloatField()
    direct_cost = models.FloatField()
    lead_time = models.FloatField()
    created_by = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
