"""Permission checks. Identity and permissions come from mango-auth; nothing is stored here."""

import logging

from fastapi import Depends, HTTPException, Request

from lime_warehouse.shared.errors import Forbidden, Unauthorized
from lime_warehouse.shared.mango_auth_client import MangoAuthClient, Principal

logger = logging.getLogger("lime_warehouse.auth")

__all__ = ["MangoAuthClient", "Principal", "require"]


def require(*permissions: str):
    """Dependency that needs a valid mango-auth token holding every listed permission.

    The client lives on `app.state.auth`, so tests can swap it without touching the routers.
    """

    async def dependency(request: Request) -> Principal:
        try:
            user = await request.app.state.auth.current_user(request)
        except HTTPException as exc:
            raise Unauthorized(str(exc.detail)) from exc
        missing = [p for p in permissions if not user.has(p)]
        if missing:
            logger.warning(
                "permission denied",
                extra={"event": "auth_failure", "actor_id": user.sub, "missing": missing},
            )
            raise Forbidden(f"Missing permission: {', '.join(missing)}")
        return user

    return Depends(dependency)
