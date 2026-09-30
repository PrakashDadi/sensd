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
