# app/services/email.py
"""
Service d'envoi d'emails via SMTP (compatible Mailpit en dev, SMTP réel en prod)
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib
from jinja2 import Environment, BaseLoader

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Templates HTML ────────────────────────────────────────────────────────────

_INSCRIPTION_GRATUITE = """
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
        <!-- Header -->
        <tr>
          <td style="background:#E05017;padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;">PASCI</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">Plateforme d'Appui à la Société Civile Ivoirienne</p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:40px;">
            <h2 style="margin:0 0 12px;color:#1a1a1a;font-size:20px;">Inscription confirmée ✓</h2>
            <p style="margin:0 0 24px;color:#555;font-size:15px;line-height:1.6;">
              Bonjour <strong>{{ participant_name }}</strong>,<br><br>
              Votre inscription à la formation <strong>« {{ formation_title }} »</strong> a bien été enregistrée.
            </p>

            <!-- Formation card -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#fff8f5;border:1px solid #fde8dc;border-radius:8px;margin-bottom:24px;">
              <tr><td style="padding:20px;">
                <p style="margin:0 0 8px;font-size:13px;color:#888;text-transform:uppercase;letter-spacing:.5px;">Formation</p>
                <p style="margin:0;font-size:17px;font-weight:700;color:#1a1a1a;">{{ formation_title }}</p>
                {% if start_date %}
                <p style="margin:8px 0 0;font-size:14px;color:#555;">📅 {{ start_date }}</p>
                {% endif %}
                {% if location %}
                <p style="margin:4px 0 0;font-size:14px;color:#555;">📍 {{ location }}</p>
                {% endif %}
                {% if trainer %}
                <p style="margin:4px 0 0;font-size:14px;color:#555;">👤 Formateur : {{ trainer }}</p>
                {% endif %}
              </td></tr>
            </table>

            <p style="margin:0 0 24px;color:#555;font-size:14px;line-height:1.6;">
              Un certificat vous sera délivré à la fin de la formation.
              Vous recevrez un email de confirmation avec votre code de certificat.
            </p>

            <!-- CTA -->
            <table cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
              <tr><td style="background:#E05017;border-radius:6px;">
                <a href="{{ formation_url }}" style="display:inline-block;padding:12px 28px;color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;">
                  Voir la formation →
                </a>
              </td></tr>
            </table>

            <p style="margin:0;color:#999;font-size:12px;border-top:1px solid #eee;padding-top:20px;">
              Cet email a été envoyé à {{ participant_email }}.<br>
              © {{ year }} PASCI — Plateforme d'Appui à la Société Civile Ivoirienne
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

_PAIEMENT_CONFIRME = """
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
        <tr>
          <td style="background:#E05017;padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;">PASCI</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">Plateforme d'Appui à la Société Civile Ivoirienne</p>
          </td>
        </tr>
        <tr>
          <td style="padding:40px;">
            <h2 style="margin:0 0 12px;color:#1a1a1a;font-size:20px;">Paiement reçu ✓</h2>
            <p style="margin:0 0 24px;color:#555;font-size:15px;line-height:1.6;">
              Bonjour <strong>{{ participant_name }}</strong>,<br><br>
              Votre paiement pour la formation <strong>« {{ formation_title }} »</strong> a été confirmé.
            </p>

            <table width="100%" cellpadding="0" cellspacing="0" style="background:#fff8f5;border:1px solid #fde8dc;border-radius:8px;margin-bottom:24px;">
              <tr><td style="padding:20px;">
                <p style="margin:0 0 8px;font-size:13px;color:#888;text-transform:uppercase;letter-spacing:.5px;">Reçu de paiement</p>
                <p style="margin:0;font-size:17px;font-weight:700;color:#1a1a1a;">{{ formation_title }}</p>
                <p style="margin:8px 0 0;font-size:15px;color:#E05017;font-weight:700;">{{ amount }} FCFA</p>
                {% if payment_date %}
                <p style="margin:6px 0 0;font-size:13px;color:#888;">Date : {{ payment_date }}</p>
                {% endif %}
                {% if transaction_id %}
                <p style="margin:4px 0 0;font-size:12px;color:#aaa;">Réf. : {{ transaction_id }}</p>
                {% endif %}
              </td></tr>
            </table>

            <table cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
              <tr><td style="background:#E05017;border-radius:6px;">
                <a href="{{ formation_url }}" style="display:inline-block;padding:12px 28px;color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;">
                  Accéder à la formation →
                </a>
              </td></tr>
            </table>

            <p style="margin:0;color:#999;font-size:12px;border-top:1px solid #eee;padding-top:20px;">
              Cet email a été envoyé à {{ participant_email }}.<br>
              © {{ year }} PASCI
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

_CERTIFICAT_EMIS = """
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
        <tr>
          <td style="background:#2A591D;padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;">PASCI</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">Certificat de réussite</p>
          </td>
        </tr>
        <tr>
          <td style="padding:40px;">
            <h2 style="margin:0 0 12px;color:#1a1a1a;font-size:20px;">Félicitations 🎓</h2>
            <p style="margin:0 0 24px;color:#555;font-size:15px;line-height:1.6;">
              Bonjour <strong>{{ participant_name }}</strong>,<br><br>
              Vous avez complété la formation <strong>« {{ formation_title }} »</strong>. Votre certificat est disponible.
            </p>

            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;margin-bottom:24px;">
              <tr><td style="padding:20px;text-align:center;">
                <p style="margin:0 0 8px;font-size:13px;color:#888;">Code de votre certificat</p>
                <p style="margin:0;font-size:28px;font-weight:700;color:#2A591D;letter-spacing:4px;font-family:monospace;">{{ cert_code }}</p>
                <p style="margin:8px 0 0;font-size:12px;color:#6b7280;">Utilisez ce code pour vérifier l'authenticité de votre certificat</p>
              </td></tr>
            </table>

            <p style="margin:0;color:#999;font-size:12px;border-top:1px solid #eee;padding-top:20px;">
              Cet email a été envoyé à {{ participant_email }}.<br>
              © {{ year }} PASCI
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


# ── Email sender ──────────────────────────────────────────────────────────────

_jinja = Environment(loader=BaseLoader())


def _render(template_str: str, **context) -> str:
    from datetime import datetime
    context.setdefault("year", datetime.now().year)
    return _jinja.from_string(template_str).render(**context)


async def _send(to: str, subject: str, html: str) -> None:
    """Envoie un email via SMTP async. Ne lève pas d'exception (log seulement)."""
    if not settings.SMTP_HOST:
        logger.warning("SMTP_HOST non configuré — email non envoyé à %s", to)
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to
        msg.attach(MIMEText(html, "html", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=settings.SMTP_TLS,
            start_tls=settings.SMTP_STARTTLS,
        )
        logger.info("Email envoyé → %s | %s", to, subject)
    except Exception as exc:
        logger.error("Erreur envoi email → %s : %s", to, exc)


# ── Public API ────────────────────────────────────────────────────────────────

async def send_inscription_confirmation(
    *,
    participant_name: str,
    participant_email: str,
    formation_title: str,
    formation_slug: str,
    start_date: Optional[str] = None,
    location: Optional[str] = None,
    trainer: Optional[str] = None,
) -> None:
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    html = _render(
        _INSCRIPTION_GRATUITE,
        participant_name=participant_name,
        participant_email=participant_email,
        formation_title=formation_title,
        start_date=start_date,
        location=location,
        trainer=trainer,
        formation_url=f"{frontend_url}/formations/{formation_slug}",
    )
    await _send(
        to=participant_email,
        subject=f"Inscription confirmée — {formation_title}",
        html=html,
    )


async def send_paiement_confirme(
    *,
    participant_name: str,
    participant_email: str,
    formation_title: str,
    formation_slug: str,
    amount: float,
    transaction_id: Optional[str] = None,
    payment_date: Optional[str] = None,
) -> None:
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    html = _render(
        _PAIEMENT_CONFIRME,
        participant_name=participant_name,
        participant_email=participant_email,
        formation_title=formation_title,
        amount=f"{amount:,.0f}".replace(",", " "),
        transaction_id=transaction_id,
        payment_date=payment_date,
        formation_url=f"{frontend_url}/formations/{formation_slug}",
    )
    await _send(
        to=participant_email,
        subject=f"Paiement confirmé — {formation_title}",
        html=html,
    )


async def send_certificat_emis(
    *,
    participant_name: str,
    participant_email: str,
    formation_title: str,
    cert_code: str,
) -> None:
    html = _render(
        _CERTIFICAT_EMIS,
        participant_name=participant_name,
        participant_email=participant_email,
        formation_title=formation_title,
        cert_code=cert_code,
    )
    await _send(
        to=participant_email,
        subject=f"Votre certificat PASCI — {formation_title}",
        html=html,
    )
