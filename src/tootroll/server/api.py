import os
import re
import json
import logging

import uvicorn
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import Response
from starlette.middleware.cors import CORSMiddleware

from typing import Dict, Optional, Any

from ..db.utils import list_by_partition

from ..vars import DATABASE_DIR

APP_PREFIX = "/api/v1"
ALLOWED_ORIGINS = "*"


logger = logging.getLogger(__name__)


router = APIRouter(prefix=APP_PREFIX)


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


@router.get("/alive", status_code=200)
async def alive() -> Response:
    response = {
        "message": "alive",
    }
    return json_response(response)


@router.get("/servers")
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


@router.get("/servers/{server}")
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


@router.get("/servers/{server}/{database}")
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


@router.get("/servers/{server}/{database}/files")
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

    response = {"Files": partition_values}

    return json_response(response)


@router.options('/{rest_of_path:path}')
async def timelines_home_options(request: Request, rest_of_path: str) -> Response:
    response = Response()
    response.headers['Access-Control-Allow-Origin'] = ALLOWED_ORIGINS
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    return response



def app_main():
    app = FastAPI(
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    uvicorn.run(app=app, port=5000, log_level="info")
