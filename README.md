# Mood It

Create Spotify playlists based on your current mood using your liked tracks.

Why?

I got so many liked songs in so many different genres and I wanted to find an easy way to only play selected songs based on my mood.
I think this already exists in some regions for Spotify but I thought it would be fun to play around with Python and Spotify's API to do this.

How?

It scans your liked songs artist-genres. The genres are compared with a map of the genres and ceratin moods with the help of AI. The map is currently static and not all genres are available.

Tech:

Backend: 
Python, FastAPI, uvicorn
Frontend: 
HTML and JavaScript

Setup:
1. Install Python
2. Install dependencies: pip install -r requirements.txt
3. Add .env with SPOTIFY_CLIENT_ID,SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, and LASTFM_API_KEY
4. Run backend: uvicorn main:app --reload
