import os
import re
import json
import logging

import uvicorn
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import Response, HTMLResponse
from starlette.middleware.cors import CORSMiddleware

from typing import Dict, Optional, Any

from ..db.utils import list_by_partition

from ..vars import DATABASE_DIR

HTML_DIR = f"{os.path.dirname(__file__)}/html"

API_PREFIX = "/api/v1"
ALLOWED_ORIGINS = "*"


logger = logging.getLogger(__name__)


app = FastAPI(
    docs_url="/docs",
    redoc_url="/redoc",
)

api = APIRouter(prefix=API_PREFIX)
static = APIRouter(prefix="")


def json_response(content: Dict[str, Any], status_code=200) -> Response:
    return Response(
        content=json.dumps(content),
        media_type="application/json",
        status_code=status_code
    )


def empty_response(status_code: int) -> Response:
    return Response(
        content=b"",
        status_code=status_code
    )


def static_file_response(file_path: str, range_request: Optional[str] = None) -> HTMLResponse:
    if not os.path.exists(file_path):
        return empty_response(404)

    if not range_request:
        with open(file_path, "rb") as ifile:
            content = ifile.read()
        return HTMLResponse(content=content, status_code=200)
    else:
        file_info = os.stat(file_path)
        range_type, ranges_str = range_request.strip(" ").split("=")
        # TODOs: 
        # accept formats like 100-, -100
        # validate if range is within file-size
        # give a proper error if range_type != bytes
        # give a proper error if range is malformed or un-supported
        # accept multiple ranges (Content-Type: multipart/byteranges; boundary=String_separator)
        assert range_type == "bytes"
        ranges = list([r.strip(" ") for r in ranges_str.split(",")])
        for range in ranges:
            r_start, r_end = range.split("-")
            assert r_start != ""
            assert r_end != ""

        fo = open(file_path, "rb")
        fo.seek(int(r_start))
        content = fo.read(int(r_end) - int(r_start) + 1)
        fo.close()

        headers = {
            "Content-Range": f"bytes {range_request}/{file_info.st_size}",
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(content)),
        }
        return Response(content=content, headers=headers, status_code=206)


@api.get("/alive", status_code=200)
async def alive() -> Response:
    response = {
        "message": "alive",
    }
    return json_response(response)


@api.get("/servers")
async def list_servers() -> Response:
    response = {"Servers": []}

    try:
        response["Servers"] = os.listdir(DATABASE_DIR)
        return json_response(response)
    except NotADirectoryError:
        logger.error(f"DATABASE_DIR '{DATABASE_DIR}' not a directory")
        return empty_response(500)
    except FileNotFoundError:
        logger.error(f"DATABASE_DIR '{DATABASE_DIR}' does not exist")
        return empty_response(500)


@api.get("/servers/{server}")
async def list_server_databases(server: str) -> Response:
    """list all (multi-file) .parquet files for the given server"""
    response = {"Databases": []}

    try:
        directory = f"{DATABASE_DIR}/{server}"
        response["Databases"] =  list([
            fname for fname in
            os.listdir(directory)
            if re.match(".*\.parquet$", fname)
            and os.path.isdir(f"{directory}/{fname}")
        ])
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
        response["Partitions"] =  list([
            fname for fname in
            os.listdir(directory)
            if re.match("^\w*=\w*$", fname)
            and os.path.isdir(f"{directory}/{fname}")
        ])
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
    partition_values: Optional[str] = None
) -> Response:

    if partition_key:
        if partition_values:
            partition_values_filter = set(filter(None, partition_values.split(",")))
        else:
            partition_values_filter = None

        partition_values = \
            list_by_partition(
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
        "Files": partition_values
    }

    return json_response(response)


@api.options('/{rest_of_path:path}')
async def timelines_home_options(request: Request, rest_of_path: str) -> Response:
    response = Response()
    response.headers['Access-Control-Allow-Origin'] = ALLOWED_ORIGINS
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    return response


# catch any other file in non-API_PREFIX path
@static.get("/{url_path:path}", response_class=HTMLResponse)
async def static_file(url_path: str, request: Request) -> HTMLResponse:

    if re.match("^db/.*/.*\.parquet/.*/.*\.parquet", url_path):
        file_path = f'{DATABASE_DIR}/{url_path.split("db/", 1)[-1]}'
    else:
        file_path = f"{HTML_DIR}/{url_path}"
        if file_path[-1] == "/":
            file_path += "index.html"
    return static_file_response(file_path, range_request=request.headers.get("Range", None))


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
    uvicorn.run(app=app, port=5000, log_level="info")
