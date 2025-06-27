from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from services.SpotifyService import getLoginRedirectUrl, exchangeCodeAndSetCookie, getUserProfile

router = APIRouter()

@router.get("/login")
def login():
    return getLoginRedirectUrl()

@router.get("/callback")
def callback(code: str):
    return exchangeCodeAndSetCookie(code)

@router.get("/me")
def get_me(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    user = getUserProfile(token)
    if not user:
        return JSONResponse(status_code=500, content={"error": "Failed to get user profile"})

    return {"display_name": user.get("display_name")}
