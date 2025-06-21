import json
import numpy as np
from sentence_transformers import SentenceTransformer

# Load embedding model
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Load optimized mood-to-genre mapping
with open("ai_generated_mood_genres_optimized.json", "r", encoding="utf-8") as f:
    MOOD_GENRES = json.load(f)

# Compute centroid vector per mood
centroids = {
    mood: np.mean(model.encode(genres), axis=0)
    for mood, genres in MOOD_GENRES.items()
}

# Save centroid vectors to file
np.savez("mood_centroids.npz", **centroids)

# Export objects
__all__ = ["model", "centroids"]
