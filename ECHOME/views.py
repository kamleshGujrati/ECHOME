from datetime import timedelta
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from .models import TimeCapsule , file
# from .IPFS import FilebaseIPFS
# from .BLOCK_CHAIN import ChainContract
from django.core.exceptions import ValidationError
from accounts.decorators import custom_login_required
from django.shortcuts import render ,redirect , get_object_or_404
from worker.utility_functions import utility_functions
from accounts.models import User
from worker.tasks import do_uploads
# client = utility_functions()
#
# contract = ChainContract()  # Initialize the contract
# ipfs = FilebaseIPFS()

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
        file_bytes = request.FILES.get('encrypted_file').read()
        if not file_bytes:
            raise ValidationError("No file was uploaded")

        # Get form data
        user=request.custom_user
        unlock_time = int(request.POST.get('unlock_time'))
        email = request.POST.get('email')
        decryption_password = request.POST.get('password')
        ext = request.POST.get('file_ext')
        mime= request.POST.get('file_mime')


        if TimeCapsule.total_capsules_by_user(user,"pending").count() >= 3:
            raise ValidationError("You have reached the maximum limit of 3 time capsules.")

        # cid = ipfs.upload_and_get_cid(file_bytes)  # upload file to IPFS and get CID

        if not all([unlock_time, email, decryption_password]):
            raise ValidationError("All fields (unlock_time, email, password) are required")
        print("got all data ")

        '''
        
        storing cid and to sepoliaetherium  via smart contracts 
         
         '''

        # try:
        #     print("storing to blockchain")
        #     contract.store_data(cid,unlock_time)
        # except Exception as e:
        #     print("failed to store to blockchain")
        #     ipfs.delete_file_by_cid(cid)
        #     raise ValidationError("Failed to store data on the blockchain") from e



        '''
        storing to mysql database 

        '''
        capsule=TimeCapsule.objects.create(
            user=user,
            email=email,
            cid="yet to store in blockchain",
            decryption_pass = decryption_password,
            unlock_time = unlock_time,
            file_ext = ext,
            file_mime = mime
        )
        file_id=file.store(file_bytes)
        do_uploads.delay(file_id,capsule.id)

        return JsonResponse("stored successfully", safe=False, status=200)

    except Exception as e:
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
        print(capsule_data)

        return JsonResponse({'total_capsules': capsule_data}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


