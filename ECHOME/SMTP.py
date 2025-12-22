from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from django.template.loader import render_to_string
from django.conf import settings
import smtplib


def send_email_with_attachment(file_info, to_email, time, time_difference, subject=None,
                               template_name='mail.html', context_extra=None):

    gmail_user = 'echhouss@gmail.com'
    gmail_pass = settings.GMAIL_PASSWORD
    subject = subject or "🔓 Your Decrypted File is Attached!"

    context = {
        'time': time,
        'time_difference': time_difference,
        'file_name': f"attachment{file_info['ext']}"
    }
    if context_extra:
        context.update(context_extra)

    body_html = render_to_string(template_name, context)

    msg = MIMEMultipart()
    msg['Subject'] = subject.replace('\n', ' ').strip()
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg.attach(MIMEText(body_html, 'html'))

    #  Use MIMEApplication to safely attach raw bytes
    attachment = MIMEApplication(file_info['bytes'], Name=f"attachment{file_info['ext']}")
    attachment.add_header(
        'Content-Disposition',
        f'attachment; filename="attachment{file_info["ext"]}"'
    )
    msg.attach(attachment)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.send_message(msg)
        print(" Email sent successfully!")
        return True
    except Exception as e:
        print(f" Failed to send email: {str(e)}")
        return False
