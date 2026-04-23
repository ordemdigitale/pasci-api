# app/admin/config.py | Admin panel configuration
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqlmodel import select
from typing import Optional
import logging

from app.core.security import verify_password, create_access_token, verify_token
from app.models.users import User
from app.database.session import async_engine, AsyncSession

logger = logging.getLogger(__name__)


class AdminAuth(AuthenticationBackend):
    """
    Authentication backend for SQLAdmin
    Allows only superusers to access the admin panel
    """

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # Validate credentials
        async with AsyncSession(async_engine) as db:
            result = await db.execute(
                select(User).where(
                    (User.email == username) | (User.username == username)
                )
            )
            user = result.scalar_one_or_none()

            if not user or not verify_password(password, user.password):
                logger.warning(f"Failed login attempt for: {username}")
                return False

            if not user.is_superuser:
                logger.warning(f"Non-superuser attempted admin access: {username}")
                return False

            # Create session token
            token = create_access_token(data={"sub": str(user.id)})
            request.session.update({"token": token, "user_id": str(user.id)})

            logger.info(f"✅ Admin login successful: {user.email}")
            return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> Optional[RedirectResponse]:
        token = request.session.get("token")

        if not token:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        try:
            # Verify token is valid
            payload = verify_token(token, "access")
            user_id = payload.get("sub")

            if not user_id:
                return RedirectResponse(request.url_for("admin:login"), status_code=302)

            # Verify user still exists and is superuser
            async with AsyncSession(async_engine) as db:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()

                if not user or not user.is_superuser or not user.is_active:
                    return RedirectResponse(request.url_for("admin:login"), status_code=302)

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        return None


def create_admin_panel(app) -> Admin:
    """
    Create and configure the admin panel
    """
    authentication_backend = AdminAuth(secret_key="your-secret-key-here")

    admin = Admin(
        app=app,
        engine=async_engine,
        title="PASCI Admin",
        authentication_backend=authentication_backend,
        base_url="/admin"
    )

    # Register model views
    from app.admin.views import (
        UserAdmin,
        CrascAdmin,
        RegionAdmin,
        OscTypeAdmin,
        OscAdmin,
        NewsAdmin,
        JobAdmin,
        KeyStatsAdmin,
        PtfAdmin,
        ProjetAdmin,
        TeamAdmin,
        HeroAdmin,
        DocumentationAdmin,
        DonAdmin,
        VolontaireAdmin,
        DemandeAdhesionAdmin,
    )

    admin.add_view(UserAdmin)
    admin.add_view(CrascAdmin)
    admin.add_view(RegionAdmin)
    admin.add_view(OscTypeAdmin)
    admin.add_view(OscAdmin)
    admin.add_view(NewsAdmin)
    admin.add_view(JobAdmin)
    admin.add_view(KeyStatsAdmin)
    admin.add_view(PtfAdmin)
    admin.add_view(ProjetAdmin)
    admin.add_view(TeamAdmin)
    admin.add_view(HeroAdmin)
    admin.add_view(DocumentationAdmin)
    admin.add_view(DonAdmin)
    admin.add_view(VolontaireAdmin)
    admin.add_view(DemandeAdhesionAdmin)

    logger.info("✅ Admin panel configured successfully")
    return admin
