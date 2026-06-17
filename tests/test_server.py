from __future__ import annotations

import base64
import io
import os
import json
import socket
import struct
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from lan_file_server.server import RangeNotSatisfiable, create_server, parse_http_range


class RangeParsingTests(unittest.TestCase):
    def test_parse_start_end_range(self) -> None:
        self.assertEqual(parse_http_range("bytes=2-5", 10), (2, 5))

    def test_parse_open_ended_range(self) -> None:
        self.assertEqual(parse_http_range("bytes=7-", 10), (7, 9))

    def test_parse_suffix_range(self) -> None:
        self.assertEqual(parse_http_range("bytes=-4", 10), (6, 9))

    def test_reject_unsatisfiable_range(self) -> None:
        with self.assertRaises(RangeNotSatisfiable):
            parse_http_range("bytes=12-20", 10)


class ServerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.httpd = create_server(self.root, host="127.0.0.1", port=0, upload_chunk_size=4)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.thread.join(timeout=5)
        self.httpd.server_close()
        self.temp_dir.cleanup()

    def open(self, path: str, **kwargs):
        return urllib.request.urlopen(self.base_url + path, timeout=5, **kwargs)

    def test_download_supports_range_requests(self) -> None:
        (self.root / "sample.bin").write_bytes(b"0123456789")
        request = urllib.request.Request(
            self.base_url + "/files/sample.bin",
            headers={"Range": "bytes=2-5"},
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(response.headers["Content-Range"], "bytes 2-5/10")
            self.assertEqual(response.headers["Accept-Ranges"], "bytes")
            self.assertEqual(response.read(), b"2345")

    def test_file_list_supports_folders_and_nested_downloads(self) -> None:
        nested = self.root / "docs"
        nested.mkdir()
        (nested / "readme.txt").write_bytes(b"hello-folder")

        root_listing = self.get_files()
        self.assertEqual(root_listing["folders"][0]["name"], "docs")
        self.assertEqual(root_listing["folders"][0]["path"], "docs")
        self.assertEqual(root_listing["folders"][0]["downloadUrl"], "/folders/docs")

        docs_listing = self.get_files("docs")
        self.assertEqual(docs_listing["path"], "docs")
        self.assertEqual(docs_listing["parent"], "")
        self.assertEqual(docs_listing["downloadUrl"], "/folders/docs")
        self.assertEqual(docs_listing["files"][0]["path"], "docs/readme.txt")

        with self.open("/files/docs/readme.txt") as response:
            self.assertEqual(response.read(), b"hello-folder")

    def test_folder_download_returns_recursive_zip(self) -> None:
        docs = self.root / "docs"
        (docs / "nested").mkdir(parents=True)
        (docs / "empty").mkdir()
        (docs / "readme.txt").write_bytes(b"hello-folder")
        (docs / "nested" / "guide.txt").write_bytes(b"nested-guide")

        with self.open("/folders/docs") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Content-Type"], "application/zip")
            self.assertEqual(response.headers["Accept-Ranges"], "bytes")
            archive_data = response.read()

        with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
            self.assertEqual(archive.read("docs/readme.txt"), b"hello-folder")
            self.assertEqual(archive.read("docs/nested/guide.txt"), b"nested-guide")
            self.assertIn("docs/empty/", archive.namelist())

    def test_root_folder_download_skips_upload_temp_directory(self) -> None:
        (self.root / "visible.txt").write_bytes(b"visible")
        (self.root / ".uploads" / "hidden.part").write_bytes(b"hidden")

        with self.open("/folders/") as response:
            archive_data = response.read()

        with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
            self.assertEqual(archive.read("shared/visible.txt"), b"visible")
            self.assertNotIn("shared/.uploads/hidden.part", archive.namelist())

    def test_folder_download_supports_range_requests(self) -> None:
        docs = self.root / "docs"
        docs.mkdir()
        (docs / "readme.txt").write_bytes(b"hello-folder")
        with self.open("/folders/docs") as response:
            archive_data = response.read()

        request = urllib.request.Request(
            self.base_url + "/folders/docs",
            headers={"Range": "bytes=0-9"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(response.headers["Content-Range"], f"bytes 0-9/{len(archive_data)}")
            self.assertEqual(response.read(), archive_data[:10])

    def test_delete_file_and_folder(self) -> None:
        (self.root / "delete-me.txt").write_bytes(b"gone")
        folder = self.root / "folder"
        (folder / "nested").mkdir(parents=True)
        (folder / "nested" / "file.txt").write_bytes(b"gone-too")

        file_result = self.delete_item("delete-me.txt")
        self.assertTrue(file_result["deleted"])
        self.assertEqual(file_result["type"], "file")
        self.assertFalse((self.root / "delete-me.txt").exists())

        folder_result = self.delete_item("folder")
        self.assertTrue(folder_result["deleted"])
        self.assertEqual(folder_result["type"], "folder")
        self.assertFalse(folder.exists())

    def test_delete_rejects_root_and_reserved_paths(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as missing_path:
            self.delete_item("")
        self.assertEqual(missing_path.exception.code, 400)

        with self.assertRaises(urllib.error.HTTPError) as reserved_path:
            self.delete_item(".uploads/temp.part")
        self.assertEqual(reserved_path.exception.code, 400)

    def test_download_rejects_unsatisfiable_ranges(self) -> None:
        (self.root / "sample.bin").write_bytes(b"0123456789")
        request = urllib.request.Request(
            self.base_url + "/files/sample.bin",
            headers={"Range": "bytes=20-30"},
        )

        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(raised.exception.code, 416)
        self.assertEqual(raised.exception.headers["Content-Range"], "bytes */10")

    def test_upload_chunks_are_resumable_and_replace_final_file(self) -> None:
        self.put_upload_chunk("clips/movie.bin", total=6, offset=0, body=b"abc")
        self.assertFalse((self.root / "clips" / "movie.bin").exists())

        status = self.get_upload_status("clips/movie.bin", total=6)
        self.assertIn("uploadId", status)
        self.assertEqual(status["offset"], 3)
        self.assertFalse(status["complete"])

        uploads = self.get_uploads()
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0]["name"], "clips/movie.bin")
        self.assertEqual(uploads[0]["offset"], 3)

        final = self.put_upload_chunk("clips/movie.bin", total=6, offset=3, body=b"def")
        self.assertTrue(final["complete"])
        self.assertEqual((self.root / "clips" / "movie.bin").read_bytes(), b"abcdef")
        self.assertEqual(self.get_uploads(), [])

        replaced = self.put_upload_chunk("clips/movie.bin", total=3, offset=0, body=b"xyz", mtime="2")
        self.assertTrue(replaced["complete"])
        self.assertEqual((self.root / "clips" / "movie.bin").read_bytes(), b"xyz")

    def test_upload_cancel_removes_partial_file_and_active_status(self) -> None:
        self.put_upload_chunk("cancel.bin", total=6, offset=0, body=b"abc")
        self.assertEqual(len(list((self.root / ".uploads").glob("*.part"))), 1)

        result = self.cancel_upload("cancel.bin", total=6)
        self.assertTrue(result["cancelled"])
        self.assertEqual(self.get_uploads(), [])
        self.assertEqual(list((self.root / ".uploads").glob("*.part")), [])

    def test_websocket_receives_upload_updates(self) -> None:
        with self.websocket("observer") as sock:
            self.assertEqual(self.read_ws_json(sock)["type"], "hello")
            initial = self.read_ws_json(sock)
            self.assertEqual(initial, {"type": "uploads", "uploads": []})

            self.put_upload_chunk("live.bin", total=6, offset=0, body=b"abc", client="other-client")
            update = self.read_until_upload_offset(sock, "live.bin", 3)
            self.assertEqual(update["uploads"][0]["name"], "live.bin")
            self.assertEqual(update["uploads"][0]["clientId"], "other-client")
            self.assertEqual(update["uploads"][0]["offset"], 3)

            self.put_upload_chunk("live.bin", total=6, offset=3, body=b"def", client="other-client")
            final = self.read_until_upload_count(sock, 0)
            self.assertEqual(final["uploads"], [])

    def put_upload_chunk(
        self,
        name: str,
        total: int,
        offset: int,
        body: bytes,
        mtime: str = "1",
        client: str = "test-client",
    ) -> dict:
        params = urllib.parse.urlencode({"path": name, "size": str(total), "mtime": mtime, "client": client})
        request = urllib.request.Request(
            self.base_url + "/api/upload?" + params,
            data=body,
            method="PUT",
            headers={"Upload-Offset": str(offset)},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_upload_status(self, name: str, total: int, mtime: str = "1", client: str = "test-client") -> dict:
        params = urllib.parse.urlencode({"path": name, "size": str(total), "mtime": mtime, "client": client})
        with self.open("/api/upload/status?" + params) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_files(self, path: str = "") -> dict:
        params = urllib.parse.urlencode({"path": path})
        with self.open("/api/files?" + params) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_uploads(self) -> list[dict]:
        with self.open("/api/uploads") as response:
            return json.loads(response.read().decode("utf-8"))["uploads"]

    def cancel_upload(self, name: str, total: int, mtime: str = "1", client: str = "test-client") -> dict:
        params = urllib.parse.urlencode({"path": name, "size": str(total), "mtime": mtime, "client": client})
        request = urllib.request.Request(
            self.base_url + "/api/upload/cancel?" + params,
            data=b"",
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def delete_item(self, path: str) -> dict:
        params = urllib.parse.urlencode({"path": path})
        request = urllib.request.Request(
            self.base_url + "/api/files?" + params,
            data=None,
            method="DELETE",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def websocket(self, client: str) -> socket.socket:
        sock = socket.create_connection(("127.0.0.1", self.httpd.server_address[1]), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET /ws?client={urllib.parse.quote(client)} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.httpd.server_address[1]}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response:
            response += sock.recv(1)
        self.assertIn(b" 101 ", response)
        return sock

    def read_until_upload_count(self, sock: socket.socket, count: int) -> dict:
        for _ in range(10):
            message = self.read_ws_json(sock)
            if message.get("type") == "uploads" and len(message.get("uploads", [])) == count:
                return message
        self.fail(f"Did not receive uploads message with {count} uploads")

    def read_until_upload_offset(self, sock: socket.socket, name: str, offset: int) -> dict:
        for _ in range(10):
            message = self.read_ws_json(sock)
            if message.get("type") != "uploads":
                continue
            for upload in message.get("uploads", []):
                if upload.get("name") == name and upload.get("offset", 0) >= offset:
                    return message
        self.fail(f"Did not receive upload {name!r} at offset {offset}")

    def read_ws_json(self, sock: socket.socket) -> dict:
        header = self.recv_exact(sock, 2)
        first, second = header
        opcode = first & 0x0F
        self.assertEqual(opcode, 0x1)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self.recv_exact(sock, 2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self.recv_exact(sock, 8))[0]
        payload = self.recv_exact(sock, length)
        return json.loads(payload.decode("utf-8"))

    def recv_exact(self, sock: socket.socket, length: int) -> bytes:
        data = b""
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                raise ConnectionError("socket closed")
            data += chunk
        return data


if __name__ == "__main__":
    unittest.main()
