from django.test import TestCase
from django.urls import reverse
from decimal import Decimal
from unittest.mock import patch
from accounts.models import SiteSettings, User
from .models import Transaction


class PaystackCallbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='paystack@example.com',
            password='StrongPass123!',
            first_name='Pay',
            last_name='Stack',
        )
        site = SiteSettings.get()
        site.paystack_enabled = True
        site.paystack_secret_key = 'sk_test_example'
        site.paystack_currency = 'NGN'
        site.save()

    def paystack_success(self, amount=10000, currency='NGN'):
        return {
            'status': True,
            'data': {
                'status': 'success',
                'amount': amount,
                'currency': currency,
            },
        }

    def test_successful_paystack_callback_credits_wallet(self):
        txn = Transaction.objects.create(
            user=self.user,
            type='deposit',
            method='paystack',
            amount='100.00',
            net_amount='100.00',
            status='pending',
            reference='DEP12345678',
            description='Paystack Deposit',
        )

        with patch('transactions.views._paystack_request', return_value=self.paystack_success()):
            response = self.client.get(reverse('paystack_callback'), {'reference': txn.reference})

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        txn.refresh_from_db()
        self.assertEqual(self.user.wallet_balance, Decimal('100.00'))
        self.assertEqual(txn.status, 'completed')

    def test_repeated_paystack_callback_does_not_credit_twice(self):
        txn = Transaction.objects.create(
            user=self.user,
            type='deposit',
            method='paystack',
            amount='100.00',
            net_amount='100.00',
            status='pending',
            reference='DEP87654321',
            description='Paystack Deposit',
        )

        with patch('transactions.views._paystack_request', return_value=self.paystack_success()):
            self.client.get(reverse('paystack_callback'), {'reference': txn.reference})
            self.client.get(reverse('paystack_callback'), {'reference': txn.reference})

        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet_balance, Decimal('100.00'))
