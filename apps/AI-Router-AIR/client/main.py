"""FastAPI client application serving the AIR test frontend."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from client.config import settings
import uvicorn

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)
BASE_DIR = Path(__file__).resolve().parent

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Mount Static
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.get("/")
async def client_root(request: Request):
    """Render the client-side AIR playground."""
    return templates.TemplateResponse(
        request=request,
        name="client/index.html",
        context={"request": request, "air_server_url": settings.AIR_SERVER_URL},
    )

if __name__ == "__main__":
    uvicorn.run("client.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
