import os, base64, time, json, requests
import numpy as np
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, Body
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from embedding_init import model, centroids

load_dotenv()

SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_AUTH_BASE = "https://accounts.spotify.com"

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Mood It backend is running"}

@app.get("/login")
def login():
    scope = "user-library-read playlist-modify-public user-read-private"
    redirect_url = (
    f"{SPOTIFY_AUTH_BASE}/authorize"
    f"?client_id={CLIENT_ID}"
    "&response_type=code"
    f"&redirect_uri={REDIRECT_URI}"
    f"&scope={scope}"
    )
    return RedirectResponse(redirect_url)

@app.get("/callback")
def callback(code: str):
    global ACCESS_TOKEN
    token_url = f"{SPOTIFY_AUTH_BASE}/api/token"
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    response = requests.post(token_url, headers=headers, data=data)
    token_data = response.json()
    ACCESS_TOKEN = token_data.get("access_token", "")
    return RedirectResponse(FRONTEND_URL)

def fetch_all_liked_tracks(headers):
    all_tracks = []
    limit = 50
    offset = 0

    # Max-limit is 50 so fetch in batches
    while True:
        url = f"{SPOTIFY_API_BASE}/me/tracks?limit={limit}&offset={offset}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            break

        items = response.json().get("items", [])
        all_tracks.extend(items)

        if len(items) < limit:
            break

        offset += limit

    return all_tracks

@app.get("/all-liked-tracks")
def all_liked_tracks():
    global ACCESS_TOKEN
    if not ACCESS_TOKEN:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    all_items = fetch_all_liked_tracks(headers)

    result = [
        {
            "name": t["track"]["name"],
            "artist": t["track"]["artists"][0]["name"]
        }
        for t in all_items if t.get("track")
    ]

    return result

def batch_fetch_artist_genres(artist_ids, headers):
    artist_genres = {}
    for i in range(0, len(artist_ids), 50):
        batch = artist_ids[i:i + 50]
        ids_param = ",".join(batch)
        url = f"{SPOTIFY_API_BASE}/artists?ids={ids_param}"

        while True:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 1))
                print(f"[WARNING] Rate limit hit. Retrying after {retry_after} seconds...")
                time.sleep(retry_after + 0.5)
                continue
            elif resp.status_code == 200:
                artists = resp.json().get("artists", [])
                for artist in artists:
                    artist_genres[artist["id"]] = artist.get("genres", [])
                print(f"[INFO] Fetched genres for artist batch {i}-{i + len(batch) - 1}")
            else:
                print(f"[WARNING] Failed to fetch artist batch {i}-{i + len(batch) - 1}: {resp.status_code}")
            break

        time.sleep(0.1)

    return artist_genres

def classify_song_by_mood(song: dict, mood_vec: np.ndarray, threshold: float = 0.6):
    """
    Classifies a single song against a mood vector using genre or fallback <Song name> by <Artist name>.
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


@app.get("/mood-tracks")
def mood_tracks(mood: str):
    global ACCESS_TOKEN
    if not ACCESS_TOKEN:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    liked_items = fetch_all_liked_tracks(headers)
    print(f"[INFO] Total liked tracks fetched: {len(liked_items)}")

    mood_vec = centroids[mood]
    matched_tracks = []
    song_entries = []
    artist_ids = set()

    # Step 1–2: Build list of liked songs and collect artist IDs
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

        # Only add valid artist IDs (skip if None or missing) to avoid API errors
        if entry["artist_id"]:
            artist_ids.add(entry["artist_id"])

    # Step 3: Batch fetch genres for all unique artists
    artist_genre_map = batch_fetch_artist_genres(list(artist_ids), headers)

    # Step 4: Assign genres to each song
    for song in song_entries:
        genres = artist_genre_map.get(song["artist_id"], [])
        song["genres"] = genres

    # Step 5: Classify all songs (use fallback text if no genres found)
    for song in song_entries:
        matched, sim, source = classify_song_by_mood(song, mood_vec)

        print(f"[DEBUG] [{source}] Track: '{song['name']}' by '{song['artist']}' | Similarity to mood '{mood}': {sim:.3f}")

        if matched:
            matched_tracks.append({
                "name": song["name"],
                "artist": song["artist"],
                "uri": song["uri"],
                "similarity": round(float(sim), 3)
            })

    print(f"[INFO] Total matched tracks for mood '{mood}': {len(matched_tracks)}")
    return matched_tracks

@app.post("/create-playlist")
def create_playlist(payload: dict = Body(...)):
    global ACCESS_TOKEN
    if not ACCESS_TOKEN:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    # Extract mood and track URIs from request body
    mood = payload.get("mood")
    uris = payload.get("uris", [])
    if not uris:
        return JSONResponse(status_code=400, content={"error": "No tracks provided"})

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Fetch current user's Spotify ID
    profile_resp = requests.get(f"{SPOTIFY_API_BASE}/me", headers=headers)
    if profile_resp.status_code != 200:
        return JSONResponse(status_code=profile_resp.status_code,
                            content={"error": "Failed to fetch user profile"})
    user_id = profile_resp.json()["id"]

    # Create a new playlist named “Mood It – {Mood}”
    playlist_body = {
        "name": f"Mood It – {mood.capitalize()}",
        "description": f"Automatically generated playlist for mood: {mood}",
        "public": True
    }
    create_resp = requests.post(
        f"{SPOTIFY_API_BASE}/users/{user_id}/playlists",
        headers=headers,
        json=playlist_body
    )
    if create_resp.status_code != 201:
        return JSONResponse(status_code=create_resp.status_code,
                            content={"error": "Failed to create playlist"})

    playlist_id = create_resp.json()["id"]
    playlist_url = create_resp.json()["external_urls"]["spotify"]

    # Add tracks to the new playlist in batches of 100 (limit)
    for i in range(0, len(uris), 100):
        batch = uris[i:i + 100]
        add_resp = requests.post(
            f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks",
            headers=headers,
            json={"uris": batch}
        )
        if add_resp.status_code not in (200, 201):
            return JSONResponse(status_code=add_resp.status_code,
                                content={"error": "Failed to add tracks"})

    # Return success message and playlist URL
    return {
        "message": "Playlist created successfully",
        "playlist_url": playlist_url
    }
