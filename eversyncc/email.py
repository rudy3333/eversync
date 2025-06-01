import sendgrid
from sendgrid.helpers.mail import Mail
from django.conf import settings
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired


signer = TimestampSigner()

def generate_token(email):
    return signer.sign(email)


def verify_token(token, max_age=3600):
    try:
        email = signer.unsign(token, max_age=max_age)
        return email
    except (BadSignature, SignatureExpired):
        return None

sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)

def send_verification_email(user_email, token):
    link = f"https://eversync.fly.dev/verify-email/?token={token}"
    message = Mail(
        from_email='eversync@hackclub.app',
        to_emails=user_email,
        subject='Verify Your Email',
        html_content=f'''
            <p>Hi there,</p>
            <p>Please verify your email by clicking the link below:</p>
            <a href="{link}">Verify Email</a>
        '''
    )
    sg.send(message)