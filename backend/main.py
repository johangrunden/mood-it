from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers.Auth import router as auth_router
from routers.Playlist import router as playlist_router
from routers.Mood import router as mood_router

load_dotenv()

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

app.include_router(auth_router)
app.include_router(playlist_router)
app.include_router(mood_router)
