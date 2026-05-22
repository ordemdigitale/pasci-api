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


_MERCI_DON = """
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
        <!-- Header vert -->
        <tr>
          <td style="background:#2A591D;padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;">PASCI</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,.80);font-size:14px;">Plateforme d'Appui à la Société Civile Ivoirienne</p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:40px;">
            <h2 style="margin:0 0 12px;color:#1a1a1a;font-size:22px;">Merci pour votre don ❤️</h2>
            <p style="margin:0 0 24px;color:#555;font-size:15px;line-height:1.6;">
              Bonjour <strong>{{ donor_name }}</strong>,<br><br>
              Nous avons bien reçu votre don et vous en remercions chaleureusement.
              Votre générosité contribue directement au renforcement des organisations de la société civile en Côte d'Ivoire.
            </p>

            <!-- Reçu -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;margin-bottom:28px;">
              <tr><td style="padding:24px;">
                <p style="margin:0 0 6px;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;">Reçu de don</p>
                <p style="margin:0;font-size:28px;font-weight:700;color:#2A591D;">{{ amount }} FCFA</p>
                {% if transaction_id %}
                <p style="margin:10px 0 0;font-size:12px;color:#9ca3af;">Référence : {{ transaction_id }}</p>
                {% endif %}
                <p style="margin:4px 0 0;font-size:12px;color:#9ca3af;">Date : {{ don_date }}</p>
              </td></tr>
            </table>

            <!-- Ce que votre don permet -->
            <p style="margin:0 0 12px;color:#1a1a1a;font-size:15px;font-weight:700;">Votre don permet de :</p>
            <ul style="margin:0 0 24px;padding-left:20px;color:#555;font-size:14px;line-height:1.9;">
              <li>Renforcer les capacités des OSC membres du CRASC</li>
              <li>Financer des formations professionnelles pour les acteurs de la société civile</li>
              <li>Soutenir les actions de plaidoyer et de défense des droits</li>
              <li>Favoriser le réseautage entre les organisations</li>
            </ul>

            <!-- CTA -->
            <table cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
              <tr><td style="background:#2A591D;border-radius:6px;">
                <a href="{{ site_url }}" style="display:inline-block;padding:12px 28px;color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;">
                  Visiter la plateforme →
                </a>
              </td></tr>
            </table>

            <p style="margin:0 0 12px;color:#555;font-size:14px;line-height:1.6;">
              Si vous avez des questions, contactez-nous à <a href="mailto:pdoc@plateforme-osci.org" style="color:#E05017;">pdoc@plateforme-osci.org</a>.
            </p>

            <p style="margin:0;color:#999;font-size:12px;border-top:1px solid #eee;padding-top:20px;">
              Cet email a été envoyé à {{ donor_email }}.<br>
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


_RESET_PASSWORD = """
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
            <h2 style="margin:0 0 12px;color:#1a1a1a;font-size:20px;">Réinitialisation de mot de passe</h2>
            <p style="margin:0 0 24px;color:#555;font-size:15px;line-height:1.6;">
              Bonjour <strong>{{ user_name }}</strong>,<br><br>
              Vous avez demandé la réinitialisation de votre mot de passe. Cliquez sur le bouton ci-dessous pour choisir un nouveau mot de passe.
            </p>
            <p style="margin:0 0 24px;color:#555;font-size:14px;line-height:1.6;">
              Ce lien est valable pendant <strong>1 heure</strong>. Si vous n'avez pas fait cette demande, ignorez cet email.
            </p>

            <!-- CTA -->
            <table cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
              <tr><td style="background:#E05017;border-radius:6px;">
                <a href="{{ reset_url }}" style="display:inline-block;padding:12px 28px;color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;">
                  Réinitialiser mon mot de passe →
                </a>
              </td></tr>
            </table>

            <p style="margin:0 0 16px;color:#888;font-size:12px;">
              Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br>
              <a href="{{ reset_url }}" style="color:#E05017;word-break:break-all;">{{ reset_url }}</a>
            </p>

            <p style="margin:0;color:#999;font-size:12px;border-top:1px solid #eee;padding-top:20px;">
              Cet email a été envoyé à {{ user_email }}.<br>
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


async def send_merci_don(
    *,
    donor_name: str,
    donor_email: str,
    montant: int,
    transaction_id: Optional[str] = None,
    don_date: Optional[str] = None,
) -> None:
    from datetime import datetime
    html = _render(
        _MERCI_DON,
        donor_name=donor_name,
        donor_email=donor_email,
        amount=f"{montant:,}".replace(",", " "),
        transaction_id=transaction_id,
        don_date=don_date or datetime.now().strftime("%d/%m/%Y"),
        site_url=settings.FRONTEND_URL.rstrip("/"),
    )
    await _send(
        to=donor_email,
        subject="Merci pour votre don — PASCI",
        html=html,
    )


_CONTACT_ACCUSE = """
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
            <h2 style="margin:0 0 12px;color:#1a1a1a;font-size:20px;">Votre message a bien été reçu ✓</h2>
            <p style="margin:0 0 24px;color:#555;font-size:15px;line-height:1.6;">
              Bonjour <strong>{{ prenom_nom }}</strong>,<br><br>
              Nous avons bien reçu votre message concernant <strong>« {{ motif }} »</strong> et nous vous en remercions.
              Notre équipe vous répondra dans les plus brefs délais.
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#fff8f5;border:1px solid #fde8dc;border-radius:8px;margin-bottom:24px;">
              <tr><td style="padding:20px;">
                <p style="margin:0 0 6px;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:.5px;">Récapitulatif</p>
                <p style="margin:4px 0;font-size:14px;color:#555;"><strong>Motif :</strong> {{ motif }}</p>
                {% if categorie %}<p style="margin:4px 0;font-size:14px;color:#555;"><strong>Catégorie :</strong> {{ categorie }}</p>{% endif %}
                {% if message_extrait %}<p style="margin:8px 0 0;font-size:14px;color:#555;font-style:italic;">« {{ message_extrait }} »</p>{% endif %}
              </td></tr>
            </table>
            <p style="margin:0 0 24px;color:#555;font-size:14px;line-height:1.6;">
              Pour toute urgence, vous pouvez nous joindre directement à
              <a href="mailto:pdoc@plateforme-osci.org" style="color:#E05017;">pdoc@plateforme-osci.org</a>
              ou au <strong>05 05 56 57 41</strong>.
            </p>
            <p style="margin:0;color:#999;font-size:12px;border-top:1px solid #eee;padding-top:20px;">
              Cet email a été envoyé à {{ email }}.<br>
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

_CONTACT_NOTIF_ADMIN = """
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
        <tr>
          <td style="background:#2A591D;padding:24px 40px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:700;">Nouveau message de contact</h1>
          </td>
        </tr>
        <tr>
          <td style="padding:32px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;margin-bottom:24px;">
              <tr style="background:#f9fafb;border-bottom:1px solid #e5e7eb;">
                <td style="padding:10px 16px;font-size:12px;font-weight:700;color:#6b7280;width:40%;">Champ</td>
                <td style="padding:10px 16px;font-size:12px;font-weight:700;color:#6b7280;">Valeur</td>
              </tr>
              <tr style="border-bottom:1px solid #f3f4f6;">
                <td style="padding:10px 16px;font-size:13px;color:#6b7280;">Nom complet</td>
                <td style="padding:10px 16px;font-size:13px;font-weight:600;color:#111827;">{{ prenom_nom }}</td>
              </tr>
              <tr style="border-bottom:1px solid #f3f4f6;background:#fafafa;">
                <td style="padding:10px 16px;font-size:13px;color:#6b7280;">Email</td>
                <td style="padding:10px 16px;font-size:13px;color:#111827;"><a href="mailto:{{ email }}" style="color:#E05017;">{{ email }}</a></td>
              </tr>
              {% if contact %}
              <tr style="border-bottom:1px solid #f3f4f6;">
                <td style="padding:10px 16px;font-size:13px;color:#6b7280;">Contact</td>
                <td style="padding:10px 16px;font-size:13px;color:#111827;">{{ contact }}</td>
              </tr>
              {% endif %}
              {% if categorie %}
              <tr style="border-bottom:1px solid #f3f4f6;background:#fafafa;">
                <td style="padding:10px 16px;font-size:13px;color:#6b7280;">Catégorie</td>
                <td style="padding:10px 16px;font-size:13px;color:#111827;">{{ categorie }}</td>
              </tr>
              {% endif %}
              {% if fonction %}
              <tr style="border-bottom:1px solid #f3f4f6;">
                <td style="padding:10px 16px;font-size:13px;color:#6b7280;">Fonction</td>
                <td style="padding:10px 16px;font-size:13px;color:#111827;">{{ fonction }}</td>
              </tr>
              {% endif %}
              {% if pays %}
              <tr style="border-bottom:1px solid #f3f4f6;background:#fafafa;">
                <td style="padding:10px 16px;font-size:13px;color:#6b7280;">Pays / Résidence</td>
                <td style="padding:10px 16px;font-size:13px;color:#111827;">{{ pays }}{% if lieu_residence %} — {{ lieu_residence }}{% endif %}</td>
              </tr>
              {% endif %}
              <tr style="border-bottom:1px solid #f3f4f6;">
                <td style="padding:10px 16px;font-size:13px;color:#6b7280;">Motif</td>
                <td style="padding:10px 16px;font-size:13px;font-weight:700;color:#E05017;">{{ motif }}</td>
              </tr>
            </table>
            {% if message %}
            <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#374151;">Message :</p>
            <p style="margin:0 0 24px;font-size:14px;color:#555;background:#f9fafb;border-left:3px solid #E05017;padding:12px 16px;border-radius:4px;line-height:1.7;white-space:pre-wrap;">{{ message }}</p>
            {% endif %}
            <table cellpadding="0" cellspacing="0">
              <tr><td style="background:#2A591D;border-radius:6px;">
                <a href="{{ backoffice_url }}" style="display:inline-block;padding:10px 24px;color:#ffffff;font-size:13px;font-weight:700;text-decoration:none;">
                  Voir dans le backoffice →
                </a>
              </td></tr>
            </table>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


async def send_contact_accuse(
    *,
    nom: str,
    prenoms: str,
    email: str,
    motif: str,
    categorie: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    prenom_nom = f"{prenoms} {nom}"
    message_extrait = (message[:120] + "…") if message and len(message) > 120 else message
    html = _render(
        _CONTACT_ACCUSE,
        prenom_nom=prenom_nom,
        email=email,
        motif=motif,
        categorie=categorie or "",
        message_extrait=message_extrait or "",
    )
    await _send(
        to=email,
        subject=f"Votre message a bien été reçu — PASCI",
        html=html,
    )


async def send_contact_notif_admin(
    *,
    nom: str,
    prenoms: str,
    email: str,
    motif: str,
    categorie: Optional[str] = None,
    fonction: Optional[str] = None,
    contact: Optional[str] = None,
    pays: Optional[str] = None,
    lieu_residence: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    html = _render(
        _CONTACT_NOTIF_ADMIN,
        prenom_nom=f"{prenoms} {nom}",
        email=email,
        motif=motif,
        categorie=categorie or "",
        fonction=fonction or "",
        contact=contact or "",
        pays=pays or "",
        lieu_residence=lieu_residence or "",
        message=message or "",
        backoffice_url=f"{frontend_url}/admin/contact",
    )
    await _send(
        to=settings.SMTP_FROM,
        subject=f"[Contact] Nouveau message — {motif} — {prenoms} {nom}",
        html=html,
    )


_CRASC_CONTACT_NOTIF = """
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
        <tr>
          <td style="background:#2A591D;padding:28px 40px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:700;">Message via le site PASCI</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,.80);font-size:14px;">Contact CRASC — {{ crasc_name }}</p>
          </td>
        </tr>
        <tr>
          <td style="padding:32px 40px;">
            <p style="margin:0 0 20px;color:#555;font-size:15px;line-height:1.6;">
              Un message a été envoyé au <strong>{{ crasc_name }}</strong> via la plateforme PASCI.
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;margin-bottom:24px;">
              <tr style="background:#f9fafb;">
                <td style="padding:10px 16px;font-size:12px;font-weight:700;color:#6b7280;width:35%;">Champ</td>
                <td style="padding:10px 16px;font-size:12px;font-weight:700;color:#6b7280;">Valeur</td>
              </tr>
              <tr style="border-top:1px solid #f3f4f6;">
                <td style="padding:10px 16px;font-size:13px;color:#6b7280;">Nom</td>
                <td style="padding:10px 16px;font-size:13px;font-weight:600;color:#111827;">{{ nom }}</td>
              </tr>
              <tr style="border-top:1px solid #f3f4f6;background:#fafafa;">
                <td style="padding:10px 16px;font-size:13px;color:#6b7280;">Email</td>
                <td style="padding:10px 16px;font-size:13px;color:#111827;"><a href="mailto:{{ email }}" style="color:#E05017;">{{ email }}</a></td>
              </tr>
              {% if telephone %}
              <tr style="border-top:1px solid #f3f4f6;">
                <td style="padding:10px 16px;font-size:13px;color:#6b7280;">Téléphone</td>
                <td style="padding:10px 16px;font-size:13px;color:#111827;">{{ telephone }}</td>
              </tr>
              {% endif %}
              <tr style="border-top:1px solid #f3f4f6;background:#fafafa;">
                <td style="padding:10px 16px;font-size:13px;color:#6b7280;">Objet</td>
                <td style="padding:10px 16px;font-size:13px;font-weight:700;color:#2A591D;">{{ objet }}</td>
              </tr>
            </table>
            <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#374151;">Message :</p>
            <p style="margin:0 0 24px;font-size:14px;color:#555;background:#f9fafb;border-left:3px solid #2A591D;padding:12px 16px;border-radius:4px;line-height:1.7;white-space:pre-wrap;">{{ message }}</p>
            <p style="margin:0;color:#999;font-size:12px;border-top:1px solid #eee;padding-top:20px;">
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

_CRASC_CONTACT_ACCUSE = """
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
            <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">Plateforme d'Appui à la Société Civile Ivoirienne</p>
          </td>
        </tr>
        <tr>
          <td style="padding:40px;">
            <h2 style="margin:0 0 12px;color:#1a1a1a;font-size:20px;">Votre message a bien été transmis ✓</h2>
            <p style="margin:0 0 24px;color:#555;font-size:15px;line-height:1.6;">
              Bonjour <strong>{{ nom }}</strong>,<br><br>
              Votre message concernant <strong>« {{ objet }} »</strong> a bien été transmis au <strong>{{ crasc_name }}</strong>.
              L'équipe vous répondra dans les plus brefs délais.
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;margin-bottom:24px;">
              <tr><td style="padding:20px;">
                <p style="margin:0 0 6px;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;">Récapitulatif</p>
                <p style="margin:4px 0;font-size:14px;color:#555;"><strong>Objet :</strong> {{ objet }}</p>
                <p style="margin:4px 0;font-size:14px;color:#555;font-style:italic;">« {{ message_extrait }} »</p>
              </td></tr>
            </table>
            <p style="margin:0;color:#999;font-size:12px;border-top:1px solid #eee;padding-top:20px;">
              Cet email a été envoyé à {{ email }}.<br>
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


async def send_crasc_contact(
    *,
    nom: str,
    email: str,
    telephone: Optional[str] = None,
    objet: str,
    message: str,
    crasc_name: str,
    email_pca: Optional[str] = None,
) -> None:
    """Envoie le message au PDOC et au PCA du CRASC, + accusé à l'expéditeur."""
    PDOC_EMAIL = "pdoc@plateforme-osci.org"

    html_notif = _render(
        _CRASC_CONTACT_NOTIF,
        nom=nom,
        email=email,
        telephone=telephone or "",
        objet=objet,
        message=message,
        crasc_name=crasc_name,
    )
    subject_notif = f"[Contact CRASC] {objet} — {nom}"

    # 1. PDOC (toujours)
    await _send(to=PDOC_EMAIL, subject=subject_notif, html=html_notif)

    # 2. PCA (si renseigné)
    if email_pca:
        await _send(to=email_pca, subject=subject_notif, html=html_notif)

    # 3. Accusé de réception à l'expéditeur
    message_extrait = (message[:120] + "…") if len(message) > 120 else message
    html_accuse = _render(
        _CRASC_CONTACT_ACCUSE,
        nom=nom,
        email=email,
        objet=objet,
        message_extrait=message_extrait,
        crasc_name=crasc_name,
    )
    await _send(
        to=email,
        subject=f"Votre message au {crasc_name} a bien été transmis — PASCI",
        html=html_accuse,
    )


async def send_reset_password(
    *,
    user_name: str,
    user_email: str,
    token: str,
) -> None:
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    reset_url = f"{frontend_url}/auth/reset-password?token={token}"
    html = _render(
        _RESET_PASSWORD,
        user_name=user_name,
        user_email=user_email,
        reset_url=reset_url,
    )
    await _send(
        to=user_email,
        subject="Réinitialisation de votre mot de passe PASCI",
        html=html,
    )
