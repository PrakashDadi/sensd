import io
import json

from django.db import connection
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from openpyxl import Workbook

from authentication.models import CustomUser

from .models import Note, PoultryCredential, PoultryProfile, UploadDataset


@override_settings(
    DEMO_LOGIN_ENABLED=True,
    DEMO_LOGIN_USERNAME="demo",
    DEMO_LOGIN_PASSWORD="demo",
)
class PoultryDashboardTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="poultry-tester",
            email="poultry@example.test",
            password="test-password-only",
        )
        self.client.force_login(self.user)

    def connect_demo(self):
        return self.client.post(
            reverse("poultrydashboard:api_blu_login"),
            data=json.dumps({"uname": "demo", "upass": "demo"}),
            content_type="application/json",
        )

    def test_anonymous_access_uses_sensd_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("poultrydashboard:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_navigation_and_all_pages_render(self):
        self.assertEqual(self.connect_demo().status_code, 200)
        names = [
            "home",
            "connect",
            "profile",
            "sensor_feed",
            "visualizations",
            "ai",
            "ai_chat",
            "faq",
            "contact",
        ]
        for name in names:
            response = self.client.get(reverse(f"poultrydashboard:{name}"))
            self.assertEqual(response.status_code, 200, name)
        dashboard = self.client.get(reverse("gis-home"))
        self.assertContains(dashboard, reverse("poultrydashboard:home"))

    def test_demo_devices_and_measurements(self):
        self.connect_demo()
        devices = self.client.get(reverse("poultrydashboard:api_blu_devices"))
        self.assertEqual(devices.status_code, 200)
        device_id = devices.json()["devices"][0]["id"]
        measurements = self.client.get(
            reverse("poultrydashboard:api_blu_measurements"),
            {"id": device_id},
        )
        self.assertEqual(measurements.status_code, 200)
        self.assertGreater(len(measurements.json()["points"]), 0)

    def test_sensitive_profile_note_and_credentials_are_encrypted(self):
        self.connect_demo()
        profile_response = self.client.post(
            reverse("poultrydashboard:api_profile"),
            data=json.dumps(
                {
                    "firstName": "PrivateFirst",
                    "lastName": "PrivateLast",
                    "email": "private@example.test",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(profile_response.status_code, 200)
        note_response = self.client.post(
            reverse("poultrydashboard:api_notes"),
            data=json.dumps({"title": "PrivateTitle", "body": "PrivateBody"}),
            content_type="application/json",
        )
        self.assertEqual(note_response.status_code, 200)

        self.assertEqual(PoultryProfile.objects.get(owner=self.user).first_name, "PrivateFirst")
        self.assertEqual(Note.objects.get(owner=self.user).body, "PrivateBody")
        self.assertEqual(PoultryCredential.objects.get(owner=self.user).password, "demo")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT first_name, email FROM poultrydashboard_poultryprofile WHERE owner_id = %s",
                [self.user.pk],
            )
            stored_first, stored_email = cursor.fetchone()
            cursor.execute(
                "SELECT password FROM poultrydashboard_poultrycredential WHERE owner_id = %s",
                [self.user.pk],
            )
            stored_password = cursor.fetchone()[0]
            cursor.execute(
                "SELECT title, body FROM poultrydashboard_note WHERE owner_id = %s",
                [self.user.pk],
            )
            stored_title, stored_body = cursor.fetchone()

        for plaintext, stored in [
            ("PrivateFirst", stored_first),
            ("private@example.test", stored_email),
            ("demo", stored_password),
            ("PrivateTitle", stored_title),
            ("PrivateBody", stored_body),
        ]:
            self.assertNotEqual(stored, plaintext)

    def test_excel_upload_is_owned_and_encrypted(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["timestamp", "temperature"])
        sheet.append(["2026-01-01T00:00:00Z", 4.2])
        buffer = io.BytesIO()
        workbook.save(buffer)
        response = self.client.post(
            reverse("poultrydashboard:api_uploads"),
            {
                "file": SimpleUploadedFile(
                    "temperatures.xlsx",
                    buffer.getvalue(),
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        dataset = UploadDataset.objects.get(owner=self.user)
        self.assertEqual(dataset.headers, ["timestamp", "temperature"])
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name, headers, rows FROM poultrydashboard_uploaddataset WHERE id = %s",
                [dataset.pk],
            )
            stored = cursor.fetchone()
        self.assertNotIn("timestamp", " ".join(stored))

    def test_ai_chat_is_optional_without_api_key(self):
        response = self.client.post(
            reverse("poultrydashboard:api_ai_chat"),
            data=json.dumps({"prompt": "Summarize my sensors"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not configured", response.json()["error"])
