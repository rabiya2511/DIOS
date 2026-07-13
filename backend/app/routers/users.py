"""
Users router — currently just /me (Profile section, endpoint 1 of 8).
"""

from fastapi import APIRouter, Depends

from app.schemas.auth import UserOut
from app.core.security import get_current_user

router = APIRouter(tags=["Profile"])


@router.get("/me", response_model=UserOut)
def read_profile(current_user: dict = Depends(get_current_user)):
    return current_user