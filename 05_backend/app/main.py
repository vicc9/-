from fastapi import FastAPI
from app.api.routers import songs,users

app = FastAPI()

app.include_router(songs.router)
app.include_router(users.router)

@app.get("/")
async def root():
    return {"message": "Hello Music Recomendation System!"}