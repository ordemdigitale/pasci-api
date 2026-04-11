# app/services/cinetpay.py
"""
Service CinetPay — Intégration paiement en ligne
Documentation officielle : https://docs.cinetpay.com

Pour activer le paiement réel :
  1. Créer un compte sur https://cinetpay.com
  2. Récupérer l'API_KEY et le SITE_ID dans le dashboard
  3. Renseigner CINETPAY_API_KEY et CINETPAY_SITE_ID dans le fichier .env
  4. Mettre à jour CINETPAY_RETURN_URL et CINETPAY_NOTIFY_URL avec les URLs de prod

En attendant, le service fonctionne en mode SIMULATION :
  - Les inscriptions payantes sont acceptées immédiatement
  - payment_status reste "pending" jusqu'à la confirmation webhook
"""
import uuid
import httpx
from typing import Optional
from app.core.config import settings


class CinetPayService:

    def _generate_transaction_id(self) -> str:
        """Génère un identifiant de transaction unique"""
        return f"PASCI-{uuid.uuid4().hex[:16].upper()}"

    async def initier_paiement(
        self,
        amount: float,
        participant_name: str,
        participant_email: str,
        description: str,
        formation_slug: str,
        participant_phone: Optional[str] = None,
    ) -> dict:
        """
        Initie un paiement CinetPay.

        Retourne un dict avec :
          - transaction_id : ID unique de la transaction
          - payment_url    : URL vers laquelle rediriger l'utilisateur
          - simulated      : True si CinetPay n'est pas encore configuré
        """
        transaction_id = self._generate_transaction_id()

        # ── Mode SIMULATION (clés non configurées) ─────────────
        if not settings.cinetpay_configured:
            return {
                "transaction_id": transaction_id,
                "payment_url": f"/formations/paiement/simulation?tid={transaction_id}&amount={int(amount)}&slug={formation_slug}",
                "simulated": True,
            }

        # ── Mode PRODUCTION (clés configurées) ─────────────────
        # Séparer prénom et nom
        name_parts = participant_name.strip().split(" ", 1)
        customer_name = name_parts[0]
        customer_surname = name_parts[1] if len(name_parts) > 1 else name_parts[0]

        payload = {
            "apikey": settings.CINETPAY_API_KEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": transaction_id,
            "amount": int(amount),
            "currency": settings.CINETPAY_CURRENCY,
            "description": description,
            "return_url": f"{settings.CINETPAY_RETURN_URL}?slug={formation_slug}",
            "notify_url": settings.CINETPAY_NOTIFY_URL,
            "customer_name": customer_name,
            "customer_surname": customer_surname,
            "customer_email": participant_email,
            "customer_phone_number": participant_phone or "",
            "customer_address": "Côte d'Ivoire",
            "customer_city": "Abidjan",
            "customer_country": "CI",
            "customer_state": "CI",
            "customer_zip_code": "00225",
            "channels": "ALL",
            "lang": "fr",
            "metadata": formation_slug,
        }
        if settings.CINETPAY_API_PASSWORD:
            payload["apikey_password"] = settings.CINETPAY_API_PASSWORD

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(settings.CINETPAY_API_URL, json=payload)
            data = response.json()

        if response.status_code >= 400 or data.get("code") not in ("201", "00"):
            raise ValueError(f"CinetPay error [{response.status_code}]: {data.get('message', data)}")

        return {
            "transaction_id": transaction_id,
            "payment_url": data["data"]["payment_url"],
            "simulated": False,
        }

    async def verifier_paiement(self, transaction_id: str) -> dict:
        """
        Vérifie le statut d'une transaction CinetPay.

        Retourne un dict avec :
          - status   : "ACCEPTED" | "REFUSED" | "PENDING"
          - operator : opérateur utilisé (ex: "ORANGE_CI")
          - amount   : montant payé
        """
        if not settings.cinetpay_configured:
            # En simulation, on considère le paiement comme accepté
            return {"status": "ACCEPTED", "operator": "SIMULATION", "amount": 0}

        payload = {
            "apikey": settings.CINETPAY_API_KEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": transaction_id,
        }
        if settings.CINETPAY_API_PASSWORD:
            payload["apikey_password"] = settings.CINETPAY_API_PASSWORD

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                settings.CINETPAY_CHECK_URL,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return {
            "status": data.get("data", {}).get("status", "PENDING"),
            "operator": data.get("data", {}).get("payment_method", ""),
            "amount": data.get("data", {}).get("amount", 0),
        }


cinetpay_service = CinetPayService()
