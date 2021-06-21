from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.models import User
import datetime

from .models import Post, Category


@shared_task
def post_notify(post_id):
    post = Post.objects.get(id=post_id)
    subscribers_list = User.objects.filter(id__in=post.category.all().values('subscriber'))

    for user in subscribers_list:

        html_content = render_to_string(
            'news/send_notify_post_create.html',
            {
                'username': user.username,
                'post': post,
                'post_text': post.text[:50],
            }
        )

        email_text = EmailMultiAlternatives(
            subject=post.header,
            body='text',
            from_email='nedgalkin@gmail.com',
            to=[user.email],
        )
        email_text.attach_alternative(html_content, "text/html")
        email_text.send()


@shared_task
def weekly_post_notify():
    today_date = datetime.datetime.now()
    week_ago_date = today_date - datetime.timedelta(weeks=1)
    category_list = Category.objects.all()

    for category in category_list:
        post_list = Post.objects.filter(category=category, time__range=(week_ago_date, today_date))
        if post_list:
            subscribers_list = category.subscriber.all()
            email_list = list(email['email'] for email in subscribers_list.values('email'))

            html_content = render_to_string(
                'news/send_notify_weekly.html',
                {
                    'post_list': post_list,
                }
            )

            email_text = EmailMultiAlternatives(
                subject='Еженедельная рассылка новостей',
                body='text',
                from_email='nedgalkin@gmail.com',
                to=email_list,
            )
            email_text.attach_alternative(html_content, "text/html")
            email_text.send()
