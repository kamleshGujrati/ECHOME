

from django.db import models
from django.utils import timezone
from accounts.models import User


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

    def total_capsules_by_user(user,status=None):
        if not status:
            return TimeCapsule.objects.filter(user=user).values(
                "id","email","file_mime","status","unlock_time","storage_time")
        else:
            return TimeCapsule.objects.filter(user=user,status=status).values(
                "id", "email", "file_mime", "status", "unlock_time", "storage_time")




class file(models.Model):
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