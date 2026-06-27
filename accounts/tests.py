from django.test import TestCase
from django.urls import reverse
from .forms import RegisterForm
from .models import PasswordResetToken, User


class RegisterFormTests(TestCase):
    def valid_form_data(self, **overrides):
        data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'phone': '5550000000',
            'country': 'United States',
            'state': 'California',
            'dial_code': '+1',
            'password': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'terms': 'on',
        }
        data.update(overrides)
        return data

    def test_terms_agreement_is_required(self):
        form = RegisterForm(data=self.valid_form_data(terms=''))

        self.assertFalse(form.is_valid())
        self.assertIn('terms', form.errors)

    def test_registration_form_accepts_checked_terms(self):
        form = RegisterForm(data=self.valid_form_data())

        self.assertTrue(form.is_valid())


class ForgotPasswordTests(TestCase):
    def test_unknown_email_shows_error_and_does_not_create_token(self):
        response = self.client.post(reverse('forgot_password'), {'email': 'missing@example.com'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No account is registered with that email address.')
        self.assertContains(response, 'value="missing@example.com"')
        self.assertEqual(PasswordResetToken.objects.count(), 0)

    def test_registered_email_creates_reset_token(self):
        User.objects.create_user(
            email='known@example.com',
            password='StrongPass123!',
            first_name='Known',
            last_name='User',
        )

        response = self.client.post(reverse('forgot_password'), {'email': 'known@example.com'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A password reset link has been sent to your email.')
        self.assertEqual(PasswordResetToken.objects.count(), 1)
