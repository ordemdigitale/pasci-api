# app/services/cinetpay.py
"""
Service CinetPay — Intégration paiement en ligne (API v1)
Documentation : https://docs.cinetpay.com

Authentification JWT via POST /v1/oauth/login
Paiement via POST /v1/payment (Bearer token)
Vérification via GET /v1/payment/{id} (Bearer token)

Sandbox  (sk_test_...) : https://api.cinetpay.net
Production (sk_live_...) : https://api.cinetpay.co
"""
import uuid
import httpx
from typing import Optional
from app.core.config import settings


class CinetPayService:

    def __init__(self):
        self._token: Optional[str] = None

    def _generate_transaction_id(self) -> str:
        """Génère un identifiant de transaction unique (max 30 chars)"""
        return f"PASCI-{uuid.uuid4().hex[:22].upper()}"

    async def _get_token(self) -> str:
        """Obtient un token JWT via POST /v1/oauth/login"""
        if self._token:
            return self._token

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{settings.cinetpay_base_url}/v1/oauth/login",
                json={
                    "api_key": settings.CINETPAY_API_KEY,
                    "api_password": settings.CINETPAY_API_PASSWORD,
                },
            )
            data = response.json()

        if not data.get("access_token"):
            raise ValueError(f"CinetPay auth failed: {data.get('status', data)}")

        self._token = data["access_token"]
        return self._token

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Effectue une requête authentifiée, avec retry si token expiré."""
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method,
                f"{settings.cinetpay_base_url}{path}",
                headers=headers,
                **kwargs,
            )
            data = response.json()

        # Token expiré → renouveler et réessayer une fois
        if data.get("code") == 1003 or data.get("status") == "EXPIRED_TOKEN":
            self._token = None
            token = await self._get_token()
            headers = {"Authorization": f"Bearer {token}"}
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(
                    method,
                    f"{settings.cinetpay_base_url}{path}",
                    headers=headers,
                    **kwargs,
                )
                data = response.json()

        return data

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
        Initie un paiement CinetPay (API v1).

        Retourne :
          - transaction_id   : ID unique côté marchand (à stocker)
          - notify_token     : token à stocker pour vérifier le webhook
          - payment_url      : URL vers laquelle rediriger l'utilisateur
          - simulated        : True si mode simulation
        """
        transaction_id = self._generate_transaction_id()

        # ── Mode SIMULATION ─────────────────────────────────────
        if not settings.cinetpay_configured:
            return {
                "transaction_id": transaction_id,
                "notify_token": "",
                "payment_url": f"/formations/paiement/simulation?tid={transaction_id}&amount={int(amount)}&slug={formation_slug}",
                "simulated": True,
            }

        # ── Mode PRODUCTION (API v1 JWT) ─────────────────────────
        name_parts = participant_name.strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else name_parts[0]

        payload = {
            "currency": settings.CINETPAY_CURRENCY,
            "merchant_transaction_id": transaction_id,
            "amount": int(amount),
            "lang": "fr",
            "designation": description[:100],
            "client_email": participant_email,
            "client_first_name": first_name,
            "client_last_name": last_name,
            "success_url": f"{settings.CINETPAY_RETURN_URL}?slug={formation_slug}&status=success",
            "failed_url": f"{settings.CINETPAY_FAILED_URL}&slug={formation_slug}",
            "notify_url": settings.CINETPAY_NOTIFY_URL,
            "channel": "PUSH",
        }
        if participant_phone:
            payload["client_phone_number"] = participant_phone

        data = await self._request("POST", "/v1/payment", json=payload)

        if data.get("status") not in ("OK", "ok") and data.get("code") not in (200, "200"):
            raise ValueError(
                f"CinetPay error [{data.get('code')}]: {data.get('status')} — {data.get('message', data)}"
            )

        return {
            "transaction_id": transaction_id,
            "notify_token": data.get("notify_token", ""),
            "payment_url": data.get("payment_url", ""),
            "simulated": False,
        }

    async def verifier_paiement(self, transaction_id: str) -> dict:
        """
        Vérifie le statut d'un paiement via GET /v1/payment/{id}.

        Retourne :
          - status   : "SUCCESS" | "FAILED" | "PENDING" | "INITIATED"
          - operator : méthode de paiement utilisée
        """
        if not settings.cinetpay_configured:
            return {"status": "SUCCESS", "operator": "SIMULATION"}

        data = await self._request("GET", f"/v1/payment/{transaction_id}")

        return {
            "status": data.get("status", "PENDING"),
            "operator": data.get("user", {}).get("phoneNumber", "") if isinstance(data.get("user"), dict) else "",
        }


cinetpay_service = CinetPayService()
