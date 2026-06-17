# py-lan-file-server

A small cross-platform Python HTTP server for sharing one folder on a local network. Start it from the command line, open the printed URL in a browser, and LAN users can upload, search, and download files.

## Features

- Clean browser UI with file search, drag-and-drop upload, size display, and modified timestamps.
- Live upload status over WebSocket, including uploads started by other clients.
- Resumable downloads through standard HTTP `Range` requests.
- Resumable browser uploads through chunked transfer.
- Upload cancellation from the originating browser client.
- Streaming upload and download paths, suitable for large files.
- Same-name uploads replace the existing file after the new upload completes.
- No runtime dependencies beyond the Python standard library.

## Requirements

Python 3.9 or newer.

## Run From Source

```bash
python -m lan_file_server --dir ./shared --host 0.0.0.0 --port 8000
```

Open the URL printed in the terminal. Other devices on the same LAN can use the printed LAN address, for example `http://192.168.1.23:8000/`.

The shared directory is created automatically when it does not exist. The default directory is `./shared`.

## Install The Command

```bash
python -m pip install .
lan-file-server --dir ./shared --port 8000
```

## Upload Resume

The web page splits files into chunks before uploading. If the browser tab is closed or the network drops, open the page again, select the same local file, and start the upload. The server continues from the bytes it already received.

Temporary upload data is stored in `.uploads` under the shared directory and is hidden from the file list. When an upload completes, the temporary file is moved atomically into the shared directory and replaces any same-name file.

## Live Uploads And Cancellation

Connected browser clients receive upload status through WebSocket. The upload panel shows active uploads from all clients and marks each row as either `This client` or `Other client`.

Only the browser client that started an upload can cancel it from the page. A manual cancellation aborts the local request and removes the server-side temporary upload file. If a connection drops unexpectedly, the active upload row is removed from connected pages and the incomplete in-flight chunk is rolled back; previously completed chunks remain available for resume.

## Download Resume

Downloads support HTTP `Range`, so browsers, download managers, and tools such as `curl -C -` can resume interrupted downloads.

## CLI

```bash
lan-file-server [directory] [--dir DIR] [--host HOST] [--port PORT] [--chunk-size BYTES]
```

Common examples:

```bash
lan-file-server --dir ./shared
lan-file-server ./shared --host 0.0.0.0 --port 8000
```
