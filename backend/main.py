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
    "happy": [
        "pop", "dance pop", "sunshine pop", "nu-disco", "disco", "disco house", "funky house", "funk rock",
        "freestyle", "future bass", "latin", "latin house", "latin indie", "italo disco", "italo dance",
        "kizomba", "reggaeton", "tropical house", "afrobeats", "afrobeat", "alté", "afro r&b", "afro soul",
        "christmas", "classic soul", "motown", "retro soul", "quiet storm", "bossa nova", "comedy"
    ],
    "sad": [
        "sad", "melancholia", "acoustic", "slowcore", "emo", "neo-psychedelic", "shoegaze",
        "indie soul", "neo soul", "indie r&b", "contemporary r&b", "minimalism", "new age",
        "italian singer-songwriter", "mexican indie", "varieté française"
    ],
    "energetic": [
        "edm", "electro", "trap", "hard rock", "drum and bass", "acid house", "bass house", "big beat",
        "big room", "breakbeat", "gabber", "g-house", "g-funk", "gangster rap", "hard house",
        "hi-nrg", "house", "metal", "nu metal", "post-punk", "punk", "rap metal", "southern hip hop",
        "tech house", "trance", "progressive trance", "tribal house", "uk garage", "jungle", "breakcore"
    ],
    "chill": [
        "lo-fi", "chillhop", "ambient", "jazz", "downtempo", "chillwave", "chillstep", "new wave",
        "trip hop", "vaporwave", "lounge", "space rock", "idm", "minimal techno", "dub techno",
        "math rock", "melodic house", "quiet storm", "new jack swing", "alté"
    ],
    "focus": [
        "instrumental", "piano", "classical", "ambient", "minimalism", "new age", "melodic house",
        "lo-fi", "idm", "lounge", "post-rock", "space rock", "minimal techno", "math rock",
        "chillhop", "new wave"
    ]
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

def fetch_all_liked_tracks(headers):
    all_tracks = []
    limit = 50
    offset = 0

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
    all_tracks = fetch_all_liked_tracks(headers)

    mood_tracks = []

    for item in all_tracks:
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

