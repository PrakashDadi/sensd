from django.test import TestCase
from django.urls import reverse

from .models import CustomUser, UserAdministrationAudit
from .user_management import create_encrypted_user, decrypt_identity


class UserControlDashboardTests(TestCase):
    def setUp(self):
        self.bootstrap = CustomUser.objects.create_user(
            username='bootstrap', email='bootstrap@example.test', password='StrongPass123!',
            is_active=True, is_staff=True, is_superuser=True,
        )
        self.admin = create_encrypted_user(
            username='admin-test', email='admin@example.test', password='StrongPass123!',
            role='Administrator', is_active=True, actor=self.bootstrap,
        )
        self.viewer = create_encrypted_user(
            username='viewer-test', email='viewer@example.test', password='StrongPass123!',
            role='Viewer', is_active=True, actor=self.admin,
        )

    def test_only_superusers_can_open_dashboard(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse('account_admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('account_admin_dashboard')).status_code, 200)

    def test_dashboard_decrypts_identity_without_rendering_ciphertext(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('account_admin_dashboard'))
        self.assertContains(response, 'viewer-test')
        self.assertContains(response, 'viewer@example.test')
        self.assertNotContains(response, 'ephemeral_public_key')

    def test_administrator_can_create_encrypted_user_with_role(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('account_admin_create'), {
            'username': 'analyst-one', 'email': 'analyst@example.test',
            'password': 'StrongPass123!', 'password_confirm': 'StrongPass123!',
            'role': 'Analyst', 'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        created = CustomUser.objects.order_by('-pk').first()
        self.assertEqual(decrypt_identity(created), ('analyst-one', 'analyst@example.test'))
        self.assertTrue(created.groups.filter(name='Analyst').exists())
        self.assertNotIn('analyst-one', created.username)

    def test_administrator_can_edit_encrypted_identity_and_role(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('account_admin_edit', args=[self.viewer.pk]), {
            'username': 'manager-one', 'email': 'manager@example.test',
            'role': 'Manager', 'is_active': 'on', 'new_password': '',
        })
        self.assertRedirects(response, reverse('account_admin_dashboard'))
        self.viewer.refresh_from_db()
        self.assertEqual(decrypt_identity(self.viewer), ('manager-one', 'manager@example.test'))
        self.assertTrue(self.viewer.is_staff)
        self.assertTrue(self.viewer.groups.filter(name='Manager').exists())

    def test_administrator_cannot_remove_own_admin_access(self):
        self.client.force_login(self.admin)
        username, email = decrypt_identity(self.admin)
        response = self.client.post(reverse('account_admin_edit', args=[self.admin.pk]), {
            'username': username, 'email': email, 'role': 'Viewer', 'is_active': 'on', 'new_password': '',
        })
        self.assertEqual(response.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_superuser)

    def test_toggle_is_post_only_and_self_deactivation_is_blocked(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('account_admin_toggle', args=[self.viewer.pk])).status_code, 405)
        self.assertEqual(self.client.post(reverse('account_admin_toggle', args=[self.admin.pk])).status_code, 403)

    def test_permanent_delete_requires_admin_password(self):
        self.client.force_login(self.admin)
        url = reverse('account_admin_delete', args=[self.viewer.pk])
        response = self.client.post(url, {'confirmation': 'DELETE', 'admin_password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CustomUser.objects.filter(pk=self.viewer.pk).exists())
        response = self.client.post(url, {'confirmation': 'DELETE', 'admin_password': 'StrongPass123!'})
        self.assertRedirects(response, reverse('account_admin_dashboard'))
        self.assertFalse(CustomUser.objects.filter(pk=self.viewer.pk).exists())
        self.assertTrue(UserAdministrationAudit.objects.filter(action='deleted').exists())
