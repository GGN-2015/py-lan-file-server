from __future__ import annotations

import base64
import email.utils
import hashlib
import json
import mimetypes
import os
import posixpath
import re
import socket
import struct
import threading
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

TEMP_DIR_NAME = ".uploads"
DOWNLOAD_COPY_BLOCK_SIZE = 1024 * 1024
UPLOAD_COPY_BLOCK_SIZE = 1024 * 1024
WINDOWS_UNSAFE_CHARS = set('<>:"/\\|?*')
_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")
_upload_locks: dict[str, threading.Lock] = {}
_upload_locks_guard = threading.Lock()
WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class RangeNotSatisfiable(ValueError):
    pass


class BadRequest(ValueError):
    pass


class UploadCancelled(ConnectionError):
    pass


class WebSocketClient:
    def __init__(self, writer) -> None:
        self.writer = writer
        self.lock = threading.Lock()

    def send_json(self, value: dict[str, Any]) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        with self.lock:
            self.write_frame(0x1, payload)

    def send_pong(self, payload: bytes) -> None:
        with self.lock:
            self.write_frame(0xA, payload)

    def write_frame(self, opcode: int, payload: bytes) -> None:
        length = len(payload)
        header = bytearray([0x80 | opcode])
        if length < 126:
            header.append(length)
        elif length <= 0xFFFF:
            header.append(126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(127)
            header.extend(struct.pack("!Q", length))
        self.writer.write(header)
        self.writer.write(payload)
        self.writer.flush()


class WebSocketHub:
    def __init__(self) -> None:
        self._clients: set[WebSocketClient] = set()
        self._lock = threading.Lock()

    def add(self, client: WebSocketClient) -> None:
        with self._lock:
            self._clients.add(client)

    def remove(self, client: WebSocketClient) -> None:
        with self._lock:
            self._clients.discard(client)

    def broadcast_json(self, value: dict[str, Any]) -> None:
        with self._lock:
            clients = list(self._clients)

        broken = []
        for client in clients:
            try:
                client.send_json(value)
            except OSError:
                broken.append(client)

        if broken:
            with self._lock:
                for client in broken:
                    self._clients.discard(client)


class UploadRegistry:
    def __init__(self, hub: WebSocketHub) -> None:
        self._hub = hub
        self._uploads: dict[str, dict[str, Any]] = {}
        self._cancelled: set[str] = set()
        self._lock = threading.Lock()

    def begin(self, upload_id: str, name: str, size: int, modified: str, client_id: str, offset: int) -> None:
        now = time.time()
        with self._lock:
            self._cancelled.discard(upload_id)
            existing = self._uploads.get(upload_id)
            started_at = existing["startedAt"] if existing else now
            self._uploads[upload_id] = {
                "id": upload_id,
                "name": name,
                "size": size,
                "modified": modified,
                "clientId": client_id,
                "offset": offset,
                "startedAt": started_at,
                "updatedAt": now,
            }
        self.broadcast()

    def progress(self, upload_id: str, offset: int) -> None:
        with self._lock:
            upload = self._uploads.get(upload_id)
            if not upload:
                return
            upload["offset"] = offset
            upload["updatedAt"] = time.time()
        self.broadcast()

    def finish(self, upload_id: str) -> None:
        with self._lock:
            self._uploads.pop(upload_id, None)
            self._cancelled.discard(upload_id)
        self.broadcast()

    def disconnect(self, upload_id: str) -> None:
        with self._lock:
            self._uploads.pop(upload_id, None)
        self.broadcast()

    def client_disconnected(self, client_id: str) -> None:
        with self._lock:
            removed = [
                upload_id
                for upload_id, upload in self._uploads.items()
                if upload.get("clientId") == client_id
            ]
            for upload_id in removed:
                self._uploads.pop(upload_id, None)
        if removed:
            self.broadcast()

    def request_cancel(self, upload_id: str) -> None:
        with self._lock:
            self._cancelled.add(upload_id)
            self._uploads.pop(upload_id, None)
        self.broadcast()

    def cancel_complete(self, upload_id: str) -> None:
        with self._lock:
            self._cancelled.discard(upload_id)

    def is_cancelled(self, upload_id: str) -> bool:
        with self._lock:
            return upload_id in self._cancelled

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            uploads = [dict(upload) for upload in self._uploads.values()]
        uploads.sort(key=lambda item: (item["startedAt"], item["name"]))
        return uploads

    def broadcast(self) -> None:
        self._hub.broadcast_json({"type": "uploads", "uploads": self.snapshot()})


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def create_server(
    directory: str | os.PathLike[str],
    host: str = "0.0.0.0",
    port: int = 8000,
    upload_chunk_size: int = 8 * 1024 * 1024,
) -> ThreadingHTTPServer:
    root = Path(directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / TEMP_DIR_NAME).mkdir(exist_ok=True)

    handler_class = make_handler(root, upload_chunk_size=max(1, upload_chunk_size))
    return ReusableThreadingHTTPServer((host, port), handler_class)


def serve_forever(
    directory: str | os.PathLike[str],
    host: str = "0.0.0.0",
    port: int = 8000,
    upload_chunk_size: int = 8 * 1024 * 1024,
) -> None:
    with create_server(directory, host=host, port=port, upload_chunk_size=upload_chunk_size) as httpd:
        root = httpd.RequestHandlerClass.storage_root
        bound_host, bound_port = httpd.server_address[:2]
        print(f"Serving directory: {root}")
        print("Open one of these URLs on your LAN:")
        for url in advertised_urls(host, bound_host, bound_port):
            print(f"  {url}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


def advertised_urls(requested_host: str, bound_host: str, port: int) -> list[str]:
    hosts: list[str]
    if requested_host in {"", "0.0.0.0", "::"}:
        hosts = ["127.0.0.1", *local_ipv4_addresses()]
    else:
        hosts = [bound_host]

    urls = []
    seen = set()
    for host in hosts:
        if host in seen:
            continue
        seen.add(host)
        urls.append(f"http://{host}:{port}/")
    return urls


def local_ipv4_addresses() -> list[str]:
    addresses = []
    try:
        hostname = socket.gethostname()
        for result in socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM):
            address = result[4][0]
            if not address.startswith("127.") and address not in addresses:
                addresses.append(address)
    except OSError:
        pass
    return addresses


def make_handler(root: Path, upload_chunk_size: int) -> type["LanFileRequestHandler"]:
    websocket_hub = WebSocketHub()
    upload_registry = UploadRegistry(websocket_hub)

    class ConfiguredLanFileRequestHandler(LanFileRequestHandler):
        pass

    ConfiguredLanFileRequestHandler.storage_root = root
    ConfiguredLanFileRequestHandler.browser_upload_chunk_size = upload_chunk_size
    ConfiguredLanFileRequestHandler.websocket_hub = websocket_hub
    ConfiguredLanFileRequestHandler.upload_registry = upload_registry

    return ConfiguredLanFileRequestHandler


class LanFileRequestHandler(BaseHTTPRequestHandler):
    server_version = "LanFileServer/0.1"
    storage_root: Path
    browser_upload_chunk_size: int
    websocket_hub: WebSocketHub
    upload_registry: UploadRegistry

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/":
            self.send_index()
        elif parsed.path == "/api/files":
            self.send_file_list()
        elif parsed.path == "/api/uploads":
            self.send_upload_list()
        elif parsed.path == "/api/upload/status":
            self.send_upload_status(parsed.query)
        elif parsed.path == "/ws":
            self.handle_websocket(parsed.query)
        elif parsed.path.startswith("/files/"):
            self.send_download(parsed.path.removeprefix("/files/"), send_body=True)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_HEAD(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path.startswith("/files/"):
            self.send_download(parsed.path.removeprefix("/files/"), send_body=False)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_PUT(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/api/upload":
            self.receive_upload_chunk(parsed.query)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/api/upload":
            self.receive_upload_chunk(parsed.query)
        elif parsed.path == "/api/upload/cancel":
            self.cancel_upload(parsed.query)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def send_index(self) -> None:
        from .ui import render_index as render_ui

        body = render_ui(self.browser_upload_chunk_size).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file_list(self) -> None:
        files = []
        for file_path in iter_visible_files(self.storage_root):
            try:
                stat = file_path.stat()
            except OSError:
                continue
            files.append(
                {
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": int(stat.st_mtime),
                    "downloadUrl": "/files/" + urllib.parse.quote(file_path.name),
                }
            )
        self.send_json({"files": files})

    def send_upload_list(self) -> None:
        self.send_json({"uploads": self.upload_registry.snapshot()})

    def send_upload_status(self, query: str) -> None:
        try:
            name, total_size, modified, client_id = upload_request_values(query)
            upload_id = upload_identifier(name, total_size, modified)
            temp_path = upload_temp_path(self.storage_root, upload_id)
            final_path = final_file_path(self.storage_root, name)
            with upload_lock(temp_path):
                offset = temp_path.stat().st_size if temp_path.exists() else 0
                if offset >= total_size and temp_path.exists():
                    os.replace(temp_path, final_path)
                    offset = total_size
                    complete = True
                else:
                    complete = False
        except BadRequest as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except OSError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self.send_json(
            {
                "uploadId": upload_id,
                "name": name,
                "offset": offset,
                "size": total_size,
                "clientId": client_id,
                "complete": complete,
            }
        )

    def receive_upload_chunk(self, query: str) -> None:
        try:
            name, total_size, modified, client_id = upload_request_values(query)
            upload_id = upload_identifier(name, total_size, modified)
            content_length = parse_content_length(self.headers.get("Content-Length"))
            client_offset = parse_non_negative_int(self.headers.get("Upload-Offset"), "Upload-Offset")
            temp_path = upload_temp_path(self.storage_root, upload_id)
            final_path = final_file_path(self.storage_root, name)
        except BadRequest as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            with upload_lock(temp_path):
                if self.upload_registry.is_cancelled(upload_id):
                    self.drain_request_body(content_length)
                    unlink_missing_ok(temp_path)
                    self.upload_registry.cancel_complete(upload_id)
                    self.send_json({"error": "Upload was cancelled."}, status=HTTPStatus.CONFLICT)
                    return

                temp_path.parent.mkdir(exist_ok=True)
                server_offset = temp_path.stat().st_size if temp_path.exists() else 0
                if client_offset != server_offset:
                    self.drain_request_body(content_length)
                    self.send_json(
                        {
                            "error": "Upload offset does not match the server offset.",
                            "offset": server_offset,
                        },
                        status=HTTPStatus.CONFLICT,
                    )
                    return

                if server_offset + content_length > total_size:
                    self.drain_request_body(content_length)
                    self.send_json({"error": "Chunk exceeds declared upload size."}, status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                    return

                self.upload_registry.begin(upload_id, name, total_size, modified, client_id, server_offset)
                mode = "r+b" if temp_path.exists() else "wb"
                with temp_path.open(mode) as target:
                    target.seek(server_offset)
                    bytes_written = self.copy_request_body(target, content_length, upload_id, server_offset)
                    target.flush()
                    os.fsync(target.fileno())

                next_offset = server_offset + bytes_written
                complete = next_offset == total_size
                if complete:
                    os.replace(temp_path, final_path)
                    self.upload_registry.finish(upload_id)
                    self.websocket_hub.broadcast_json({"type": "filesChanged"})
                else:
                    self.upload_registry.progress(upload_id, next_offset)

        except UploadCancelled:
            unlink_missing_ok(temp_path)
            self.upload_registry.cancel_complete(upload_id)
            return
        except ConnectionError:
            truncate_file(temp_path, client_offset)
            self.upload_registry.disconnect(upload_id)
            return
        except OSError as exc:
            self.upload_registry.disconnect(upload_id)
            self.send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self.send_json({"uploadId": upload_id, "name": name, "offset": next_offset, "size": total_size, "complete": complete})

    def cancel_upload(self, query: str) -> None:
        try:
            name, total_size, modified, _client_id = upload_request_values(query)
            upload_id = upload_identifier(name, total_size, modified)
            temp_path = upload_temp_path(self.storage_root, upload_id)
        except BadRequest as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self.upload_registry.request_cancel(upload_id)
        try:
            with upload_lock(temp_path):
                unlink_missing_ok(temp_path)
                self.upload_registry.cancel_complete(upload_id)
        except OSError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self.send_json({"uploadId": upload_id, "name": name, "cancelled": True})

    def send_download(self, encoded_name: str, send_body: bool) -> None:
        try:
            name = decode_download_name(encoded_name)
            file_path = final_file_path(self.storage_root, name)
        except BadRequest as exc:
            self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        if not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        try:
            stat = file_path.stat()
            size = stat.st_size
            range_header = self.headers.get("Range")
            if range_header:
                start, end = parse_http_range(range_header, size)
                status = HTTPStatus.PARTIAL_CONTENT
            else:
                start, end = 0, max(0, size - 1)
                status = HTTPStatus.OK
            content_length = 0 if size == 0 else end - start + 1
        except RangeNotSatisfiable:
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range", f"bytes */{file_path.stat().st_size}")
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            return
        except OSError as exc:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
            return

        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Last-Modified", email.utils.formatdate(stat.st_mtime, usegmt=True))
        self.send_header("Content-Disposition", content_disposition_header(name))
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()

        if send_body and content_length:
            try:
                with file_path.open("rb") as source:
                    source.seek(start)
                    copy_limited(source, self.wfile, content_length)
            except (BrokenPipeError, ConnectionResetError):
                return

    def send_json(self, value: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def handle_websocket(self, query: str) -> None:
        key = self.headers.get("Sec-WebSocket-Key")
        upgrade = self.headers.get("Upgrade", "")
        if not key or upgrade.lower() != "websocket":
            self.send_error(HTTPStatus.BAD_REQUEST, "Expected WebSocket upgrade.")
            return

        params = urllib.parse.parse_qs(query, keep_blank_values=True)
        client_id = sanitize_client_id(single_query_value(params, "client", default="unknown"))
        accept = base64.b64encode(hashlib.sha1((key + WEBSOCKET_GUID).encode("ascii")).digest()).decode("ascii")
        client = WebSocketClient(self.wfile)

        self.send_response(HTTPStatus.SWITCHING_PROTOCOLS)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.close_connection = True

        self.websocket_hub.add(client)
        try:
            client.send_json({"type": "hello", "clientId": client_id})
            client.send_json({"type": "uploads", "uploads": self.upload_registry.snapshot()})
            while True:
                frame = read_websocket_frame(self.rfile)
                if frame is None:
                    break
                opcode, payload = frame
                if opcode == 0x8:
                    break
                if opcode == 0x9:
                    client.send_pong(payload)
        except (ConnectionError, OSError):
            pass
        finally:
            self.websocket_hub.remove(client)
            self.upload_registry.client_disconnected(client_id)

    def copy_request_body(self, target, content_length: int, upload_id: str, initial_offset: int) -> int:
        remaining = content_length
        written = 0
        while remaining:
            if self.upload_registry.is_cancelled(upload_id):
                raise UploadCancelled("Upload was cancelled.")
            chunk = self.rfile.read(min(UPLOAD_COPY_BLOCK_SIZE, remaining))
            if not chunk:
                raise ConnectionError("Client closed connection during upload.")
            target.write(chunk)
            written += len(chunk)
            remaining -= len(chunk)
            self.upload_registry.progress(upload_id, initial_offset + written)
        return written

    def drain_request_body(self, content_length: int) -> None:
        remaining = content_length
        while remaining:
            chunk = self.rfile.read(min(UPLOAD_COPY_BLOCK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)


def iter_visible_files(root: Path):
    try:
        entries = sorted(root.iterdir(), key=lambda item: item.name.casefold())
    except OSError:
        return

    for entry in entries:
        if entry.name == TEMP_DIR_NAME:
            continue
        if entry.is_file():
            yield entry


def upload_request_values(query: str) -> tuple[str, int, str, str]:
    params = urllib.parse.parse_qs(query, keep_blank_values=True)
    raw_name = single_query_value(params, "name")
    size = parse_non_negative_int(single_query_value(params, "size"), "size")
    modified = single_query_value(params, "mtime", default="0")
    client_id = sanitize_client_id(single_query_value(params, "client", default="unknown"))
    return sanitize_upload_name(raw_name), size, modified, client_id


def single_query_value(params: dict[str, list[str]], key: str, default: str | None = None) -> str:
    values = params.get(key)
    if not values:
        if default is None:
            raise BadRequest(f"Missing query parameter: {key}")
        return default
    return values[0]


def parse_content_length(value: str | None) -> int:
    if value is None:
        raise BadRequest("Missing Content-Length header.")
    return parse_non_negative_int(value, "Content-Length")


def parse_non_negative_int(value: str | None, label: str) -> int:
    if value is None or value == "":
        raise BadRequest(f"Missing {label}.")
    try:
        number = int(value)
    except ValueError as exc:
        raise BadRequest(f"{label} must be an integer.") from exc
    if number < 0:
        raise BadRequest(f"{label} must be non-negative.")
    return number


def sanitize_upload_name(raw_name: str) -> str:
    name = raw_name.replace("\\", "/")
    name = posixpath.basename(name)
    name = name.replace("\x00", "")
    name = "".join("_" if (char in WINDOWS_UNSAFE_CHARS or ord(char) < 32) else char for char in name)
    name = name.strip()
    name = name.rstrip(". ")
    if name in {"", ".", ".."}:
        raise BadRequest("Invalid file name.")
    if name.casefold() == TEMP_DIR_NAME.casefold():
        raise BadRequest("This file name is reserved.")
    return name


def decode_download_name(encoded_name: str) -> str:
    name = urllib.parse.unquote(encoded_name)
    if not name or name in {".", ".."}:
        raise BadRequest("Invalid file name.")
    if "\x00" in name or "/" in name or "\\" in name:
        raise BadRequest("Nested paths are not allowed.")
    if name.casefold() == TEMP_DIR_NAME.casefold():
        raise BadRequest("This file name is reserved.")
    return name


def final_file_path(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if path.parent != root:
        raise BadRequest("File must stay inside the shared directory.")
    return path


def sanitize_client_id(value: str) -> str:
    cleaned = "".join(char for char in value if char.isalnum() or char in {"-", "_"})
    return cleaned[:80] or "unknown"


def upload_identifier(name: str, total_size: int, modified: str) -> str:
    return hashlib.sha256(f"{name}\0{total_size}\0{modified}".encode("utf-8")).hexdigest()


def upload_temp_path(root: Path, upload_id: str) -> Path:
    return root / TEMP_DIR_NAME / f"{upload_id}.part"


def unlink_missing_ok(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def truncate_file(path: Path, size: int) -> None:
    try:
        with path.open("r+b") as file:
            file.truncate(size)
    except FileNotFoundError:
        pass


def upload_lock(path: Path) -> threading.Lock:
    key = str(path)
    with _upload_locks_guard:
        lock = _upload_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _upload_locks[key] = lock
        return lock


def parse_http_range(header: str, size: int) -> tuple[int, int]:
    if size <= 0:
        raise RangeNotSatisfiable("Empty files do not have byte ranges.")

    if "," in header:
        raise RangeNotSatisfiable("Multiple ranges are not supported.")

    match = _RANGE_RE.match(header.strip())
    if not match:
        raise RangeNotSatisfiable("Invalid Range header.")

    start_text, end_text = match.groups()
    if not start_text and not end_text:
        raise RangeNotSatisfiable("Invalid Range header.")

    if not start_text:
        suffix_length = int(end_text)
        if suffix_length <= 0:
            raise RangeNotSatisfiable("Invalid suffix range.")
        start = max(size - suffix_length, 0)
        end = size - 1
    else:
        start = int(start_text)
        end = int(end_text) if end_text else size - 1
        if start >= size or start > end:
            raise RangeNotSatisfiable("Requested range is outside the file.")
        end = min(end, size - 1)

    return start, end


def content_disposition_header(name: str) -> str:
    ascii_name = name.encode("ascii", "ignore").decode("ascii")
    ascii_name = "".join("_" if (char in {'"', "\\"} or ord(char) < 32 or ord(char) == 127) else char for char in ascii_name)
    if not ascii_name:
        ascii_name = "download"
    quoted_name = urllib.parse.quote(name)
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quoted_name}"


def copy_limited(source, target, length: int) -> None:
    remaining = length
    while remaining:
        chunk = source.read(min(DOWNLOAD_COPY_BLOCK_SIZE, remaining))
        if not chunk:
            break
        target.write(chunk)
        remaining -= len(chunk)


def read_websocket_frame(reader) -> tuple[int, bytes] | None:
    header = reader.read(2)
    if not header:
        return None
    if len(header) != 2:
        raise ConnectionError("Incomplete WebSocket frame header.")

    first, second = header
    opcode = first & 0x0F
    masked = bool(second & 0x80)
    length = second & 0x7F
    if length == 126:
        length = struct.unpack("!H", read_exact(reader, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", read_exact(reader, 8))[0]

    mask = read_exact(reader, 4) if masked else b""
    payload = read_exact(reader, length) if length else b""
    if masked:
        payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    return opcode, payload


def read_exact(reader, length: int) -> bytes:
    data = reader.read(length)
    if len(data) != length:
        raise ConnectionError("Incomplete WebSocket frame.")
    return data
