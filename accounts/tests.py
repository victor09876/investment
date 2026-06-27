from django.test import TestCase
from .forms import RegisterForm


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
