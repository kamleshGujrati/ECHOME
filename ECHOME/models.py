

from django.db import models
from django.utils import timezone
from accounts.models import User

import logging

logger = logging.getLogger(__name__)

class Status(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SENT = 'sent', 'Sent'
    DELETED = 'deleted', 'Deleted'


class TimeCapsule(models.Model):

    user=models.ForeignKey(User, on_delete=models.CASCADE)

    email = models.EmailField()

    cid = models.CharField(max_length=255)

    decryption_pass = models.CharField(max_length=255)

    storage_time = models.DateTimeField(default=timezone.now)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    unlock_time = models.IntegerField(default=0)  # in seconds

    file_ext = models.CharField(max_length=10, default='txt')

    file_mime = models.CharField(max_length=20, default='text/plain')
    class Meta:
        db_table = 'TimeCapsule'
    
    @classmethod
    def total_capsules_by_user(cls,user,status=None):
        if not status:
            return cls.objects.filter(user=user).values(
                "id","email","file_mime","status","unlock_time","storage_time")
        else:
            return cls.objects.filter(user=user,status=status).values(
                "id", "email", "file_mime", "status", "unlock_time", "storage_time")


    @classmethod
    def get_capsule_by_id(cls, capsule_id):
        try:
            return cls.objects.get(id=capsule_id)
        except cls.DoesNotExist:
            logger.warning(f"Time capsule with ID {capsule_id} not found.")
            return None
        
    @classmethod 
    def create_capsule(cls, user, email, cid, decryption_pass, unlock_time, file_ext, file_mime):
        
        capsule = cls.objects.create(
            user=user,
            email=email,
            cid=cid,
            decryption_pass=decryption_pass,
            unlock_time=unlock_time,
            file_ext=file_ext,
            file_mime=file_mime
        )
        logger.info(f"Time capsule created successfully for user {user.email}")
        return capsule

class File(models.Model):
    
    file_data = models.BinaryField()

    class Meta:
        db_table = 'file_storage'

    def store(file_bytes):
        f = file(file_data=file_bytes)
        f.save()
        return f.id

    def get_and_delete(file_id):
        try:
            f = file.objects.get(id=file_id)
            file_bytes = f.file_data
            f.delete()
            return file_bytes
        except file.DoesNotExist:
            return None
