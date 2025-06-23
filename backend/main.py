from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, Body
from fastapi.responses import RedirectResponse, JSONResponse
import requests
from dotenv import load_dotenv
import os, base64, time, json
from sentence_transformers import SentenceTransformer
import numpy as np
from embedding_init import model, centroids
from urllib.parse import quote_plus

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

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

    mood_vec = centroids[mood]
    matched_tracks = []

    for item in all_items:
        track = item.get("track")
        if not track:
            continue

        artist_name = track["artists"][0]["name"]
        track_name = track["name"]
        encoded_artist = quote_plus(artist_name)
        encoded_track = quote_plus(track_name)

        url = (
            f"https://ws.audioscrobbler.com/2.0/"
            f"?method=track.gettoptags"
            f"&artist={encoded_artist}"
            f"&track={encoded_track}"
            f"&api_key={os.getenv('LASTFM_API_KEY')}"
            f"&format=json"
        )

        try:
            r = requests.get(url)
            r.raise_for_status()
            tag_data = r.json().get("toptags", {}).get("tag", [])
            tags = [t["name"].lower() for t in tag_data if int(t.get("count", 0)) > 10]
            tag_string = " ".join(tags)

            if not tag_string.strip():
                continue

            tag_vec = model.encode(tag_string)
            sim = np.dot(mood_vec, tag_vec) / (np.linalg.norm(mood_vec) * np.linalg.norm(tag_vec))
            print(f"[DEBUG] Track: '{track_name}' by '{artist_name}' | Tags: {tags} | Similarity to '{mood}': {sim:.3f}")

            if sim >= 0.4:
                matched_tracks.append({
                    "name": track_name,
                    "artist": artist_name,
                    "uri": track["uri"],
                    "similarity": round(float(sim), 3)
                })

        except Exception as e:
            print(f"[WARNING] Failed to fetch tags for '{track_name}' by '{artist_name}': {e}")

        time.sleep(0.2)  # Respect API rate limits

    print(f"[INFO] {len(matched_tracks)} tracks matched the mood '{mood}' with similarity ≥ 0.4")
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
