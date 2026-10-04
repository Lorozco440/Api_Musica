import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException
from .routers import auth, catalog, playlists

app = FastAPI(title="MusicAPI", version="1.0.0", description="API de música: clientes, catálogo, playlists privadas y JWT. Primero registre un usuario, inicie sesión y pegue su access_token en Authorize.")


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": {"message": str(exc.detail)}}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Never echo request inputs, especially passwords, back into error responses.
    details = [{"field": ".".join(map(str, error["loc"])), "message": error["msg"]} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"error": {"message": "Datos inválidos", "details": details}})


@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception):
    logging.getLogger("musicapi").error("Unhandled error: %s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"error": {"message": "Error interno del servidor"}})


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse("/docs")


@app.get("/health", tags=["Estado"])
def health():
    return {"status": "ok"}


for router in (auth.router, catalog.router, playlists.router):
    app.include_router(router, prefix="/api/v1")
