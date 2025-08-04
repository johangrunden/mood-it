# Mood It

Create Spotify playlists based on your current mood using your liked tracks.

Why?

I got so many liked songs in so many different genres and I wanted to find an easy way to only play selected songs based on my mood.
I think this already exists in some regions for Spotify but I thought it would be fun to play around with Python and Spotify's API to do this.

How?

It scans your liked songs artist-genres. The artist-genres are used to filter the songs to the desired mood with the help of Embedded Classification.

Tech:

Python, FastAPI, uvicorn, SenSentenceTransformer, Embedded Classification

Setup:
1. Install Python
2. Install dependencies: pip install -r requirements.txt
3. Add .env with FRONTEND_URL, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REDIRECT_URI
4. Run backend: uvicorn main:app --reload
