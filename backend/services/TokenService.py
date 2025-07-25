from fastapi import Request, Response
from fastapi.responses import JSONResponse

def getTokenFromRequest(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
       return auth_header[7:]
    else:
       return JSONResponse(status_code=401, content={"error": "Not authenticated"})

def requireTokenOrUnauthorized(request: Request) -> str | JSONResponse:
    token = getTokenFromRequest(request)
    if not token:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    return token

def setTokenCookie(response: Response, token: str) -> Response:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True, # Set to True in production
        samesite="None",
        max_age=3600
    )
    return response

def getAuthHeaders(token: str) -> dict:
    return {"Authorization": f"Bearer {token}",
            "Content-Type": "application/json"}

def getAuthHeadersFromRequest(request: Request) -> dict | JSONResponse:
    tokenOrResponse = requireTokenOrUnauthorized(request)
    if isinstance(tokenOrResponse, JSONResponse):
        return tokenOrResponse
    return getAuthHeaders(tokenOrResponse)
