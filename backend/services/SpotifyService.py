import os
import time
import requests
from typing import List, Dict
from dotenv import load_dotenv
from fastapi.responses import RedirectResponse, JSONResponse

load_dotenv()

SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_AUTH_BASE = "https://accounts.spotify.com"

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")


def get_login_redirect_url() -> RedirectResponse:
    """
    Returns a redirect response to Spotify's authorization URL.
    """
    scope = "user-library-read playlist-modify-public user-read-private"
    redirect_url = (
        f"{SPOTIFY_AUTH_BASE}/authorize"
        f"?client_id={CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scope}"
    )
    return RedirectResponse(redirect_url)


def exchange_code_and_set_cookie(code: str):
    """
    Exchanges an authorization code for an access token and sets it as a cookie.
    """
    token = exchange_code_for_token(code)
    if not token:
        return JSONResponse(status_code=400, content={"error": "Token exchange failed"})

    response = RedirectResponse(FRONTEND_URL)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="Lax",
        max_age=3600
    )
    return response


def exchange_code_for_token(code: str) -> str | None:
    """
    Exchanges an authorization code for an access token using Spotify's token endpoint.
    """
    token_url = f"{SPOTIFY_AUTH_BASE}/api/token"
    auth_header = requests.auth._basic_auth_str(CLIENT_ID, CLIENT_SECRET)
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json().get("access_token")
    print(f"[WARNING] Failed to exchange token: {response.status_code}")
    return None

def get_user_profile(token: str):
    """
    Retrieves the user's Spotify profile using the access token.
    """
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{SPOTIFY_API_BASE}/me", headers=headers)

    if response.status_code != 200:
        print(f"[ERROR] Failed to fetch user profile: {response.status_code}")
        return None

    return response.json()

def fetch_all_liked_tracks(headers: Dict[str, str]) -> List[dict]:
    """
    Retrieves all liked tracks for the user in batches of 50.
    """
    all_tracks = []
    limit = 50
    offset = 0

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

def batch_fetch_artist_genres(artist_ids: List[str], headers: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Retrieves genres for a batch of Spotify artist IDs, with retry on rate limiting.
    """
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

    return artist_genres

def create_playlist_for_user(user_id: str, mood: str, uris: List[str], headers: Dict[str, str]) -> str | None:
    """
    Creates a public playlist for the given user and adds tracks to it.
    """
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
        print(f"[WARNING] Failed to create playlist: {create_resp.status_code}")
        return None

    playlist_id = create_resp.json()["id"]
    playlist_url = create_resp.json()["external_urls"]["spotify"]

    for i in range(0, len(uris), 100):
        batch = uris[i:i + 100]
        add_resp = requests.post(
            f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks",
            headers=headers,
            json={"uris": batch}
        )
        if add_resp.status_code not in (200, 201):
            print(f"[WARNING] Failed to add tracks to playlist: {add_resp.status_code}")
            return None

    return playlist_url
