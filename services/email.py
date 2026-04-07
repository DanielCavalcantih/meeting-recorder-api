import resend
import os

resend.api_key = os.getenv("RESEND_API_KEY")

def send_email(to_email: str):
    resend.Emails.send({
        "from": "MeetRec <onboarding@resend.dev>",
        "to": [to_email],
        "subject": "Seu resumo está pronto 🎉",
        "html": f"""
            <h2>Resumo finalizado</h2>
            <p>Sua reunião já está disponível.</p>
            <a href="{os.getenv("SITE_URL")}/meetings">Ver resumo</a>
        """
    })