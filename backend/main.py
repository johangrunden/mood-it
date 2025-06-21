from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, Body
from fastapi.responses import RedirectResponse, JSONResponse
import requests
from dotenv import load_dotenv
import os, base64, time, json
from sentence_transformers import SentenceTransformer
import numpy as np
from embedding_init import model, centroids

load_dotenv()

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
        "https://accounts.spotify.com/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scope}"
    )
    return RedirectResponse(redirect_url)

@app.get("/callback")
def callback(code: str):
    global ACCESS_TOKEN
    token_url = "https://accounts.spotify.com/api/token"
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
        url = f"https://api.spotify.com/v1/me/tracks?limit={limit}&offset={offset}"
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

@app.get("/mood-tracks")
def mood_tracks(mood: str):
    global ACCESS_TOKEN
    if not ACCESS_TOKEN:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    all_items = fetch_all_liked_tracks(headers)
    print(f"[INFO] Total liked tracks fetched: {len(all_items)}")

    artist_ids = {
        item["track"]["artists"][0]["id"]
        for item in all_items
        if item.get("track")
    }
    print(f"[INFO] Unique artist IDs found: {len(artist_ids)}")

    # Fetch artist genres
    artist_genre_map = {}
    artist_id_list = list(artist_ids)
    for i in range(0, len(artist_id_list), 50):
        batch = artist_id_list[i:i + 50]
        print(f"[INFO] Fetching genres for artist batch {i // 50 + 1} ({len(batch)} artists)")
        while True:
            r = requests.get(
                "https://api.spotify.com/v1/artists",
                params={"ids": ",".join(batch)},
                headers=headers
            )
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", 5))
                print(f"[WARNING] Rate limited. Retrying in {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            try:
                r.raise_for_status()
                for artist in r.json().get("artists", []):
                    genres = artist.get("genres", [])
                    artist_genre_map[artist["id"]] = genres
                    print(f"[DEBUG] Artist: {artist['name']} | Genres: {genres}")
                break
            except requests.exceptions.HTTPError as e:
                print(f"[ERROR] Failed to fetch artist batch {i // 50 + 1}: {e}")
                break

    # Classification time, calculate cosine similarity with the specific mood-centroid
    mood_vec = centroids[mood]
    matched_tracks = []
    for item in all_items:
        track = item.get("track")
        if not track:
            continue

        artist = track["artists"][0]
        artist_genres = artist_genre_map.get(artist["id"], [])
        if not artist_genres:
            continue

        genre_string = " ".join(artist_genres)
        genre_vec = model.encode(genre_string)
        sim = np.dot(mood_vec, genre_vec) / (np.linalg.norm(mood_vec) * np.linalg.norm(genre_vec))
        print(f"[DEBUG] Track: {track['name']} | Artist: {artist['name']} | Similarity to '{mood}': {sim:.3f}")

        if sim >= 0.55:  # Adjust threshold if needed
            matched_tracks.append({
                "name": track["name"],
                "artist": artist["name"],
                "uri": track["uri"],
                "similarity": round(float(sim), 3)
            })

    print(f"[INFO] {len(matched_tracks)} tracks matched the mood '{mood}' with similarity ≥ 0.6")
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
    profile_resp = requests.get("https://api.spotify.com/v1/me", headers=headers)
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
        f"https://api.spotify.com/v1/users/{user_id}/playlists",
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
            f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
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
