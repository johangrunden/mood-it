from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
import requests
from dotenv import load_dotenv
import os
import base64

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

# AI-generated genre mappings for each mood
MOOD_GENRES = {
    "happy": ["pop", "dance pop", "sunshine pop", "nu-disco"],
    "sad": ["sad", "melancholia", "acoustic", "slowcore"],
    "energetic": ["edm", "electro", "trap", "hard rock", "drum and bass"],
    "chill": ["lo-fi", "chillhop", "ambient", "jazz", "downtempo"],
    "focus": ["instrumental", "piano", "classical", "ambient"]
}

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

@app.get("/all-liked-tracks")
def all_liked_tracks():
    global ACCESS_TOKEN
    if not ACCESS_TOKEN:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get("https://api.spotify.com/v1/me/tracks?limit=50", headers=headers)
    if response.status_code != 200:
        return {"error": "Failed to get liked tracks"}
    
    items = response.json().get("items", [])
    result = [{"name": t["track"]["name"], "artist": t["track"]["artists"][0]["name"]} for t in items if t["track"]]
    return result

@app.get("/mood-tracks")
def mood_tracks(mood: str):
    global ACCESS_TOKEN
    if not ACCESS_TOKEN:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get("https://api.spotify.com/v1/me/tracks?limit=50", headers=headers)

    if response.status_code != 200:
        return {"error": "Failed to get liked tracks"}

    items = response.json().get("items", [])
    mood_tracks = []

    for item in items:
        track = item.get("track")
        if not track:
            continue
        name = track["name"]
        artist_info = track["artists"][0]
        artist_id = artist_info["id"]
        artist_name = artist_info["name"]

        # Fetch artist's genres
        artist_response = requests.get(f"https://api.spotify.com/v1/artists/{artist_id}", headers=headers)
        if artist_response.status_code != 200:
            continue

        genres = artist_response.json().get("genres", [])
        match = any(
            any(mood_genre in genre for mood_genre in MOOD_GENRES.get(mood, []))
            for genre in genres
        )

        if match:
            mood_tracks.append({
                "name": name,
                "artist": artist_name,
                "genres": genres
            })

    print(f"Total matched tracks for mood '{mood}': {len(mood_tracks)}")
    return mood_tracks