from datetime import timedelta
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from .models import TimeCapsule , File

from django.core.exceptions import ValidationError
from accounts.decorators import custom_login_required
from django.shortcuts import render ,redirect , get_object_or_404
from worker.utility_functions import utility_functions
from accounts.models import User
from worker.tasks import do_uploads


from .forms import TimeCapsuleForm


import logging

logger = logging.getLogger(__name__)




def homepage(request):
    return render(request, 'index.html')

@custom_login_required
def formpage(request):
    return render(request, 'form.html')


@custom_login_required
def process_secure_upload(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

    try:
        # Get the uploaded file object
        form = TimeCapsuleForm(request.POST, request.FILES)
        
        if not form.is_valid():
            logger.warning(f"Form validation failed: {form.errors}")
            return JsonResponse({'error': form.errors}, status=400)
        
        cleaned_data = form.cleaned_data

        file_bytes = cleaned_data['encrypted_file'].read()
        
        file_id=File.saveFile(file_bytes)
        
        capsule = TimeCapsule.create_capsule(
            user=request.custom_user,
            email=cleaned_data['email'],
            cid="yet to store in blockchain",
            decryption_pass=cleaned_data['decryption_password'],
            unlock_time=cleaned_data['unlock_time'],
            file_ext=cleaned_data['file_ext'],
            file_mime=cleaned_data['file_mime']
        )

        logger.info(f"Scheduling upload for file ID {file_id} and time capsule ID {capsule.id}")
        
            
        do_uploads.delay(file_id,capsule.id)

        logger.info(f"Time capsule created successfully for user {capsule.email}")
        
        return JsonResponse("stored successfully", safe=False, status=200)

    except Exception as e:
        logger.error(f"Error occurred while processing secure upload: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)


@custom_login_required
def dashboard(request):
    # decide user-type (example: add CharField user_type to User model)
    user_type = getattr(request.custom_user, 'user_type', None)

    msgs = TimeCapsule.objects.filter(user=request.custom_user).order_by('-storage_time')

    # add friendly "approx_time" (unlock_time is seconds stored)
    for m in msgs:
        m.approx_time = m.storage_time + timedelta(seconds=m.unlock_time)

    return render(request, 'dashboard.html',
                  {'messages': msgs, 'user_type': user_type})

@custom_login_required
def delete_time_capsule(request, id ):
    if request.custom_user.user_type != 'dev':
        logger.warning(f"User {request.custom_user.email} attempted to delete time capsule {id} without permission.")
        raise PermissionDenied
    msg = get_object_or_404(TimeCapsule, id=id, email=request.custom_user.email)
    msg.status = 'deleted'
    msg.save()
    messages.success(request, "Message marked deleted.")
    return redirect('dashboard')


def total_capsules_api(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET requests are allowed'}, status=405)

    try:
        capsule_data = {
            "total_users": User.objects.count(),
            "pending": TimeCapsule.objects.filter(status="pending").count(),
            "deleted": TimeCapsule.objects.filter(status="deleted").count(),
            "sent": TimeCapsule.objects.filter(status="sent").count(),
        }
        logger.info(f"Total capsules data: {capsule_data}")

        return JsonResponse({'total_capsules': capsule_data}, status=200)
    except Exception as e:
        logger.error(f"Error occurred while fetching total capsules data: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)


