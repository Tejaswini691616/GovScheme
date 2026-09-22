# PATH: GovScheme/utils/email_service.py
import os
import smtplib
from email.message import EmailMessage


def send_otp_email(receiver_email, otp):
    address = os.getenv("EMAIL_ADDRESS", "").strip()
    password = os.getenv("EMAIL_PASSWORD", "").strip()
    if not address or not password:
        return False
    msg = EmailMessage()
    msg["Subject"] = "SmartGov AI - Password Reset OTP"
    msg["From"] = address
    msg["To"] = receiver_email
    msg.set_content(f"Your SmartGov AI password reset OTP is {otp}. It expires in 10 minutes.")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
        smtp.login(address, password)
        smtp.send_message(msg)
    return True
