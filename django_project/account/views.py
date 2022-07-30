from django.shortcuts import render, redirect
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import login, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse

from ..models import Journal, JournalGroupEditors, UserProfile
from django.contrib.auth.models import User
import json

from django.conf import settings
import stripe
stripe.api_key = settings.GET_STRIPE_SECRET()

from mixpanel import Mixpanel
mp = Mixpanel('030864cc6061ba2b6fce33b1832408e2')

@login_required(login_url='/auth/login')
def settings(request):
    context = {}
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
        else:
            messages.error(request, 'Please correct the error below.')
        context['form'] = form
    else:
        form = PasswordChangeForm(request.user)
        context['form'] = form
    
        try: 
            journal = Journal.objects.get(user=request.user)
            editors = JournalGroupEditors.objects.all().filter(journal=journal)
            context['editors'] = editors
        except: 
            context['editors'] = {}

    return render(request, 'account/settings.html', context)

@login_required(login_url='/auth/login')
def add_editor(request):
    if request.method == 'POST':
        editor_username = request.POST['editor']
        editor_user = None
        try:
            editor_user = User.objects.get(username=editor_username)
        except:
            messages.error(request, 'This user does not exist')

        if editor_user is not None:
            journal_username = request.POST['journal_username']
            journal_user = User.objects.get(username=journal_username)
            journal = Journal.objects.get(user=journal_user)

            editor_profile = UserProfile.objects.filter(user=editor_user).first()
            if editor_profile.user_type != 'E':
                messages.error(request, 'This user is not an editor')
            else:
                JournalGroupEditors.objects.create(journal=journal, editor=editor_user)
                mp.track(request.user.id, 'Added an Editor', {"Editor Name": editor_user.username})
                messages.success(request, 'New editor added')

    return HttpResponseRedirect('/')


@login_required(login_url='/auth/login')
def remove_editor(request):
    if request.method == 'POST':
        editor_username = request.POST['editor']
        editor_user = None

        try:
            editor_user = User.objects.get(username=editor_username)
        except:
            messages.error(request, 'This user does not exist.')

        if editor_user is not None:

            editor_profile = UserProfile.objects.filter(user=editor_user).first()
            if editor_profile.user_type != 'E':
                messages.error(request, 'This user is not an editor')
            else:
                remove_editor = JournalGroupEditors.objects.get(editor=editor_user)
                JournalGroupEditors.delete(remove_editor)
                mp.track(request.user.id, 'Removed an Editor', {"Editor Name": editor_user.username})
                messages.success(request, 'Editor removed')

    return HttpResponseRedirect('/')

@login_required(login_url='/auth/login')
def payment(request):
    return render(request, "account/payment.html")

@login_required(login_url='/auth/login')
def status(request):
    if request.method == 'GET':
        client_secret = request.GET['setup_intent']
        setup_intent = stripe.SetupIntent.retrieve(client_secret,)
        status = setup_intent.status
        if status == 'succeeded':
            user_profile = UserProfile.objects.all().filter(user=request.user).first()
            user_profile.billing_saved = True
            user_profile.save()

    return render(request, "account/status.html")

@login_required(login_url='/auth/login')
def checkout(request):
    user_profile = UserProfile.objects.all().filter(user=request.user).first()

    intent = stripe.SetupIntent.create(
        customer = user_profile.stripe_id,
        payment_method_types = ["card"],
    )

    context = {}
    context['CLIENT_SECRET'] = intent.client_secret

    return render(request, 'account/checkout.html', context=context)
