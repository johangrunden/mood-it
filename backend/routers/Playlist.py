from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse
from services.SpotifyService import getUserProfile, createPlaylistForUser

router = APIRouter()

@router.post("/create-playlist")
def create_playlist(request: Request, payload: dict = Body(...)):
    token = request.cookies.get("access_token")
    if not token:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    mood = payload.get("mood")
    uris = payload.get("uris", [])
    if not uris:
        return JSONResponse(status_code=400, content={"error": "No tracks provided"})

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    user = getUserProfile(token)
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
