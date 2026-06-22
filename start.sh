#!/bin/bash
cd "$(dirname "$0")"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║          InvestPro — Django Platform         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "📦 Installing dependencies..."
pip install django Pillow -q

echo "🗄  Running migrations..."
python manage.py migrate --run-syncdb -v 0

echo "🌱 Seeding data..."
python manage.py shell -c "
from accounts.models import User, SiteSettings, RegistrationCode
from investments.models import Plan
from transactions.models import WalletAddress

if not User.objects.filter(email='admin@investpro.com').exists():
    User.objects.create_superuser(email='admin@investpro.com',password='Admin@1234',first_name='Admin',last_name='InvestPro')
    print('  Admin: admin@investpro.com / Admin@1234')

if not User.objects.filter(email='john@example.com').exists():
    u = User.objects.create_user(email='john@example.com',password='Demo@1234',first_name='John',last_name='Doe',country='United States')
    u.wallet_balance=24850; u.profit_balance=8320; u.is_kyc_verified=True; u.kyc_status='verified'; u.save()
    print('  Demo: john@example.com / Demo@1234')

s = SiteSettings.get()
s.bitcoin_address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh'
s.usdt_trc20_address='TFjLqNB7S4Xh5sW5yVq3YPnHJQn2pCHjdK'
s.ethereum_address='0x71C7656EC7ab88b098defB751B7401B5f6d8976F'
s.bank_name='InvestPro Financial Bank'; s.bank_account_name='InvestPro Ltd.'
s.bank_account_number='0123456789'; s.bank_routing='026009593'; s.bank_swift='CHASUS33'; s.save()

plans=[
  dict(name='Starter Plan',slug='starter',icon='medal',description='Perfect for new investors',daily_roi='1.5',duration_days=30,min_amount='100',max_amount='999',referral_bonus_pct='5',sort_order=1),
  dict(name='Silver Plan',slug='silver',icon='award',description='Our most popular choice',daily_roi='2.5',duration_days=60,min_amount='1000',max_amount='4999',referral_bonus_pct='7',sort_order=2),
  dict(name='Gold Plan',slug='gold',icon='gem',description='Best returns for serious investors',daily_roi='3.5',duration_days=90,min_amount='5000',max_amount='24999',referral_bonus_pct='10',is_featured=True,sort_order=3),
  dict(name='Platinum Plan',slug='platinum',icon='crown',description='Elite returns for high-net investors',daily_roi='5.0',duration_days=120,min_amount='25000',referral_bonus_pct='15',sort_order=4),
]
for p in plans: Plan.objects.get_or_create(slug=p['slug'],defaults=p)

for coin,addr,label in [('bitcoin','bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh','BTC'),('usdt_trc20','TFjLqNB7S4Xh5sW5yVq3YPnHJQn2pCHjdK','USDT TRC20'),('ethereum','0x71C7656EC7ab88b098defB751B7401B5f6d8976F','ETH')]:
    WalletAddress.objects.get_or_create(coin=coin,defaults={'address':addr,'label':label})

from accounts.models import Rank, KYCField, InvestmentDuration, CronJobLog, Branding
if Rank.objects.count() == 0:
    ranks=[dict(name='Beginner',color='#9CA3AF',min_deposit=100,min_referrals=1,min_investment=20,weekly_reward=2,rank_bonus_pct=1,special_roi_pct=0,description='Entry-level rank',sort_order=1),
           dict(name='Bronze',color='#92400E',min_deposit=500,min_referrals=3,min_investment=200,weekly_reward=10,rank_bonus_pct=2,special_roi_pct=0.2,description='Consistent small investors',sort_order=2),
           dict(name='Silver',color='#9CA3AF',min_deposit=2000,min_referrals=8,min_investment=1000,weekly_reward=35,rank_bonus_pct=3,special_roi_pct=0.5,description='Growing your portfolio',sort_order=3),
           dict(name='Gold',color='#C9A84C',min_deposit=10000,min_referrals=20,min_investment=5000,weekly_reward=120,rank_bonus_pct=5,special_roi_pct=1,description='Serious investors',sort_order=4),
           dict(name='Platinum',color='#E8C96A',min_deposit=50000,min_referrals=50,min_investment=25000,weekly_reward=500,rank_bonus_pct=8,special_roi_pct=2,description='Elite tier',sort_order=5)]
    for r in ranks: Rank.objects.create(**r)
    print('  5 ranks created')

if KYCField.objects.count() == 0:
    kfields=[dict(label='Full Legal Name',field_type='text',placeholder='As shown on ID',is_required=True,sort_order=1),
             dict(label='Date of Birth',field_type='date',is_required=True,sort_order=2),
             dict(label='National ID / Passport Number',field_type='text',is_required=True,sort_order=3),
             dict(label='Gender',field_type='select',options='Male,Female,Other',is_required=True,sort_order=4),
             dict(label='Government ID (Front)',field_type='image',is_required=True,sort_order=5),
             dict(label='Government ID (Back)',field_type='image',is_required=True,sort_order=6),
             dict(label='Proof of Address',field_type='file',is_required=True,sort_order=7),
             dict(label='Risk Tolerance',field_type='select',options='Low,Medium,High',is_required=False,sort_order=8),
             dict(label='Additional Notes',field_type='textarea',is_required=False,sort_order=9)]
    for f in kfields: KYCField.objects.create(**f)
    print('  9 KYC fields created')

if InvestmentDuration.objects.count() == 0:
    durations=[dict(label='1 Hour',value=1,unit='hours',days=1,sort_order=1),dict(label='6 Hours',value=6,unit='hours',days=1,sort_order=2),
               dict(label='12 Hours',value=12,unit='hours',days=1,sort_order=3),dict(label='24 Hours',value=24,unit='hours',days=1,sort_order=4),
               dict(label='3 Days',value=3,unit='days',days=3,sort_order=5),dict(label='7 Days',value=7,unit='days',days=7,sort_order=6),
               dict(label='30 Days',value=30,unit='days',days=30,sort_order=7),dict(label='60 Days',value=60,unit='days',days=60,sort_order=8),
               dict(label='90 Days',value=90,unit='days',days=90,sort_order=9)]
    for d in durations: InvestmentDuration.objects.create(**d)
    print('  9 investment durations created')

if CronJobLog.objects.count() == 0:
    CronJobLog.objects.create(name='Credit Daily ROI',slug='credit_roi',status='success')
    CronJobLog.objects.create(name='Ranking Updates',slug='ranking_update',status='success')
    CronJobLog.objects.create(name='Referral Commissions',slug='referral_commission',status='success')
    print('  Cron logs initialized')

Branding.get()

if RegistrationCode.objects.count() == 0:
    for i in range(5): RegistrationCode.objects.create(label=f'Invite Code {i+1}',max_uses=10)

from accounts.models import FrontPage, SidebarMenuItem, BlogPost
if FrontPage.objects.count() == 0:
    pages = [
        ('home','Grow Your Wealth With Confidence','Join a transparent, secure investment platform.',''),
        ('about','About Us','Our mission is to make investing accessible.','InvestPro was founded with a simple belief: every person deserves access to professional-grade investment tools.'),
        ('how_it_works','How It Works','Investing made simple — five steps and you are earning daily.',''),
        ('faq','Frequently Asked Questions','Everything you need to know before getting started.',''),
        ('contact','Get in Touch','Questions, ideas, or support — we are here.',''),
        ('privacy','Privacy Policy','How we collect, use, and protect your personal information.','# Privacy Policy\n\nPlease see our full policy below.'),
        ('terms','Terms & Conditions','Please read these terms carefully.','# Terms & Conditions\n\n## 1. Acceptance\n\nBy using our platform you agree to these terms.'),
    ]
    for slug, title, subtitle, content_val in pages:
        FrontPage.objects.create(slug=slug, title=title, subtitle=subtitle, content=content_val)
    print('  FrontPages seeded')
if SidebarMenuItem.objects.count() == 0:
    items = [('plans','Investment Plans'),('my_investments','My Investments'),('calculator','ROI Calculator'),('deposit','Deposit'),('withdrawal','Withdrawal'),('transactions_history','Transactions'),('transfer','Transfer'),('statement','Statement'),('investment_report','Investment Report'),('referrals','Referrals'),('ranking','Ranking'),('kyc','KYC Verification'),('notifications','Notifications'),('tickets','Support'),('login_history','Login History'),('profile','Profile'),('settings','Settings')]
    for i,(key,label) in enumerate(items): SidebarMenuItem.objects.create(key=key,label=label,sort_order=i)
    print('  SidebarMenuItems seeded')
if BlogPost.objects.count() == 0:
    BlogPost.objects.create(title='Welcome to InvestPro', slug='welcome-to-investpro', excerpt='Discover how InvestPro helps you grow your money with daily returns and transparent investment plans.', content='Welcome to InvestPro — your new home for smart, transparent investing.\n\nOur platform offers daily ROI across a range of carefully structured plans, designed to match investors at every level.\n\nGet started today by creating a free account, completing KYC, and making your first deposit.', category='News', author_name='InvestPro Team')
    print('  Default blog post created')

    print('  5 sample registration codes created')
print('  ✅ Database ready')
" 2>/dev/null

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅  Server starting...                      ║"
echo "║                                              ║"
echo "║  🌐  Open in browser:                        ║"
echo "║      http://127.0.0.1:8000                   ║"
echo "║                                              ║"
echo "║  👤  Demo login:                             ║"
echo "║      john@example.com / Demo@1234            ║"
echo "║                                              ║"
echo "║  🛡️   Admin panel:                           ║"
echo "║      http://127.0.0.1:8000/panel/            ║"
echo "║      admin@investpro.com / Admin@1234        ║"
echo "║                                              ║"
echo "║  ⚡  Credit ROI daily (run as cron):         ║"
echo "║      python manage.py credit_roi             ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

python manage.py runserver 0.0.0.0:8000
