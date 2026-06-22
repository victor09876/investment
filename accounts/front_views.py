"""
Public marketing site views: Home, About, Contact, Blog, Top Investors, FAQ, How It Works.
Content for most pages comes from the FrontPage model (editable in /panel/pages/).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from .models import FrontPage, BlogPost, SiteSettings, User
from investments.models import Plan


def get_page(slug, default_title=''):
    page, _ = FrontPage.objects.get_or_create(slug=slug, defaults={'title': default_title or slug.title()})
    return page


def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    page = get_page('home', 'Home')
    plans = Plan.objects.filter(is_active=True).order_by('sort_order')[:4]
    posts = BlogPost.objects.filter(is_published=True).order_by('-created_at')[:3]
    from investments.models import Investment
    stats = {
        'total_users': User.objects.filter(is_staff=False).count(),
        'total_invested': Investment.objects.aggregate(t=Sum('amount'))['t'] or 0,
        'total_plans': Plan.objects.filter(is_active=True).count(),
    }
    return render(request, 'front/home.html', {'page': page, 'plans': plans, 'posts': posts, 'stats': stats})


def about_view(request):
    page = get_page('about', 'About Us')
    return render(request, 'front/about.html', {'page': page})


def contact_view(request):
    page = get_page('contact', 'Contact')
    site = SiteSettings.get()
    if request.method == 'POST':
        from .email_utils import send_email
        name = request.POST.get('name','').strip()
        email = request.POST.get('email','').strip()
        subject = request.POST.get('subject','').strip()
        body = request.POST.get('message','').strip()
        if name and email and body:
            send_email(site.support_email or site.company_email, f'Contact Form: {subject or "New message"}', 'contact_message',
                       {'name': name, 'email': email, 'subject': subject, 'message': body})
            messages.success(request, "Thanks for reaching out! We'll get back to you soon.")
        else:
            messages.error(request, 'Please fill in all required fields.')
        return redirect('front_contact')
    return render(request, 'front/contact.html', {'page': page, 'site': site})


def faq_view(request):
    page = get_page('faq', 'FAQ')
    faqs = []
    for line in page.content.splitlines():
        line = line.strip()
        if line.lower().startswith('q:'):
            rest = line[2:].strip()
            if '|' in rest and 'a:' in rest.lower():
                q_part, a_part = rest.split('|', 1)
                a_part = a_part.strip()
                if a_part.lower().startswith('a:'):
                    a_part = a_part[2:].strip()
                faqs.append({'q': q_part.strip(), 'a': a_part})
    return render(request, 'front/faq.html', {'page': page, 'faqs': faqs})


def how_it_works_view(request):
    page = get_page('how_it_works', 'How It Works')
    plans = Plan.objects.filter(is_active=True).order_by('sort_order')
    steps = [
        ('1', 'user-plus', 'Create Your Account', 'Sign up for free in under two minutes. No credit card required. Your account dashboard is ready immediately.'),
        ('2', 'id-card', 'Verify Your Identity', 'Complete a quick KYC check to unlock full withdrawal access. Upload a government ID and you\'ll be verified within 24 hours.'),
        ('3', 'wallet', 'Fund Your Wallet', 'Deposit via Bitcoin, USDT (TRC20 or ERC20), Ethereum, or PayPal. Funds are credited to your wallet as soon as your deposit is confirmed.'),
        ('4', 'gem', 'Activate an Investment Plan', 'Choose a plan that matches your goals, enter your investment amount, and activate it. Daily ROI is credited to your Profit Balance every 24 hours — automatically.'),
        ('5', 'money-bill-transfer', 'Withdraw Anytime', 'Once your plan matures (or your profit balance has funds), request a withdrawal. We process it to your crypto wallet or PayPal, usually within hours.'),
    ]
    return render(request, 'front/how_it_works.html', {'page': page, 'plans': plans, 'steps': steps})


def top_investors_view(request):
    """Real-data leaderboard based on total amount invested."""
    from investments.models import Investment
    leaders = (User.objects.filter(is_staff=False)
               .annotate(total_invested=Sum('investments__amount'))
               .filter(total_invested__gt=0)
               .order_by('-total_invested')[:20])
    return render(request, 'front/top_investors.html', {'leaders': leaders})


def blog_list_view(request):
    posts = BlogPost.objects.filter(is_published=True).order_by('-created_at')
    category = request.GET.get('category','')
    if category:
        posts = posts.filter(category=category)
    categories = BlogPost.objects.filter(is_published=True).exclude(category='').values_list('category', flat=True).distinct()
    return render(request, 'front/blog_list.html', {'posts': posts, 'categories': categories, 'active_category': category})


def blog_detail_view(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    related = BlogPost.objects.filter(is_published=True, category=post.category).exclude(pk=post.pk)[:3]
    return render(request, 'front/blog_detail.html', {'post': post, 'related': related})


def privacy_view(request):
    page = get_page('privacy', 'Privacy Policy')
    return render(request, 'front/legal.html', {'page': page})


def terms_view(request):
    page = get_page('terms', 'Terms & Conditions')
    return render(request, 'front/legal.html', {'page': page})


def handler404(request, exception=None):
    return render(request, '404.html', status=404)
