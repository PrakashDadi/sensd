from django.test import TestCase
from django.urls import reverse

from authentication.models import CustomUser
from poultrydashboard.models import PoultryProfile

from .models import UserProfile


class SharedProfileTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='profile-user',
            email='profile@example.test',
            password='test-password-only',
        )
        self.client.force_login(self.user)

    def test_profile_is_created_for_authenticated_user(self):
        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'One profile shared across SENSD')
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

    def test_profile_update_is_owned_and_syncs_existing_poultry_profile(self):
        poultry = PoultryProfile.objects.create(owner=self.user)

        response = self.client.post(reverse('profile'), {
            'first_name': 'Ada',
            'last_name': 'Lovelace',
            'phone': '555-0100',
            'address': '1 Research Way',
            'city': 'Auburn',
            'state': 'AL',
            'postal_code': '36849',
            'photo_data_url': '',
        })

        self.assertRedirects(response, reverse('profile'))
        poultry.refresh_from_db()
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.first_name, 'Ada')
        self.assertEqual(profile.city, 'Auburn')
        self.assertEqual(poultry.first_name, 'Ada')
        self.assertEqual(poultry.email, 'profile@example.test')

    def test_legacy_and_poultry_profile_urls_redirect_to_shared_profile(self):
        legacy = self.client.get(reverse('profile_details', args=['ignored']))
        poultry = self.client.get(reverse('poultrydashboard:profile'))

        self.assertRedirects(legacy, reverse('profile'))
        self.assertEqual(poultry.status_code, 200)
        self.assertContains(poultry, 'One profile shared across SENSD')

    def test_anonymous_profile_access_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])


class PlatformHomeTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='platform-user',
            email='platform@example.test',
            password='test-password-only',
        )

    def test_authenticated_root_renders_three_workspace_choices(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'GIS Visualization')
        self.assertContains(response, 'SENSD Optimization Tools')
        self.assertContains(response, 'Poultry Analytics')
        self.assertContains(response, reverse('gis-home'))
        self.assertContains(response, reverse('sensd'))
        self.assertContains(response, reverse('poultrydashboard:home'))
        self.assertContains(response, 'SENSD platform navigation')

    def test_global_navigation_is_available_in_each_workspace_shell(self):
        self.client.force_login(self.user)

        for route_name in ('gis-home', 'poultrydashboard:home'):
            response = self.client.get(reverse(route_name))
            self.assertEqual(response.status_code, 200, route_name)
            self.assertContains(response, 'SENSD platform navigation')
            self.assertContains(response, reverse('index'))
            self.assertContains(response, reverse('gis-home'))
            self.assertContains(response, reverse('sensd'))
            self.assertContains(response, reverse('poultrydashboard:home'))

    def test_anonymous_root_still_uses_existing_login_flow(self):
        response = self.client.get(reverse('index'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])
