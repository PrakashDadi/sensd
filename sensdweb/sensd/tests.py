from django.test import TestCase
from django.urls import reverse

from authentication.models import CustomUser, UserKey
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


class OptimizationWorkspaceTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='optimization-user',
            email='optimization@example.test',
            password='test-password-only',
        )
        public_key, private_key = UserKey.generate_key_pair()
        UserKey.objects.create(
            user=self.user,
            public_key=public_key,
            private_key=private_key,
        )
        self.client.force_login(self.user)
        session = self.client.session
        session['uservalues'] = {
            'pk': self.user.pk,
            'username': 'optimization-user',
            'email': 'optimization@example.test',
            'isactive': True,
        }
        session.save()

    def test_dashboard_is_limited_to_optimization_tools(self):
        response = self.client.get(reverse('sensd'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sensor Placement Optimization')
        self.assertContains(response, 'Intelligent Distribution Optimization')
        self.assertContains(response, 'Recent Sensor Placement results')
        self.assertNotContains(response, '<h2>Poultry Dashboard</h2>', html=True)
        self.assertContains(response, 'navbar-light sensd-navbar')
        self.assertNotContains(response, 'navbar-dark sensd-navbar')

    def test_optimization_navigation_preserves_existing_workflow_routes(self):
        response = self.client.get(reverse('sensd'))

        self.assertContains(response, 'Sensor Placement')
        self.assertContains(response, 'Optimization activity')
        for route_name in ('new_request', 'upload_excel', 'user_requests', 'isdrequests_home', 'requests_list'):
            self.assertContains(response, reverse(route_name))

    def test_sensor_upload_uses_sensor_placement_language(self):
        response = self.client.get(reverse('upload_excel'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sensor Placement Optimization')
        self.assertContains(response, 'Upload optimization workbook')

    def test_manual_request_pages_share_seven_step_navigation(self):
        request_id = 'Request-navigation-test'
        workflow_routes = (
            'AllNodes',
            'InitialNodes',
            'FinishedGoods',
            'ARCForm',
            'PTMForm',
            'PTMFNodesForm',
            'DynamicParameterForm',
        )

        for step_number, route_name in enumerate(workflow_routes, start=1):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name, args=[request_id]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Sensor Placement manual request progress')
                self.assertContains(response, f'Step {step_number} of 7')
                self.assertContains(response, 'aria-current="step"')
                for workflow_route in workflow_routes:
                    self.assertContains(response, reverse(workflow_route, args=[request_id]))

    def test_first_manual_request_page_uses_shared_application_shell(self):
        response = self.client.get(reverse('AllNodes', args=['Request-shell-test']))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SENSD platform navigation')
        self.assertContains(response, 'Optimization navigation')

    def test_optimization_activity_keeps_tool_workflows_separate(self):
        response = self.client.get(reverse('user_requests'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Optimization activity sections')
        self.assertContains(response, 'id="sensor-placement-activity"')
        self.assertContains(response, 'id="distribution-activity"')
        self.assertLess(
            response.content.index(b'id="sensor-placement-activity"'),
            response.content.index(b'id="distribution-activity"'),
        )
        self.assertContains(response, reverse('new_request'))
        self.assertContains(response, reverse('upload_excel'))
        self.assertContains(response, reverse('isdrequests_home'))
        self.assertContains(response, reverse('requests_list'))
        self.assertContains(response, 'No Sensor Placement requests yet')
        self.assertContains(response, 'No Intelligent Distribution requests yet')

    def test_distribution_history_links_back_to_combined_activity(self):
        response = self.client.get(reverse('requests_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detailed request history')
        self.assertContains(response, f'{reverse("user_requests")}#distribution-activity')
