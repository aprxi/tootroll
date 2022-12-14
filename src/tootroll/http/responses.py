import os
import re
import json
import mmap

from fastapi.responses import Response, HTMLResponse

from typing import Dict, List, Tuple, Optional, Any

from ..vars import DATABASE_DIR

HTML_DIR = f"{os.path.dirname(__file__)}/html"


def json_response(content: Dict[str, Any], status_code: int = 200) -> Response:
    return Response(
        content=json.dumps(content),
        media_type="application/json",
        status_code=status_code,
    )


def empty_response(status_code: int) -> Response:
    return Response(content=b"", status_code=status_code)


def validate_http_request_range(input_range: str, filesize: int) -> Tuple[int, int]:

    if not re.match("[0-9]{1,}-[0-9]{0,}$|^[0-9]{0,}-[0-9]{1,}$", input_range):
        raise ValueError(f"invalid range: {input_range}")

    r_start_str, r_end_str = input_range.split("-")
    if not r_start_str:
        # e.g. -10, get last 10 bytes)
        r_start = filesize - int(r_end_str)
        r_end = filesize - 1
    elif not r_end_str:
        # e.g. 10-, start at byte #10
        r_start = int(r_start_str)
        r_end = filesize - 1
    else:
        r_start = int(r_start_str)
        r_end = int(r_end_str)

    if r_start < 0 or r_start >= filesize:
        raise ValueError(f"invalid range, {input_range} (filesize={filesize}")

    return int(r_start), int(r_end)


def path_url_to_file(url_path: str) -> Tuple[str, str]:
    if re.match("^db/.*/.*\\.parquet/.*/.*\\.parquet", url_path):
        file_path = f'{DATABASE_DIR}/{url_path.split("db/", 1)[-1]}'
        content_type = "application/octet-stream"
    else:
        file_path = f"{HTML_DIR}/{url_path}"
        if file_path[-1] == "/":
            file_path += "index.html"
        content_type = "text/html"
    return file_path, content_type


def static_file_head_response(
    url_path: str, range_request: Optional[str] = None
) -> Response:
    file_path, content_type = path_url_to_file(url_path)

    if not os.path.exists(file_path):
        return empty_response(404)

    file_info = os.stat(file_path)
    if not range_request:
        headers = {
            "Content-Type": content_type,
            "Content-Length": str(file_info.st_size),
            "Accept-Ranges": "bytes",
        }
        return Response(content=b"", headers=headers, status_code=200)
    # else:
    try:
        ranges = parse_range_request(range_request, file_info.st_size)
    except ValueError as error:
        return Response(content=str(error), status_code=400)

    headers = {
        "Content-Type": content_type,
        "Content-Length": str(file_info.st_size),
        "Accept-Ranges": "bytes",
        "Content-Range": f"{range_request}/{file_info.st_size}",
    }
    return Response(content=b"", headers=headers, status_code=206)


def parse_range_request(range_request: str, file_size: int) -> List[Tuple[int, int]]:
    range_type, ranges_str = range_request.strip(" ").split("=")
    if range_type.lower() != "bytes":
        raise ValueError("Only support ranges of bytes")

    return [
        validate_http_request_range(input_range, file_size)
        for input_range in list([r.strip(" ") for r in ranges_str.split(",")])
    ]


def static_file_get_response(
    url_path: str, range_request: Optional[str] = None
) -> HTMLResponse:

    file_path, content_type = path_url_to_file(url_path)
    if not os.path.exists(file_path):
        return empty_response(404)

    if not range_request:
        with open(file_path, "rb") as ifile:
            content = ifile.read()
        return HTMLResponse(content=content, status_code=200)
    # else:
    file_info = os.stat(file_path)

    try:
        ranges = parse_range_request(range_request, file_info.st_size)
    except ValueError as error:
        return Response(content=str(error), status_code=400)

    content = b""
    with open(file_path, "r+b") as f:
        # map whole file
        mm = mmap.mmap(f.fileno(), 0)

        for r_start, r_end in ranges:
            mm.seek(int(r_start))
            content = mm.read(int(r_end) - int(r_start) + 1)

            # TODO: # parse multiple ranges
            # (Content-Type: multipart/byteranges; boundary=String_separator)
            break

        mm.close()

    headers = {
        "Content-Range": f"{range_request}/{file_info.st_size}",
        "Content-Type": content_type,
        "Content-Length": str(len(content)),
    }
    return Response(content=content, headers=headers, status_code=206)
