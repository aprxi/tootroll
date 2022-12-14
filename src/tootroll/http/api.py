import os
import re
import logging

import uvicorn
from fastapi import APIRouter, FastAPI, WebSocket, Request
from fastapi.responses import Response, HTMLResponse
from starlette.middleware.cors import CORSMiddleware

from typing import Optional

from .responses import (
    json_response,
    empty_response,
    static_file_head_response,
    static_file_get_response,
)
from ..db.utils import list_by_partition
from ..vars import DATABASE_DIR


API_PREFIX = "/api/v1"
ALLOWED_ORIGINS = "*"


logger = logging.getLogger(__name__)


app = FastAPI(
    docs_url="/docs",
    redoc_url="/redoc",
)

api = APIRouter(prefix=API_PREFIX)
static = APIRouter(prefix="")


@api.get("/alive", status_code=200)
async def alive() -> Response:
    response = {
        "message": "alive",
    }
    return json_response(response)


@api.get("/servers")
async def list_servers() -> Response:
    """List available servers to client"""
    response = {"Servers": []}

    try:
        response["Servers"] = os.listdir(DATABASE_DIR)
    except NotADirectoryError:
        # log as warning on server only -- for client this is not an error
        logger.warning(f"DATABASE_DIR '{DATABASE_DIR}' not a directory")
    except FileNotFoundError:
        # log as warning on server only -- for client this is not an error
        logger.warning(f"DATABASE_DIR '{DATABASE_DIR}' does not exist")

    return json_response(response, status_code=200)


@api.get("/servers/{server}")
async def list_server_databases(server: str) -> Response:
    """list all (multi-file) .parquet files for the given server"""
    response = {"Databases": []}

    try:
        directory = f"{DATABASE_DIR}/{server}"
        response["Databases"] = list(
            [
                fname
                for fname in os.listdir(directory)
                if re.match(".*\\.parquet$", fname)
                and os.path.isdir(f"{directory}/{fname}")
            ]
        )
        return json_response(response)
    except NotADirectoryError:
        return empty_response(404)
    except FileNotFoundError:
        return empty_response(404)


@api.get("/servers/{server}/{database}")
async def list_database_partitions(server: str, database: str) -> Response:

    response = {"Partitions": []}

    try:
        directory = f"{DATABASE_DIR}/{server}/{database}"
        response["Partitions"] = list(
            [
                fname
                for fname in os.listdir(directory)
                if re.match("^\w*=\w*$", fname)
                and os.path.isdir(f"{directory}/{fname}")
            ]
        )
        return json_response(response)
    except NotADirectoryError:
        return empty_response(404)
    except FileNotFoundError:
        return empty_response(404)


@api.get("/servers/{server}/{database}/files")
async def list_partition_files(
    server: str,
    database: str,
    partition_key: Optional[str] = None,
    partition_values: Optional[str] = None,
) -> Response:

    if partition_key:
        if partition_values:
            partition_values_filter = set(filter(None, partition_values.split(",")))
        else:
            partition_values_filter = None

        partition_values = list_by_partition(
            server,
            database,
            partition_key,
            partition_values_filter=partition_values_filter,
        )
    else:
        # not yet implemented
        return empty_response(400)

    response = {
        "Path": f"http://localhost:5000/db/{server}/{database}",
        "Files": partition_values,
    }

    return json_response(response)


@api.options("/{rest_of_path:path}")
async def timelines_home_options(request: Request, rest_of_path: str) -> Response:
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGINS
    response.headers[
        "Access-Control-Allow-Methods"
    ] = "POST, GET, DELETE, OPTIONS, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    return response


ws_html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:5000/");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@static.get("/demo")
async def demo():
    return HTMLResponse(ws_html)


@static.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        print("Received text", data)
        await websocket.send_text(f"Message text was: {data}")


# catch any other file in non-API_PREFIX path
@static.head("/{url_path:path}", response_class=HTMLResponse)
async def static_file_head(url_path: str, request: Request) -> HTMLResponse:
    # print( json.dumps(request.headers, indent=4, default=str))
    return static_file_head_response(
        url_path, range_request=request.headers.get("Range", None)
    )


@static.get("/{url_path:path}", response_class=HTMLResponse)
async def static_file_get(url_path: str, request: Request) -> HTMLResponse:
    # print( json.dumps(request.headers, indent=4, default=str))
    return static_file_get_response(
        url_path, range_request=request.headers.get("Range", None)
    )


def app_main():
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api)
    app.include_router(static)
    uvicorn.run(app=app, host="0.0.0.0", port=5000, log_level="info")
