from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from services.SpotifyService import fetch_all_liked_tracks, batch_fetch_artist_genres
from sentence_transformers import SentenceTransformer
from embedding_init import model, centroids
import numpy as np

router = APIRouter()

@router.get("/mood-tracks")
def mood_tracks(request: Request, mood: str):
    token = request.cookies.get("access_token")
    if not token:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    headers = {"Authorization": f"Bearer {token}"}
    liked_items = fetch_all_liked_tracks(headers)
    print(f"[INFO] Total liked tracks fetched: {len(liked_items)}")

    mood_vec = centroids[mood]
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

    artist_genre_map = batch_fetch_artist_genres(list(artist_ids), headers)

    for song in song_entries:
        genres = artist_genre_map.get(song["artist_id"], [])
        song["genres"] = genres

    for song in song_entries:
        matched, sim, source = classify_song_by_mood(song, mood_vec)
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
    token = request.cookies.get("access_token")
    if not token:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    headers = {"Authorization": f"Bearer {token}"}
    liked = fetch_all_liked_tracks(headers)

    result = [
        {
            "name": t["track"]["name"],
            "artist": t["track"]["artists"][0]["name"]
        }
        for t in liked if t.get("track")
    ]

    return result

def classify_song_by_mood(song: dict, mood_vec: np.ndarray, threshold: float = 0.6):
    """
    Classifies a single song against a mood vector using genre or fallback to <Song name> by <Artist name>.
    """
    if song["genres"]:
        text_input = " ".join(song["genres"]).lower()
        source = "genres"
    else:
        text_input = f"{song['name']} by {song['artist']}".lower()
        source = "fallback_text"

    tag_vec = model.encode(text_input)
    sim = np.dot(mood_vec, tag_vec) / (np.linalg.norm(mood_vec) * np.linalg.norm(tag_vec))

    matched = sim >= threshold
    return matched, sim, source