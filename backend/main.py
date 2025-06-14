# main.py - Entry point for FastAPI backend

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Mood It backend is running"}
