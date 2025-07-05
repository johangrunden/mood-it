from fastapi import APIRouter, Request
from services.TokenService import getAuthHeadersFromRequest
from services.MoodService import getTracksByMood, getAllLikedTracks

router = APIRouter()

@router.get("/mood-tracks")
def mood_tracks(request: Request, mood: str):
    headers = getAuthHeadersFromRequest(request)
    return getTracksByMood(headers, mood)

@router.get("/all-liked-tracks")
def all_liked_tracks(request: Request):
    headers = getAuthHeadersFromRequest(request)
    return getAllLikedTracks(headers)
