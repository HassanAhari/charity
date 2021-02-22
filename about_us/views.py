from django.contrib.auth import get_user_model
from django.shortcuts import render
from accounts.models import User


def about_us(request):
    users = User.objects.all()
    context = {
        'users': users,
    }
    return render(request, 'about_us.html', context)