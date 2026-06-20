# py-lan-file-server

A small cross-platform Python HTTP server for sharing one folder on a local network. Start it from the command line, open the printed URL in a browser, and LAN users can upload, search, and download files.

## Features

- Clean browser UI with folder browsing, file search, drag-and-drop file upload, size display, modified timestamps, and delete actions.
- Server-side folder pagination with at most 10 visible items per page.
- Recursive file count and total size statistics for the current folder.
- Folder selection uploads every file recursively while preserving relative paths.
- Live upload status over WebSocket, including uploads started by other clients.
- Optional PIN protection for the web UI, API, uploads, downloads, and WebSocket connection.
- Resumable file downloads through standard HTTP `Range` requests.
- Recursive folder downloads as ZIP archives, including support for resuming interrupted ZIP transfers.
- Resumable browser uploads through chunked transfer.
- Upload cancellation from the originating browser client.
- Streaming upload and download paths, suitable for large files.
- Same-name uploads replace the existing file after the new upload completes.
- No runtime dependencies beyond the Python standard library.

## Requirements

Python 3.9 or newer.

## Run From Source

```bash
python -m lan_file_server --dir ./shared --host 0.0.0.0 --port 8000 --title "Team Files" --pin 1234
```

Open the URL printed in the terminal. Other devices on the same LAN can use the printed LAN address, for example `http://192.168.1.23:8000/`.

The shared directory is created automatically when it does not exist. The default directory is `./shared`.

## Install The Command

```bash
python -m pip install .
lan-file-server --dir ./shared --port 8000
```

## Folders

The shared directory may contain nested folders. The browser UI lets users open folders, go back to parent folders, download files from any level, and delete files or entire folders.

Use `Choose folder` to upload a local directory recursively. Each file is uploaded as its own resumable transfer and keeps its relative path under the selected folder.

Use `Folder ZIP` to download the current folder recursively, or use the `ZIP` action beside any folder row. ZIP downloads keep the selected folder as the top-level entry inside the archive.

## Upload Resume

The web page splits files into chunks before uploading. If the browser tab is closed or the network drops, open the page again, select the same local file, and start the upload. The server continues from the bytes it already received.

Temporary upload data is stored in `.uploads` under the shared directory and is hidden from the file list. When an upload completes, the temporary file is moved atomically into the shared directory and replaces any same-name file.

## Live Uploads And Cancellation

Connected browser clients receive upload status through WebSocket. The upload panel highlights the active file with the highest current progress and folds the rest into a compact summary with elapsed time, total file count, and uploaded file count. The highlighted row is marked as either `This client` or `Other client`, so uploads started in another browser remain visible without cluttering the page.

Only the browser client that started an upload can cancel it from the page. A manual cancellation aborts the local request and removes the server-side temporary upload file. If a connection drops unexpectedly, the active upload row is removed from connected pages and the incomplete in-flight chunk is rolled back; previously completed chunks remain available for resume.

## Download Resume

File downloads support HTTP `Range`, so browsers, download managers, and tools such as `curl -C -` can resume interrupted downloads. Folder ZIP downloads also accept `Range` requests; the server rebuilds the ZIP before serving the requested byte range.

## Delete Files And Folders

Each file and folder row has a `Delete` action. Deleting a folder removes the folder recursively. Connected pages refresh through WebSocket after a successful delete.

## PIN Protection

Use `--pin` to require a PIN before clients can access the page, API, uploads, downloads, delete actions, or WebSocket updates.

```bash
lan-file-server --dir ./shared --pin 1234
```

After a successful unlock, the browser receives an HTTP-only cookie containing a random salt and a server-verifiable signature. The PIN itself is not stored in the cookie. If `--pin` is omitted, clients can open the site directly.

## CLI

```bash
lan-file-server [directory] [--dir DIR] [--host HOST] [--port PORT] [--chunk-size BYTES] [--title TITLE] [--pin PIN]
```

Common examples:

```bash
lan-file-server --dir ./shared
lan-file-server ./shared --host 0.0.0.0 --port 8000
lan-file-server ./shared --title "Team Files"
lan-file-server ./shared --pin 1234
```

If `--title` is omitted, the browser title and page heading use the default `LAN Files`.
