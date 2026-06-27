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


class CryptoQuoteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='crypto@example.com',
            password='StrongPass123!',
            first_name='Crypto',
            last_name='User',
        )
        self.client.force_login(self.user)

    @patch('transactions.views._crypto_prices_usd')
    def test_crypto_quote_endpoint_returns_coin_amount(self, mock_prices):
        mock_prices.return_value = {'bitcoin': Decimal('50000')}

        response = self.client.get(reverse('crypto_quote'), {'method': 'bitcoin', 'amount': '100'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['symbol'], 'BTC')
        self.assertEqual(data['crypto_amount'], '0.002000000000')

    @patch('transactions.views._crypto_prices_usd')
    def test_crypto_deposit_stores_estimated_coin_amount(self, mock_prices):
        mock_prices.return_value = {'ethereum': Decimal('2500')}

        response = self.client.post(reverse('deposit'), {
            'method': 'ethereum',
            'amount': '100',
            'reference': '0xabc',
        })

        self.assertEqual(response.status_code, 302)
        txn = Transaction.objects.get(user=self.user, method='ethereum')
        self.assertEqual(txn.crypto_symbol, 'ETH')
        self.assertEqual(txn.crypto_amount, Decimal('0.040000000000'))
        self.assertEqual(txn.crypto_rate_usd, Decimal('2500'))
