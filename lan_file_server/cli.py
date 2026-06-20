from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .server import serve_forever


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lan-file-server",
        description="Serve one folder on the LAN with browser upload/download support.",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        help="Folder used as the shared file collection. Defaults to ./shared.",
    )
    parser.add_argument(
        "-d",
        "--dir",
        dest="directory_option",
        help="Folder used as the shared file collection. Overrides the positional folder.",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Address to bind. Use 0.0.0.0 to listen on all network interfaces.",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="TCP port to listen on.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=8 * 1024 * 1024,
        help="Browser upload chunk size in bytes.",
    )
    parser.add_argument(
        "--title",
        default="LAN Files",
        help='Browser page title. Defaults to "LAN Files".',
    )
    parser.add_argument(
        "--pin",
        default=None,
        help="Require this PIN before clients can access the web UI, API, uploads, and downloads.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    directory = Path(args.directory_option or args.directory or "shared")
    serve_forever(
        directory,
        host=args.host,
        port=args.port,
        upload_chunk_size=args.chunk_size,
        page_title=args.title,
        pin=args.pin,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
