from django.conf import settings
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from urllib.parse import quote
from django.core.mail import send_mail



signer = TimestampSigner()

def generate_token(email):
    return signer.sign(email)


def verify_token(token, max_age=3600):
    try:
        email = signer.unsign(token, max_age=max_age)
        return email
    except (BadSignature, SignatureExpired):
        return None



def send_verification_email(user_email):
    token = generate_token(user_email)
    link = f"https://eversync.fly.dev/verify-email/?token={quote(token)}"
    subject = "Verify Your Email"
    message = f"Hi there,\n\nPlease verify your email by clicking the link below:\n{link}\n\nThanks!"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user_email]

    send_mail(subject, message, from_email, recipient_list)