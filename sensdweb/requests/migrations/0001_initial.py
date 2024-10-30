# Generated by Django 5.0.7 on 2024-10-03 05:18

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AllNodes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_request_id', models.CharField(max_length=500)),
                ('node_id', models.IntegerField()),
                ('node_name', models.CharField(max_length=100)),
                ('probability', models.FloatField()),
                ('cumulative_cost', models.FloatField()),
                ('demand_rate', models.FloatField()),
                ('created_by', models.CharField(blank=True, max_length=100, null=True)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_by', models.CharField(blank=True, max_length=100, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Arc',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_request_id', models.CharField(max_length=500)),
                ('Arc_id', models.IntegerField()),
                ('from_node_id', models.IntegerField()),
                ('from_node_name', models.CharField(max_length=500)),
                ('to_node_id', models.IntegerField()),
                ('to_node_name', models.CharField(max_length=500)),
                ('multiplier', models.FloatField()),
                ('created_by', models.CharField(max_length=100)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_by', models.CharField(blank=True, max_length=100, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='DynamicParameters',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_request_id', models.CharField(max_length=500)),
                ('dynamic_parameter_id', models.IntegerField()),
                ('maxsteps_k', models.IntegerField()),
                ('maxpercentage_alpha', models.FloatField()),
                ('maxbudget_B', models.FloatField()),
                ('created_by', models.CharField(max_length=100, null=True)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_by', models.CharField(blank=True, max_length=100, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='FinishedGoods',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_request_id', models.CharField(max_length=500)),
                ('node_id', models.IntegerField()),
                ('node_name', models.CharField(max_length=100)),
                ('demand_rate', models.FloatField()),
                ('created_by', models.CharField(max_length=100)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_by', models.CharField(blank=True, max_length=100, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='InitialNodes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_request_id', models.CharField(max_length=500)),
                ('node_id', models.IntegerField()),
                ('node_name', models.CharField(max_length=100)),
                ('created_by', models.CharField(max_length=100)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_by', models.CharField(blank=True, max_length=100, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='NodeResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('result_id', models.CharField(max_length=255)),
                ('request_id', models.CharField(max_length=255)),
                ('node_id', models.CharField(max_length=255)),
                ('direct_cost', models.FloatField()),
                ('cumulative_cost', models.FloatField()),
                ('demand_rate', models.FloatField()),
                ('lead_time', models.FloatField()),
                ('is_deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='PathogenTestingMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ptm_id', models.IntegerField()),
                ('user_request_id', models.CharField(max_length=500)),
                ('pathogen_testing_method', models.CharField(max_length=100)),
                ('created_by', models.CharField(max_length=100)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_by', models.CharField(blank=True, max_length=100, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='PathogenTestingMethodFNodes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('node_id', models.IntegerField()),
                ('user_request_id', models.CharField(max_length=500)),
                ('pathogen_testing_method_id', models.CharField(max_length=500)),
                ('sensitivity', models.FloatField()),
                ('direct_cost', models.FloatField()),
                ('lead_time', models.FloatField()),
                ('created_by', models.CharField(max_length=100)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_by', models.CharField(blank=True, max_length=100, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Request',
            fields=[
                ('request_id', models.AutoField(primary_key=True, serialize=False)),
                ('user_request_id', models.CharField(max_length=500, null=True)),
                ('final_excel', models.FileField(blank=True, null=True, upload_to='excels/')),
                ('created_by', models.CharField(max_length=100)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_by', models.CharField(blank=True, max_length=100, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='ResultModel',
            fields=[
                ('result_id', models.AutoField(primary_key=True, serialize=False)),
                ('user_result_id', models.CharField(max_length=500, null=True)),
                ('user_request_id', models.CharField(max_length=500, null=True)),
                ('final_excel', models.FileField(blank=True, null=True, upload_to='excels/')),
                ('created_by', models.CharField(max_length=100)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_by', models.CharField(blank=True, max_length=100, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='VariableResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('result_id', models.CharField(max_length=255)),
                ('request_id', models.CharField(max_length=255)),
                ('variable_name', models.CharField(max_length=255)),
                ('value', models.FloatField()),
                ('is_deleted', models.BooleanField(default=False)),
            ],
        ),
    ]
