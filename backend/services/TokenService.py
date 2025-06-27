from fastapi import Request, Response
from fastapi.responses import JSONResponse

def getTokenFromRequest(request: Request) -> str | None:
    return request.cookies.get("access_token")

def requireTokenOrUnauthorized(request: Request) -> str | JSONResponse:
    token = getTokenFromRequest(request)
    if not token:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    return token

def setTokenCookie(response: Response, token: str):
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="Lax",
        max_age=3600
    )

def getAuthHeaders(token: str) -> dict:
    return {"Authorization": f"Bearer {token}",
            "Content-Type": "application/json"}

def getAuthHeadersFromRequest(request: Request) -> dict | JSONResponse:
    """
    Returns headers or 401 response if token is missing in request cookies.
    """
    tokenOrResponse = requireTokenOrUnauthorized(request)
    if isinstance(tokenOrResponse, JSONResponse):
        return tokenOrResponse
    return getAuthHeaders(tokenOrResponse)