
from __future__ import annotations
import logging
from .models import ScheduledTaskLog
from django.utils import timezone
from ECHOME.SMTP import send_email_with_attachment
from ECHOME.models import TimeCapsule ,file
from datetime import timedelta
from django.utils.timezone import now
from ECHOME.BLOCK_CHAIN import ChainContract
from ECHOME.IPFS import FilebaseIPFS
from .utility_functions import utility_functions


from celery import shared_task
from celery.utils.log import get_task_logger
contract = ChainContract()  # contract object
utility_client = utility_functions()
ipfsClient = FilebaseIPFS()  # filebase object



logger=get_task_logger(__name__)

def send_notification( ):
    """
    main task that notifies users about their expired time capsule
    and send them the file

    """
    log_entry = ScheduledTaskLog.objects.create(
        task_name="send_notification",
        status="running"
    )

    try:

        logger.info("Executing notification  task")

        expired_data = contract.get_expired_data()
        if not expired_data:
            logger.info("No expired data found")
            log_entry.status = "completed"
            log_entry.details = "No expired data found"
            return
        list_cid = expired_data["cids"]

        print("list of cid",list_cid)

        if not list_cid:
            logger.info("No expired CIDs found")
            log_entry.status = "completed"
            log_entry.details = "No expired CIDs found"
            return

        else:
            for cid in list_cid:
                try:
                    cid = cid.decode('utf-8').strip('\x00').strip() if isinstance(cid,bytes) else cid.strip()

                    print("for cid",cid)
                    capsules = TimeCapsule.objects.filter(cid=cid[-12:],status="pending")
                    if capsules.count() == 1:
                        capsule = capsules[0]
                    else:
                        current_time = now()
                        capsule = None
                        smallest_diff = None

                        for record in capsules:
                            time = record.storage_time + timedelta(seconds=record.unlock_time)
                            diff = abs((time - current_time).total_seconds())

                            if smallest_diff is None or diff < smallest_diff:
                                smallest_diff = diff
                                capsule = record

                    data = {
                        'cid': cid,
                        'email': capsule.email,
                        'decryption_pass': capsule.decryption_pass,
                        'storage_time': capsule.storage_time,
                        'file_ext': capsule.file_ext,
                        'file_mime': capsule.file_mime,
                    }
                    capsule.status = "sent"

                except TimeCapsule.DoesNotExist:
                    print("capsule dta in db  not found")
                    logger.error(f"Time capsule with CID {cid} not found.")
                    ipfsClient.delete_file_by_cid(cid)
                    continue

                '''get file from ipfs and check it '''

                print("getting file from ipfs")
                file_dict = ipfsClient.get_file_by_cid(cid)

                if not file_dict:
                    logger.error(f"Failed to retrieve file for CID {cid}")
                    print("file not found in filebase")
                    capsule.status = "failed"
                    capsule.save()
                    continue

                logger.info(f"File retrieved successfully for CID {cid}")


                ''''check if file is encrypted or not '''

                decrypted_file = utility_client.decrypt_aes256_cbc(file_dict["bytes"], data['decryption_pass'])
                file_dict['bytes'] = decrypted_file

                if not decrypted_file:
                    logger.error(f"Decryption failed for CID {cid}")
                    capsule.status = "failed"
                    capsule.save()
                    continue
                '''file type and extension '''

                file_dict['mime_type'] = data['file_mime']
                file_dict['ext'] = data['file_ext']


                '''send email with decrypted file '''
                print("email sending")

                diffrance = utility_client.detailed_time_difference(data['storage_time'])

                email_sent = send_email_with_attachment(
                    to_email=data['email'],
                    file_info=file_dict,
                    time=data['storage_time'],
                    time_difference = diffrance,
                )
                print("email sent")
                if not email_sent:
                    logger.error(f"Failed to send email for CID {cid}")
                    capsule.status = "failed"
                    capsule.save()
                    continue
                else:
                    logger.info(f"Email sent successfully for CID {cid}")
                    capsule.status = "sent"
                    capsule.save()

            log_entry.status = "completed"

        log_entry.details = "Task completed successfully"

    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        log_entry.status = "failed"
        log_entry.details = str(e)
        print("error", e)
    finally:
        log_entry.completed_at = timezone.now()
        log_entry.save()

def cleanup_old_logs(days_to_keep=7):
    """
    Cleans up old task logs
    """
    from django.utils import timezone
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=days_to_keep)
    deleted_count, _ = ScheduledTaskLog.objects.filter(
        started_at__lt=cutoff_date
    ).delete()

    logger.info(f"Deleted {deleted_count} old log entries")


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=600)
def run_send_notification(self):
    """
    Celery task wrapper that calls your existing send_notification() function.
    - bind=True gives self so you can retry manually if needed
    - max_retries and autoretry_for provide automatic retry behaviour
    """
    try:
        logger.info("Celery: starting send_notification wrapper")
        # Note: legacy_send_notification logs and handles DB entries already.
        send_notification()
        logger.info("Celery: send_notification finished")
        return {"status": "ok"}
    except Exception as exc:
        logger.exception("Celery: send_notification failed, will retry")
        # raise to let autoretry_for handle it, or manually retry:
        raise self.retry(exc=exc, countdown=60)


@shared_task
def do_uploads(file_id,capsule_id):
    file_bytes = file.get_and_delete(file_id)
    # get file bytes and delete from db
    cid = ipfsClient.upload_and_get_cid(file_bytes)  # upload file to IPFS and get CID
    capsule = TimeCapsule.objects.get(id=capsule_id)
    if not cid:
        capsule.status = "failed"
        capsule.save()
        return
    # update cid in database
    capsule.cid = cid[-12:]

    try:
        contract.store_data(cid, capsule.unlock_time)

    except Exception as e:
        ipfsClient.delete_file_by_cid(cid)
        print("failed to store to blockchain :", e)
        capsule.status = "failed"
    capsule.save()
