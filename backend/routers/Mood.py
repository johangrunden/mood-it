from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from services.SpotifyService import fetchAllLikedTracks, batchFetchArtistGenres
from services.ClassificationService import classifySongByMood, getMoodVector
from services.TokenService import getAuthHeadersFromRequest
import numpy as np

router = APIRouter()

@router.get("/mood-tracks")
def mood_tracks(request: Request, mood: str):
    headers = getAuthHeadersFromRequest(request)
    
    liked_items = fetchAllLikedTracks(headers)
    print(f"[INFO] Total liked tracks fetched: {len(liked_items)}")

    mood_vec = getMoodVector(mood)
    if mood_vec is None:
        return JSONResponse(status_code=400, content={"error": f"Unknown mood: {mood}"})

    matched_tracks = []
    song_entries = []
    artist_ids = set()

    for item in liked_items:
        track = item.get("track")
        if not track:
            continue

        artist = track["artists"][0]
        entry = {
            "name": track["name"],
            "artist": artist.get("name"),
            "uri": track["uri"],
            "artist_id": artist.get("id"),
            "genres": []
        }
        song_entries.append(entry)
        if entry["artist_id"]:
            artist_ids.add(entry["artist_id"])

    artist_genre_map = batchFetchArtistGenres(list(artist_ids), headers)

    for song in song_entries:
        genres = artist_genre_map.get(song["artist_id"], [])
        song["genres"] = genres

    for song in song_entries:
        matched, sim, source = classifySongByMood(song, mood_vec)
        print(f"[DEBUG] [{source}] '{song['name']}' by '{song['artist']}' | Similarity to mood '{mood}': {sim:.3f}")
        if matched:
            matched_tracks.append({
                "name": song["name"],
                "artist": song["artist"],
                "uri": song["uri"],
                "similarity": round(float(sim), 3)
            })

    print(f"[INFO] Total matched tracks for mood '{mood}': {len(matched_tracks)}")
    return matched_tracks

@router.get("/all-liked-tracks")
def all_liked_tracks(request: Request):
    liked = fetchAllLikedTracks(getAuthHeadersFromRequest(request))

    result = [
        {
            "name": t["track"]["name"],
            "artist": t["track"]["artists"][0]["name"]
        }
        for t in liked if t.get("track")
    ]

    return result