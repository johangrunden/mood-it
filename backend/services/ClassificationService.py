import numpy as np
from embedding_init import model, centroids

def classifySongByMood(song: dict, mood_vec: np.ndarray, threshold: float = 0.6):
    """
    Classifies a single song against a mood vector using genres or fallback text.
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

def getMoodVector(mood: str) -> np.ndarray | None:
    return centroids.get(mood)
