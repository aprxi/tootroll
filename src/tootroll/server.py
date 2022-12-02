
import json
import logging
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from starlette.middleware.cors import CORSMiddleware


app = FastAPI()

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

ALLOWED_ORIGINS = "*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/alive", status_code=200)
async def alive() -> JSONResponse:
    response = {
        "message": "alive",
    }
    return JSONResponse(content=response, status_code=200)


@app.options('/{rest_of_path:path}')
async def timelines_home_options(request: Request, rest_of_path: str) -> Response:
    response = Response()
    response.headers['Access-Control-Allow-Origin'] = ALLOWED_ORIGINS
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    return response


@app.get("/api/v1/timelines/home")
async def timelines_home() -> JSONResponse:
    with open("response.dump", "rb") as stream:
        response = json.loads(stream.read())

    return JSONResponse(content=response, status_code=200)


def app_main():
    uvicorn.run(f"{__name__}:app", port=5000, log_level="info")
