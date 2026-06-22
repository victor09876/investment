# InvestPro — Django Investment Platform

A complete, professional investment platform built entirely with Django (templates, static files, session auth).

## 🚀 Quick Start

```bash
cd investpro_full
pip install -r requirements.txt
bash start.sh
```

Then open **http://127.0.0.1:8000** in your browser.

## 🔑 Login Credentials

| Role       | Email                   | Password     |
|------------|-------------------------|--------------|
| Demo User  | john@example.com        | Demo@1234    |
| Admin      | admin@investpro.com     | Admin@1234   |

## 📋 All Pages

### User Pages
| URL | Page |
|-----|------|
| `/login/` | Login |
| `/register/` | Register (with optional reg code) |
| `/forgot-password/` | Forgot Password |
| `/dashboard/` | Dashboard with stats & charts |
| `/investments/plans/` | Browse investment plans |
| `/investments/plans/<slug>/` | Invest in a plan |
| `/investments/my/` | My investments (active/completed/cancelled) |
| `/investments/calculator/` | ROI calculator |
| `/transactions/deposit/` | Deposit funds (crypto, bank, card) |
| `/transactions/withdrawal/` | Withdraw funds with PIN |
| `/transactions/history/` | Full transaction history |
| `/notifications/` | Notifications |
| `/profile/` | Profile & referral program |
| `/settings/` | Account settings |
| `/change-password/` | Change password |
| `/set-pin/` | Set/change withdrawal PIN |

### Admin Panel (`/panel/`)
| URL | Page |
|-----|------|
| `/panel/` | Admin dashboard with KPIs |
| `/panel/users/` | Manage all users |
| `/panel/users/<id>/` | User detail — adjust balance, KYC, reset password |
| `/panel/transactions/` | Approve/reject deposits & withdrawals |
| `/panel/investments/` | View all investments |
| `/panel/plans/` | Create/manage investment plans |
| `/panel/settings/` | Site settings, wallet addresses, bank details |
| `/panel/reg-codes/` | Generate & manage registration codes |
| `/panel/credit-roi/` | Manually trigger daily ROI credit |

## ⚙️ Project Structure

```
investpro_full/
├── accounts/          ← Auth, user model, notifications
│   ├── models.py      ← User, SiteSettings, RegistrationCode, Notification
│   ├── views.py       ← Login, register, profile, dashboard
│   ├── admin_views.py ← Custom admin panel views
│   ├── forms.py       ← Django forms
│   ├── urls.py        ← User URLs
│   └── admin_urls.py  ← Admin panel URLs
├── investments/       ← Plans and investments
│   ├── models.py      ← Plan, Investment
│   ├── views.py       ← Plans list, invest, cancel, calculator
│   └── management/commands/credit_roi.py
├── transactions/      ← Deposits, withdrawals, history
│   ├── models.py      ← Transaction, WalletAddress
│   └── views.py       ← Deposit, withdrawal, history
├── templates/         ← All HTML templates
│   ├── base.html      ← Base HTML
│   ├── layout.html    ← Dashboard layout with sidebar
│   ├── accounts/      ← Auth + user templates
│   ├── investments/   ← Plan & investment templates
│   ├── transactions/  ← Finance templates
│   └── custom_admin/  ← Admin panel templates
├── static/
│   ├── css/style.css  ← Complete design system (navy + gold)
│   └── js/main.js     ← Utilities: toast, modal, tabs, charts
├── requirements.txt
├── start.sh           ← One-click startup
└── manage.py
```

## 🎫 Registration Code System

1. Go to **Admin Panel → Settings** → toggle "Require Registration Code" ON
2. Go to **Admin Panel → Reg. Codes** → Generate codes
3. Share codes with invited users — they enter it at registration
4. Toggle codes on/off, set max uses, set expiry dates

## ⚡ Daily ROI Credit

Run daily via cron to credit profits to active investments:

```bash
python manage.py credit_roi
```

Or from the admin panel: click **⚡ Credit ROI Now** in the sidebar.

Cron example (8am daily):
```
0 8 * * * cd /path/to/investpro_full && python manage.py credit_roi
```

## ✅ What Works

- Full user registration & login (session-based)
- Registration code gate (toggle on/off in admin)
- Dashboard with live stats, charts, active investments
- 4 investment plans with daily ROI
- Invest from wallet balance with referral bonus
- Cancel investment with configurable fee
- Deposit with 6 payment methods + proof upload
- Withdrawal with 4-digit PIN validation
- Full transaction history with filters
- Admin: approve/reject deposits & withdrawals
- Admin: adjust user balances, reset passwords
- Admin: KYC status management
- Admin: create/edit/delete investment plans
- Admin: configure wallet addresses & bank details
- Notification system (auto-created on events)
- Referral system with per-plan bonus %
- ROI calculator
