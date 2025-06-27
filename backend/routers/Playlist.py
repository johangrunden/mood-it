from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse
from services.SpotifyService import getUserProfile, createPlaylistForUser
from services.TokenService import getAuthHeadersFromRequest, getTokenFromRequest

router = APIRouter()

@router.post("/create-playlist")
def create_playlist(request: Request, payload: dict = Body(...)):

    headers = getAuthHeadersFromRequest(request)

    mood = payload.get("mood")
    uris = payload.get("uris", [])
    if not uris:
        return JSONResponse(status_code=400, content={"error": "No tracks provided"})

    user = getUserProfile(getTokenFromRequest(request))
    if not user:
        return JSONResponse(status_code=500, content={"error": "Failed to get user profile"})

    user_id = user.get("id")
    playlist_url = createPlaylistForUser(user_id, mood, uris, headers)
    if not playlist_url:
        return JSONResponse(status_code=500, content={"error": "Failed to create playlist"})

    return {
        "message": "Playlist created successfully",
        "playlist_url": playlist_url
    }
