# server.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import threading
from contextlib import asynccontextmanager
from pydantic import BaseModel

# Each POD will run exactly one server process.
# Kubernetes will scale replicas (pods) for you.
SERVER_ID = os.getenv("SERVER_ID", "unknown")

pipe = None
READY = False
ready_lock = threading.Lock()

class TextRequest(BaseModel):
    text: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    load model once when process starts, mark ready when a warmup call succeeds
    """
    global pipe, READY
    print(print("CORS policy: * / * / * (allow all)"))
    print("loading model")
    try:
        from transformers import pipeline

        pipe = pipeline("text-classification", model="ProsusAI/finbert")

        #warmup inference
        _ = pipe("Warmup check")
        
        with ready_lock:
            READY = True

        print("[lifespan] Model is loaded and ready")
    
    except Exception as e:
        with ready_lock:
            READY = False
        print(f"[lifespan] Model failed to load: {e}")

    yield #app runs here

    #optional shutdown cleanup
    print("[lifespan] shutting down")
    del pipe

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    #allow_origins=["https://app.vaultin.app"],
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/sentiment")
def sentiment(req: TextRequest):
    if not READY or pipe is None:
        raise HTTPException(status_code=503, detail="model is not ready")
    response = pipe(req.text)
    return {
        "server_id": SERVER_ID,
        "response": response
    }

@app.get("/readyz")
def readyz():
    #acquire lock for read
    with ready_lock:
        if READY and pipe is not None:
            return "ready"
    raise HTTPException(status_code=503, detail="model is not ready")
