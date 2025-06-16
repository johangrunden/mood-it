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
    track_ids = [item["track"]["id"] for item in items if item["track"]]

    # Get audio features for all songs
    features = []
    for i in range(0, len(track_ids), 50):
        batch = track_ids[i:i+50]
        response = requests.get(
            "https://api.spotify.com/v1/audio-features?ids=" + ",".join(batch),
            headers=headers
        )
        if response.status_code == 200:
            batch_features = response.json().get("audio_features", [])
            features.extend(batch_features)
        else:
            print("Error:", response.status_code, response.text)

    # Filter songs
    def mood_filter(f):
        if not f:
            return False
        if mood == "happy":
            return f["valence"] > 0.5 and f["energy"] > 0.4 and f["danceability"] > 0.4
        elif mood == "sad":
            return f["valence"] < 0.5 and f["energy"] < 0.6
        elif mood == "focus":
            return f["instrumentalness"] > 0.3 and f["energy"] < 0.6
        elif mood == "energetic":
            return f["energy"] > 0.6 and f["danceability"] > 0.5 and f["tempo"] > 100
        elif mood == "chill":
            return (
                f["energy"] < 0.6 and
                f["tempo"] < 115 and
                f["valence"] < 0.65 and
                (f["acousticness"] > 0.2 or f["instrumentalness"] > 0.1)
            )
        return True

    selected_ids = [f["id"] for f in features if mood_filter(f)]

    selected_tracks = [t for t in items if t["track"]["id"] in selected_ids]

    result = [{"name": t["track"]["name"], "artist": t["track"]["artists"][0]["name"]} for t in selected_tracks]
    return result
