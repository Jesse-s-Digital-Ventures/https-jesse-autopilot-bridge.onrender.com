import httpx
import logging
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from config import settings, mask_key
from sellvia_client import get_sellvia_headers

logger = logging.getLogger("app.admin")
router = APIRouter(prefix="/admin/sellvia", tags=["Admin Key Rotation"])

class KeyRotationRequest(BaseModel):
    new_api_key: str
    revoke_old_key: bool = True

def verify_admin_key(x_admin_key: str = Header(...)):
    """Verifies internal admin access header."""
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized Admin Request")

@router.post("/rotate-key", dependencies=[Depends(verify_admin_key)])
async def rotate_sellvia_key(payload: KeyRotationRequest):
    """
    Verifies candidate key against Sellvia API, promotes it to SELLVIA_API_KEY, 
    and cascades current key to SELLVIA_OLD_API_KEY.
    """
    new_key = payload.new_api_key.strip()
    if not new_key:
        raise HTTPException(status_code=400, detail="New API key cannot be empty.")

    # 1. Test validation against Sellvia endpoint
    test_url = f"{settings.SELLVIA_BASE_URL.rstrip('/')}/catalogue"
    test_headers = {
        "X-API-Key": new_key,
        "Authorization": f"Bearer {new_key}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            test_resp = await client.get(test_url, headers=test_headers)
            if test_resp.status_code not in (200, 201):
                logger.error(f"Rotation rejected: Candidate key validation returned {test_resp.status_code}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Candidate key rejected by Sellvia API (HTTP {test_resp.status_code})."
                )
    except httpx.RequestError as exc:
        logger.error(f"Network error during key validation: {str(exc)}")
        raise HTTPException(status_code=502, detail="Failed to connect to Sellvia API for validation.")

    # 2. Swap keys in application memory
    if payload.revoke_old_key:
        settings.SELLVIA_OLD_API_KEY = None
    else:
        settings.SELLVIA_OLD_API_KEY = settings.SELLVIA_API_KEY

    settings.SELLVIA_API_KEY = new_key

    logger.info(
        f"Sellvia API Key successfully rotated! "
        f"Active Key: {mask_key(settings.SELLVIA_API_KEY)} | "
        f"Fallback Key: {mask_key(settings.SELLVIA_OLD_API_KEY)}"
    )

    return {
        "status": "success",
        "message": "Sellvia master key validated and rotated successfully.",
        "active_key_preview": mask_key(settings.SELLVIA_API_KEY),
        "fallback_key_preview": mask_key(settings.SELLVIA_OLD_API_KEY)
    }
