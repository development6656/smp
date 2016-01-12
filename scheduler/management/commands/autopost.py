import urllib
import re
import requests

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from twitter import Twitter, OAuth

from scheduler.models import ScheduledPost


def post_to_facebook(post):
    try:
        account = SocialAccount.objects.get(user=post.user,
                                            provider=post.service)
    except SocialAccount.DoesNotExist:
        return None
    try:
        access_token = account.socialtoken_set.get().token
    except SocialToken.DoesNotExist:
        return None
    message = post.status.encode("utf-8")
    link = re.findall("https?://[^\s]+", post.status)
    params = {
        "message": message,
        "access_token": access_token
    }
    if link:
        params["link"] = link[0]
    response = requests.post(
        "https://graph.facebook.com/{0}/feed?{1}".format(
            account.uid,
            urllib.urlencode(params)
        ))
    if response.ok:
        post.is_posted = True
        post.save()
        


def post_to_twitter(post):
    app = SocialApp.objects.get(provider=post.service)
    try:
        account = SocialAccount.objects.get(user=post.user,
                                            provider=post.service)
    except SocialAccount.DoesNotExist:
        return None
    try:
        token = account.socialtoken_set.get().token
        token_secret = account.socialtoken_set.get().token_secret
    except SocialToken.DoesNotExist:
        return None
    twt = Twitter(auth=OAuth(token, token_secret, app.client_id, app.secret))
    twt.statuses.update(status=post.status.encode("utf-8"))
    post.is_posted = True
    post.save()


class Command(BaseCommand):
    help = 'Autopost to the social platforms'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        next_min = now + timezone.timedelta(minutes=1)
        for post in ScheduledPost.objects.filter(is_posted=False,
                                                 scheduled_datetime__gte=now,
                                                 scheduled_datetime__lt=next_min):
            if post.service == "facebook":
                post_to_facebook(post)
            elif post.service == "twitter":
                post_to_twitter(post)
