from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("isdrequests", "0010_remove_precedence_request_delete_diversion_and_more")]

    operations = [
        migrations.AddField(
            model_name="request",
            name="queued_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="request",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="request",
            name="finished_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="request",
            name="status",
            field=models.CharField(
                choices=[
                    ("NEW", "New"), ("SAVED", "Saved"), ("QUEUED", "Queued"),
                    ("RUNNING", "Running"), ("DONE", "Done"), ("FAILED", "Failed"),
                ],
                default="NEW",
                max_length=12,
            ),
        ),
    ]
