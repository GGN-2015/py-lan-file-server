from __future__ import annotations

import html


DEFAULT_PAGE_TITLE = "LAN Files"


def render_index(upload_chunk_size: int, page_title: str = DEFAULT_PAGE_TITLE) -> str:
    escaped_chunk_size = html.escape(str(upload_chunk_size), quote=True)
    escaped_title = html.escape(page_title or DEFAULT_PAGE_TITLE)
    return (
        PAGE_HTML
        .replace("__UPLOAD_CHUNK_SIZE__", escaped_chunk_size)
        .replace("__PAGE_TITLE__", escaped_title)
    )


PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__PAGE_TITLE__</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: #f4f6f8;
      --fg: #18212f;
      --muted: #697586;
      --line: #d9e0ea;
      --accent: #2563eb;
      --accent-strong: #1d4ed8;
      --surface: #ffffff;
      --surface-soft: #f8fafc;
      --surface-raised: #ffffff;
      --success: #168153;
      --danger: #b42318;
      --shadow: 0 16px 40px rgb(24 33 47 / 0.08);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #111418;
        --fg: #ecf1f7;
        --muted: #a6b0bf;
        --line: #2d3746;
        --accent: #60a5fa;
        --accent-strong: #93c5fd;
        --surface: #171c22;
        --surface-soft: #1f2630;
        --surface-raised: #1b222b;
        --success: #62d18f;
        --danger: #ff8a80;
        --shadow: 0 16px 40px rgb(0 0 0 / 0.22);
      }
    }
    * {
      box-sizing: border-box;
    }
    html {
      min-width: 320px;
    }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--fg);
    }
    body.dragging .upload-panel {
      border-color: var(--accent);
      box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 18%, transparent), var(--shadow);
    }
    main {
      width: min(1120px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 42px;
    }
    header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      align-items: end;
      margin-bottom: 18px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: clamp(30px, 4vw, 44px);
      line-height: 1;
      letter-spacing: 0;
    }
    .subtitle {
      color: var(--muted);
      min-height: 22px;
    }
    .stats {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }
    .stat {
      min-width: 96px;
      padding: 9px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      text-align: right;
    }
    .stat-value {
      display: block;
      font-size: 18px;
      font-weight: 750;
      line-height: 1.15;
    }
    .stat-label {
      display: block;
      margin-top: 2px;
      color: var(--muted);
      font-size: 12px;
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(300px, 390px) minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }
    .panel,
    .files-shell {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }
    .upload-panel {
      position: sticky;
      top: 18px;
      padding: 16px;
      transition: border-color 160ms ease, box-shadow 160ms ease;
    }
    .panel-title,
    .files-title {
      margin: 0;
      font-size: 16px;
      line-height: 1.25;
      letter-spacing: 0;
    }
    #currentPath {
      margin-top: 4px;
      overflow-wrap: anywhere;
    }
    .panel-head,
    .files-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }
    .actions {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
    button,
    .file-button,
    .search-input {
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface-raised);
      color: var(--fg);
      font: inherit;
      letter-spacing: 0;
    }
    button,
    .file-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      padding: 8px 12px;
      cursor: pointer;
      user-select: none;
    }
    button.icon {
      width: 38px;
      padding: 0;
      font-size: 18px;
      line-height: 1;
    }
    button.primary {
      border-color: var(--accent);
      background: var(--accent);
      color: white;
      font-weight: 700;
    }
    button:hover,
    .file-button:hover,
    .search-input:focus {
      border-color: var(--accent-strong);
    }
    button:focus-visible,
    .file-button:focus-visible,
    .search-input:focus-visible {
      outline: 3px solid color-mix(in srgb, var(--accent) 28%, transparent);
      outline-offset: 2px;
    }
    button:disabled {
      cursor: not-allowed;
      opacity: 0.48;
    }
    #clearBtn:disabled {
      visibility: hidden;
      opacity: 0;
    }
    input[type="file"] {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
      clip-path: inset(50%);
      white-space: nowrap;
    }
    .drop-zone {
      display: grid;
      gap: 12px;
      padding: 16px;
      border: 1px dashed var(--line);
      border-radius: 8px;
      background: var(--surface-soft);
    }
    .selection-summary {
      min-height: 24px;
      color: var(--muted);
      overflow-wrap: anywhere;
    }
    .selection-list,
    .upload-list,
    .active-upload-list {
      display: grid;
      gap: 9px;
      margin-top: 14px;
    }
    .selection-item,
    .upload-item,
    .active-upload-item {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: center;
      min-height: 56px;
      padding: 10px 11px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-raised);
    }
    .file-name,
    .upload-name {
      min-width: 0;
      font-weight: 650;
      overflow-wrap: anywhere;
    }
    .active-upload-item.other {
      border-color: color-mix(in srgb, var(--accent) 34%, var(--line));
    }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 2px 7px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      white-space: nowrap;
    }
    .badge.other {
      border-color: color-mix(in srgb, var(--accent) 42%, var(--line));
      color: var(--accent-strong);
    }
    .meta,
    .upload-note,
    .upload-percent {
      color: var(--muted);
      font-size: 13px;
    }
    .upload-percent {
      min-width: 48px;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .progress-track {
      height: 8px;
      margin-top: 8px;
      overflow: hidden;
      border-radius: 999px;
      background: color-mix(in srgb, var(--line) 72%, transparent);
    }
    .progress-bar {
      width: 0%;
      height: 100%;
      border-radius: inherit;
      background: var(--accent);
      transition: width 120ms ease;
    }
    .upload-item.complete .progress-bar {
      background: var(--success);
    }
    .upload-item.failed .progress-bar {
      background: var(--danger);
    }
    .files-shell {
      overflow: hidden;
    }
    .files-head {
      margin: 0;
      padding: 14px;
      border-bottom: 1px solid var(--line);
      background: var(--surface);
    }
    .files-head .actions {
      flex: 0 1 360px;
      flex-wrap: nowrap;
      justify-content: flex-end;
    }
    .search-wrap {
      position: relative;
      flex: 1 1 260px;
      min-width: 220px;
      max-width: 300px;
    }
    .search-wrap span {
      position: absolute;
      left: 11px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--muted);
      pointer-events: none;
    }
    .search-input {
      width: 100%;
      padding: 8px 12px 8px 32px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th,
    td {
      padding: 13px 14px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: middle;
    }
    th {
      color: var(--muted);
      background: var(--surface-soft);
      font-size: 12px;
      font-weight: 750;
    }
    tr:last-child td {
      border-bottom: 0;
    }
    tbody tr {
      transition: background 120ms ease;
    }
    tbody tr:hover {
      background: var(--surface-soft);
    }
    a {
      color: var(--accent-strong);
      text-decoration: none;
      overflow-wrap: anywhere;
    }
    a:hover {
      text-decoration: underline;
    }
    .name-cell {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }
    .file-mark {
      display: inline-grid;
      place-items: center;
      flex: 0 0 32px;
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: color-mix(in srgb, var(--accent) 13%, var(--surface-soft));
      color: var(--accent-strong);
      font-weight: 800;
    }
    .file-link {
      font-weight: 650;
    }
    .size {
      white-space: nowrap;
      font-variant-numeric: tabular-nums;
    }
    .download-link {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 34px;
      padding: 6px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface-raised);
      color: var(--fg);
      font-weight: 650;
    }
    .download-link:hover {
      border-color: var(--accent-strong);
      text-decoration: none;
    }
    .row-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .delete-button {
      min-height: 34px;
      padding: 6px 10px;
      border-color: color-mix(in srgb, var(--danger) 40%, var(--line));
      color: var(--danger);
      font-weight: 650;
    }
    .delete-button:hover {
      border-color: var(--danger);
    }
    .current-folder-link {
      flex: 0 0 auto;
    }
    .pagination {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 14px;
      border-top: 1px solid var(--line);
      background: var(--surface);
    }
    .pagination .actions {
      flex-wrap: nowrap;
    }
    .page-status {
      color: var(--muted);
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    .empty {
      display: grid;
      place-items: center;
      min-height: 220px;
      padding: 24px;
      color: var(--muted);
      text-align: center;
    }
    .status-ok {
      color: var(--success);
    }
    .status-error {
      color: var(--danger);
    }
    .subsection-title {
      margin: 16px 0 0;
      color: var(--muted);
      font-size: 12px;
      font-weight: 750;
      letter-spacing: 0;
      text-transform: uppercase;
    }
    @media (max-width: 900px) {
      main {
        width: min(100vw - 22px, 1120px);
      }
      header,
      .layout {
        grid-template-columns: 1fr;
      }
      .stats {
        justify-content: flex-start;
      }
      .upload-panel {
        position: static;
      }
    }
    @media (max-width: 650px) {
      main {
        padding-top: 18px;
      }
      .stats {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
      .stat {
        min-width: 0;
        text-align: left;
      }
      .panel-head,
      .files-head,
      .pagination,
      .drop-zone .actions {
        align-items: stretch;
        flex-direction: column;
      }
      .search-wrap,
      .actions button,
      .actions .download-link,
      .file-button {
        width: 100%;
      }
      .files-head .actions {
        flex: 1 1 auto;
        flex-wrap: nowrap;
        width: 100%;
      }
      .files-head .search-wrap {
        min-width: 0;
        max-width: none;
      }
      .files-head button.icon {
        flex: 0 0 48px;
      }
      table,
      thead,
      tbody,
      th,
      td,
      tr {
        display: block;
      }
      thead {
        display: none;
      }
      tbody tr {
        padding: 10px 0;
        border-bottom: 1px solid var(--line);
      }
      tbody tr:last-child {
        border-bottom: 0;
      }
      td {
        border-bottom: 0;
        padding: 7px 14px;
      }
      td::before {
        content: attr(data-label);
        display: block;
        margin-bottom: 4px;
        color: var(--muted);
        font-size: 12px;
      }
      .name-cell {
        align-items: flex-start;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>__PAGE_TITLE__</h1>
        <div id="summary" class="subtitle">Loading files...</div>
      </div>
      <div class="stats" aria-live="polite">
        <div class="stat">
          <span id="fileCount" class="stat-value">0</span>
          <span class="stat-label">Files</span>
        </div>
        <div class="stat">
          <span id="totalSize" class="stat-value">0 B</span>
          <span class="stat-label">Total size</span>
        </div>
        <div class="stat">
          <span id="latestTime" class="stat-value">-</span>
          <span class="stat-label">Latest</span>
        </div>
      </div>
    </header>

    <div class="layout">
      <section class="panel upload-panel" aria-labelledby="uploadTitle">
        <div class="panel-head">
          <h2 id="uploadTitle" class="panel-title">Upload</h2>
          <button id="clearBtn" class="icon" type="button" title="Clear selection" aria-label="Clear selection" disabled>
            <span aria-hidden="true">x</span>
          </button>
        </div>
        <div id="dropZone" class="drop-zone">
          <input id="fileInput" type="file" multiple>
          <input id="folderInput" type="file" multiple webkitdirectory directory>
          <div class="actions">
            <label class="file-button" for="fileInput">
              <span aria-hidden="true">+</span>
              <span>Choose files</span>
            </label>
            <label class="file-button" for="folderInput">
              <span aria-hidden="true">[]</span>
              <span>Choose folder</span>
            </label>
            <button id="uploadBtn" class="primary" type="button" disabled>
              <span aria-hidden="true">^</span>
              <span>Upload</span>
            </button>
          </div>
          <div id="selectionSummary" class="selection-summary">No files selected</div>
        </div>
        <h3 class="subsection-title">Active uploads</h3>
        <div id="activeUploads" class="active-upload-list" aria-live="polite"></div>
        <div id="selectionList" class="selection-list"></div>
        <div id="uploadList" class="upload-list" aria-live="polite"></div>
      </section>

      <section class="files-shell" aria-labelledby="filesTitle">
        <div class="files-head">
          <div>
            <h2 id="filesTitle" class="files-title">Files</h2>
            <div id="currentPath" class="meta"></div>
          </div>
          <div class="actions">
            <label class="search-wrap">
              <span aria-hidden="true">?</span>
              <input id="fileSearch" class="search-input" type="search" placeholder="Search files" autocomplete="off">
            </label>
            <a id="downloadFolderBtn" class="download-link current-folder-link" href="/folders/" download="shared.zip" title="Download current folder as ZIP">
              <span aria-hidden="true">v</span>
              <span>Folder ZIP</span>
            </a>
            <button id="refreshBtn" class="icon" type="button" title="Refresh" aria-label="Refresh">
              <span aria-hidden="true">R</span>
            </button>
          </div>
        </div>
        <div id="files"></div>
      </section>
    </div>
  </main>

  <script>
    const CHUNK_SIZE = Number("__UPLOAD_CHUNK_SIZE__");
    const fileInput = document.querySelector("#fileInput");
    const folderInput = document.querySelector("#folderInput");
    const uploadBtn = document.querySelector("#uploadBtn");
    const clearBtn = document.querySelector("#clearBtn");
    const uploadList = document.querySelector("#uploadList");
    const activeUploads = document.querySelector("#activeUploads");
    const selectionList = document.querySelector("#selectionList");
    const selectionSummary = document.querySelector("#selectionSummary");
    const filesSection = document.querySelector("#files");
    const summary = document.querySelector("#summary");
    const refreshBtn = document.querySelector("#refreshBtn");
    const downloadFolderBtn = document.querySelector("#downloadFolderBtn");
    const fileSearch = document.querySelector("#fileSearch");
    const dropZone = document.querySelector("#dropZone");
    const fileCount = document.querySelector("#fileCount");
    const totalSize = document.querySelector("#totalSize");
    const latestTime = document.querySelector("#latestTime");
    const currentPathLabel = document.querySelector("#currentPath");
    let selectedFiles = [];
    let allFiles = [];
    let allFolders = [];
    let currentPath = "";
    let currentPage = 1;
    let currentPagination = { page: 1, perPage: 10, totalItems: 0, totalPages: 1 };
    let currentStats = { fileCount: 0, totalSize: 0, latestModified: 0 };
    let activeUploadItems = [];
    let activeUploadRows = new Map();
    let localUploadBatch = null;
    let currentRequests = new Map();
    let dragDepth = 0;
    const clientId = getClientId();

    function getClientId() {
      const key = "lan-file-client-id";
      let value = localStorage.getItem(key);
      if (!value) {
        value = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        localStorage.setItem(key, value);
      }
      return value;
    }

    function formatBytes(value) {
      if (value === 0) return "0 B";
      const units = ["B", "KB", "MB", "GB", "TB"];
      const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
      const number = value / Math.pow(1024, index);
      return `${number.toFixed(number >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
    }

    function formatDate(timestamp) {
      return new Date(timestamp * 1000).toLocaleString();
    }

    function formatShortDate(timestamp) {
      if (!timestamp) return "-";
      return new Date(timestamp * 1000).toLocaleDateString(undefined, { month: "2-digit", day: "2-digit" });
    }

    function plural(count, singular, pluralForm) {
      return count === 1 ? singular : pluralForm;
    }

    function fileUploadPath(file) {
      return normalizeRelativePath(file.webkitRelativePath || file.relativePath || file.name);
    }

    function normalizeRelativePath(path) {
      return String(path || "").replace(/\\\\/g, "/").replace(/^\\/+/, "");
    }

    function uploadUrl(file) {
      const params = new URLSearchParams({
        path: fileUploadPath(file),
        size: String(file.size),
        mtime: String(file.lastModified || 0),
        client: clientId,
      });
      return `/api/upload?${params.toString()}`;
    }

    function uploadStatusUrl(file) {
      const params = new URLSearchParams({
        path: fileUploadPath(file),
        size: String(file.size),
        mtime: String(file.lastModified || 0),
        client: clientId,
      });
      return `/api/upload/status?${params.toString()}`;
    }

    function cancelUrl(upload) {
      const params = new URLSearchParams({
        path: upload.path || upload.name,
        size: String(upload.size),
        mtime: String(upload.modified || 0),
        client: clientId,
      });
      return `/api/upload/cancel?${params.toString()}`;
    }

    function itemDeleteUrl(path) {
      const params = new URLSearchParams({ path });
      return `/api/files?${params.toString()}`;
    }

    function folderZipName(path) {
      const parts = normalizeRelativePath(path).split("/").filter(Boolean);
      return `${parts.pop() || "shared"}.zip`;
    }

    function encodedRelativePath(path) {
      return normalizeRelativePath(path).split("/").filter(Boolean).map(encodeURIComponent).join("/");
    }

    function folderDownloadUrl(path) {
      const encoded = encodedRelativePath(path);
      return encoded ? `/folders/${encoded}` : "/folders/";
    }

    function setSelectedFiles(files) {
      selectedFiles = Array.from(files || []);
      renderSelection();
    }

    function renderSelection() {
      const total = selectedFiles.reduce((sum, file) => sum + file.size, 0);
      selectionSummary.textContent = selectedFiles.length
        ? `${selectedFiles.length} ${plural(selectedFiles.length, "file", "files")} / ${formatBytes(total)}`
        : "No files selected";
      uploadBtn.disabled = selectedFiles.length === 0;
      clearBtn.disabled = selectedFiles.length === 0;
      selectionList.innerHTML = "";

      for (const file of selectedFiles.slice(0, 4)) {
        const item = document.createElement("div");
        item.className = "selection-item";
        item.innerHTML = `
          <div>
            <div class="file-name"></div>
            <div class="meta"></div>
          </div>
          <span class="meta">Ready</span>
        `;
        item.querySelector(".file-name").textContent = fileUploadPath(file);
        item.querySelector(".meta").textContent = formatBytes(file.size);
        selectionList.appendChild(item);
      }

      if (selectedFiles.length > 4) {
        const item = document.createElement("div");
        item.className = "selection-item";
        item.innerHTML = `<div class="meta"></div><span class="meta">Selected</span>`;
        item.querySelector(".meta").textContent = `${selectedFiles.length - 4} more ${plural(selectedFiles.length - 4, "file", "files")}`;
        selectionList.appendChild(item);
      }
    }

    function uploadPercent(offset, size) {
      return size === 0 ? 100 : Math.min(100, Math.floor((offset / size) * 100));
    }

    function beginLocalUploadBatch(files) {
      localUploadBatch = {
        startedAt: Date.now() / 1000,
        items: files.map((file) => ({
          file,
          offset: 0,
          note: "Waiting",
          state: "waiting",
        })),
      };
      renderLocalUploadQueue();
    }

    function updateLocalUploadItem(index, offset, note, state = "active") {
      if (!localUploadBatch || !localUploadBatch.items[index]) return;
      const item = localUploadBatch.items[index];
      item.offset = Math.min(offset, item.file.size);
      item.note = note;
      item.state = state;
      renderLocalUploadQueue();
    }

    function renderLocalUploadQueue() {
      uploadList.innerHTML = "";
      if (!localUploadBatch) return;

      const items = localUploadBatch.items;
      const incomplete = items.filter((item) => item.state !== "complete" && uploadPercent(item.offset, item.file.size) < 100);
      const leading = incomplete.slice().sort((a, b) => {
        const percentB = uploadPercent(b.offset, b.file.size);
        const percentA = uploadPercent(a.offset, a.file.size);
        return percentB - percentA;
      })[0];

      if (leading) {
        uploadList.appendChild(createLocalUploadRow(leading));
      }

      const completed = items.filter((item) => item.state === "complete").length;
      const failed = items.filter((item) => item.state === "failed").length;
      if (items.length > 1 || !leading) {
        const folded = leading ? items.length - 1 : 0;
        const item = document.createElement("div");
        item.className = "selection-item";
        item.innerHTML = `
          <div>
            <div class="file-name"></div>
            <div class="meta"></div>
          </div>
          <span class="badge"></span>
        `;
        item.querySelector(".file-name").textContent = leading
          ? `${folded} folded ${plural(folded, "file", "files")}`
          : "Upload batch complete";
        item.querySelector(".meta").textContent = `${formatElapsed(localUploadBatch.startedAt)} elapsed - ${items.length} total files, ${completed} uploaded${failed ? `, ${failed} failed` : ""}`;
        item.querySelector(".badge").textContent = leading ? "Summary" : "Done";
        uploadList.appendChild(item);
      }
    }

    function createLocalUploadRow(item) {
      const file = item.file;
      const percent = uploadPercent(item.offset, file.size);
      const row = document.createElement("div");
      row.className = "upload-item";
      row.classList.toggle("complete", item.state === "complete");
      row.classList.toggle("failed", item.state === "failed");
      row.innerHTML = `
        <div>
          <div class="upload-name"></div>
          <div class="progress-track"><div class="progress-bar"></div></div>
          <div class="upload-note"></div>
        </div>
        <div class="upload-percent"></div>
      `;
      row.querySelector(".upload-name").textContent = fileUploadPath(file);
      row.querySelector(".progress-bar").style.width = `${percent}%`;
      row.querySelector(".upload-percent").textContent = `${percent}%`;
      row.querySelector(".upload-note").textContent = `${formatBytes(item.offset)} / ${formatBytes(file.size)} - ${item.note}`;
      row.querySelector(".upload-note").className = item.state === "failed"
        ? "upload-note status-error"
        : item.state === "complete"
          ? "upload-note status-ok"
          : "upload-note";
      return row;
    }

    function renderActiveUploads(uploads = activeUploadItems) {
      activeUploadItems = uploads;
      activeUploadRows = new Map();
      activeUploads.innerHTML = "";
      const inProgressUploads = uploads.filter((upload) => upload.size === 0 ? upload.offset === 0 : uploadPercent(upload.offset, upload.size) < 100);

      if (!inProgressUploads.length) {
        const empty = document.createElement("div");
        empty.className = "selection-item";
        empty.innerHTML = `<div class="meta">No active uploads</div>`;
        activeUploads.appendChild(empty);
        return;
      }

      const leading = inProgressUploads.slice().sort((a, b) => {
        const percentA = uploadPercent(a.offset, a.size);
        const percentB = uploadPercent(b.offset, b.size);
        if (percentB !== percentA) return percentB - percentA;
        return (b.updatedAt || 0) - (a.updatedAt || 0);
      })[0];
      const folded = inProgressUploads.filter((upload) => upload.id !== leading.id);

      renderActiveUploadRow(leading);
      if (folded.length) {
        const startedAt = Math.min(...inProgressUploads.map((upload) => upload.startedAt || Date.now() / 1000));
        const uploaded = uploads.filter((upload) => upload.size > 0 && uploadPercent(upload.offset, upload.size) >= 100).length;
        const totalBytes = inProgressUploads.reduce((sum, upload) => sum + (upload.size || 0), 0);
        const doneBytes = inProgressUploads.reduce((sum, upload) => sum + Math.min(upload.offset || 0, upload.size || 0), 0);
        const summaryRow = document.createElement("div");
        summaryRow.className = "selection-item";
        summaryRow.innerHTML = `
          <div>
            <div class="file-name"></div>
            <div class="meta"></div>
          </div>
          <span class="badge"></span>
        `;
        summaryRow.querySelector(".file-name").textContent = `${folded.length} more active ${plural(folded.length, "upload", "uploads")}`;
        summaryRow.querySelector(".meta").textContent = `${formatElapsed(startedAt)} elapsed - ${inProgressUploads.length} total files, ${uploaded} complete - ${formatBytes(doneBytes)} / ${formatBytes(totalBytes)}`;
        summaryRow.querySelector(".badge").textContent = "Folded";
        activeUploads.appendChild(summaryRow);
      }
    }

    function renderActiveUploadRow(upload) {
      const mine = upload.clientId === clientId;
      const row = document.createElement("div");
      row.className = mine ? "active-upload-item" : "active-upload-item other";
      row.dataset.uploadId = upload.id;
      row.innerHTML = `
        <div>
          <div class="upload-name"></div>
          <div class="progress-track"><div class="progress-bar"></div></div>
          <div class="upload-note"></div>
        </div>
        <div class="actions">
          <span class="badge"></span>
          <button class="cancel-upload" type="button">Cancel</button>
        </div>
      `;
      row.querySelector(".upload-name").textContent = upload.path || upload.name;
      const percent = uploadPercent(upload.offset, upload.size);
      row.querySelector(".progress-bar").style.width = `${percent}%`;
      row.querySelector(".upload-note").textContent = `${formatBytes(upload.offset)} / ${formatBytes(upload.size)}`;
      const badge = row.querySelector(".badge");
      badge.textContent = mine ? "This client" : "Other client";
      badge.classList.toggle("other", !mine);
      const cancel = row.querySelector(".cancel-upload");
      cancel.disabled = !mine;
      cancel.title = mine ? "Cancel this upload" : "Only the uploading client can cancel this";
      if (mine) {
        cancel.addEventListener("click", () => cancelUpload(upload));
      }
      activeUploads.appendChild(row);
      activeUploadRows.set(upload.id, row);
    }

    function formatElapsed(startedAt) {
      if (!startedAt) return "0s";
      const seconds = Math.max(0, Math.floor(Date.now() / 1000 - startedAt));
      if (seconds < 60) return `${seconds}s`;
      const minutes = Math.floor(seconds / 60);
      if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
      return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
    }

    async function cancelUpload(upload) {
      const controller = currentRequests.get(upload.id);
      if (controller) {
        controller.abort();
      }
      await fetch(cancelUrl(upload), { method: "POST" }).catch(() => {});
      await loadFiles().catch(() => {});
    }

    function renderStats(stats, pagination) {
      const totalFiles = stats.fileCount || 0;
      fileCount.textContent = String(totalFiles);
      totalSize.textContent = formatBytes(stats.totalSize || 0);
      latestTime.textContent = formatShortDate(stats.latestModified || 0);
      summary.textContent = totalFiles
        ? `${totalFiles} ${plural(totalFiles, "file", "files")} / ${formatBytes(stats.totalSize || 0)}`
        : "No files yet";
      if (pagination && pagination.totalItems && fileSearch.value.trim()) {
        summary.textContent += ` - ${pagination.totalItems} matching ${plural(pagination.totalItems, "item", "items")}`;
      }
    }

    function renderFiles() {
      const folders = allFolders;
      const files = allFiles;
      currentPathLabel.textContent = currentPath ? `/${currentPath}` : "/";
      downloadFolderBtn.href = folderDownloadUrl(currentPath);
      downloadFolderBtn.download = folderZipName(currentPath);

      if (!folders.length && !files.length && !currentPath) {
        filesSection.innerHTML = `<div class="empty">${currentPagination.totalItems ? "No matching items" : "No files yet"}</div>${paginationMarkup()}`;
        bindPaginationControls();
        return;
      }
      if (!folders.length && !files.length && currentPath) {
        filesSection.innerHTML = `<div class="empty">${currentPagination.totalItems ? "No matching items" : "This folder is empty"}</div>${paginationMarkup()}`;
        bindPaginationControls();
        return;
      }

      filesSection.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Size</th>
              <th>Modified</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
        ${paginationMarkup()}
      `;
      const tbody = filesSection.querySelector("tbody");
      if (currentPath) {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td data-label="Name">
            <div class="name-cell">
              <span class="file-mark" aria-hidden="true">D</span>
              <a class="file-link" href="#">..</a>
            </div>
          </td>
          <td data-label="Size" class="size">Folder</td>
          <td data-label="Modified"></td>
          <td data-label="Actions"></td>
        `;
        row.querySelector(".file-link").addEventListener("click", (event) => {
          event.preventDefault();
          loadFiles(parentPath(currentPath), 1).catch(showFileError);
        });
        tbody.appendChild(row);
      }
      for (const folder of folders) {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td data-label="Name">
            <div class="name-cell">
              <span class="file-mark" aria-hidden="true">D</span>
              <a class="file-link" href="#"></a>
            </div>
          </td>
          <td data-label="Size" class="size">Folder</td>
          <td data-label="Modified"></td>
          <td data-label="Actions">
            <div class="row-actions">
              <a class="download-link"><span aria-hidden="true">v</span><span>ZIP</span></a>
              <button class="delete-button" type="button">Delete</button>
            </div>
          </td>
        `;
        const folderLink = row.querySelector(".file-link");
        folderLink.textContent = folder.name;
        folderLink.addEventListener("click", (event) => {
          event.preventDefault();
          loadFiles(folder.path, 1).catch(showFileError);
        });
        row.children[2].textContent = formatDate(folder.modified);
        const downloadLink = row.querySelector(".download-link");
        downloadLink.href = folder.downloadUrl || folderDownloadUrl(folder.path);
        downloadLink.download = folderZipName(folder.path);
        row.querySelector(".delete-button").addEventListener("click", () => deleteItem(folder.path, folder.name, "folder"));
        tbody.appendChild(row);
      }
      for (const file of files) {
        const row = document.createElement("tr");
        const href = file.downloadUrl;
        row.innerHTML = `
          <td data-label="Name">
            <div class="name-cell">
              <span class="file-mark" aria-hidden="true">F</span>
              <a class="file-link"></a>
            </div>
          </td>
          <td data-label="Size" class="size"></td>
          <td data-label="Modified"></td>
          <td data-label="Actions">
            <div class="row-actions">
              <a class="download-link"><span aria-hidden="true">v</span><span>Download</span></a>
              <button class="delete-button" type="button">Delete</button>
            </div>
          </td>
        `;
        const nameLink = row.querySelector(".file-link");
        nameLink.href = href;
        nameLink.textContent = file.name;
        nameLink.download = file.name;
        row.querySelector(".size").textContent = formatBytes(file.size);
        row.children[2].textContent = formatDate(file.modified);
        const downloadLink = row.querySelector(".download-link");
        downloadLink.href = href;
        downloadLink.download = file.name;
        row.querySelector(".delete-button").addEventListener("click", () => deleteItem(file.path, file.name, "file"));
        tbody.appendChild(row);
      }
      bindPaginationControls();
    }

    function paginationMarkup() {
      const totalPages = currentPagination.totalPages || 1;
      const page = currentPagination.page || 1;
      const totalItems = currentPagination.totalItems || 0;
      const from = totalItems ? (page - 1) * currentPagination.perPage + 1 : 0;
      const to = totalItems ? Math.min(page * currentPagination.perPage, totalItems) : 0;
      return `
        <div class="pagination">
          <div class="page-status">${totalItems ? `${from}-${to} of ${totalItems} items` : "0 items"} - Page ${page} of ${totalPages}</div>
          <div class="actions">
            <button id="prevPageBtn" type="button" ${page <= 1 ? "disabled" : ""}>Previous</button>
            <button id="nextPageBtn" type="button" ${page >= totalPages ? "disabled" : ""}>Next</button>
          </div>
        </div>
      `;
    }

    function bindPaginationControls() {
      const previous = document.querySelector("#prevPageBtn");
      const next = document.querySelector("#nextPageBtn");
      if (previous) {
        previous.addEventListener("click", () => loadFiles(currentPath, currentPage - 1).catch(showFileError));
      }
      if (next) {
        next.addEventListener("click", () => loadFiles(currentPath, currentPage + 1).catch(showFileError));
      }
    }

    async function deleteItem(path, name, type) {
      const confirmed = window.confirm(`Delete ${type} "${name}"?`);
      if (!confirmed) return;
      const response = await fetch(itemDeleteUrl(path), { method: "DELETE" });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        summary.textContent = data.error || `Delete failed: ${response.status}`;
        return;
      }
      await loadFiles().catch(showFileError);
    }

    function parentPath(path) {
      const parts = normalizeRelativePath(path).split("/").filter(Boolean);
      parts.pop();
      return parts.join("/");
    }

    function showFileError(error) {
      summary.textContent = error.message || "File list failed";
    }

    async function loadFiles(path = currentPath, page = currentPage) {
      summary.textContent = "Loading files...";
      const params = new URLSearchParams({
        path,
        page: String(page),
        per_page: "10",
        search: fileSearch.value.trim(),
      });
      const response = await fetch(`/api/files?${params.toString()}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`File list failed: ${response.status}`);
      const data = await response.json();
      currentPath = data.path || "";
      currentPagination = data.pagination || { page: 1, perPage: 10, totalItems: 0, totalPages: 1 };
      currentPage = currentPagination.page || 1;
      currentStats = data.stats || { fileCount: 0, totalSize: 0, latestModified: 0 };
      allFolders = data.folders || [];
      allFiles = data.files || [];
      renderStats(currentStats, currentPagination);
      renderFiles();
    }

    function connectWebSocket() {
      const scheme = location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${scheme}://${location.host}/ws?client=${encodeURIComponent(clientId)}`);
      socket.addEventListener("message", (event) => {
        let message;
        try {
          message = JSON.parse(event.data);
        } catch {
          return;
        }
        if (message.type === "uploads") {
          renderActiveUploads(message.uploads || []);
        } else if (message.type === "filesChanged") {
          loadFiles().catch(showFileError);
        }
      });
      socket.addEventListener("close", () => {
        window.setTimeout(connectWebSocket, 1200);
      });
    }

    async function uploadFile(file, index) {
      let offset = 0;
      let uploadId = "";
      try {
        const statusResponse = await fetch(uploadStatusUrl(file), { cache: "no-store" });
        if (!statusResponse.ok) throw new Error(await statusResponse.text());
        const status = await statusResponse.json();
        uploadId = status.uploadId || "";
        offset = Math.min(status.offset || 0, file.size);
        updateLocalUploadItem(index, offset, offset ? "Resuming" : "Starting");

        if (file.size === 0) {
          const controller = new AbortController();
          if (uploadId) currentRequests.set(uploadId, controller);
          const response = await fetch(uploadUrl(file), {
            method: "PUT",
            headers: { "Upload-Offset": "0" },
            body: new Blob([]),
            signal: controller.signal,
          });
          if (uploadId) currentRequests.delete(uploadId);
          if (!response.ok) throw new Error(await response.text());
          updateLocalUploadItem(index, 0, "Complete", "complete");
          return;
        }

        while (offset < file.size) {
          const nextOffset = Math.min(offset + CHUNK_SIZE, file.size);
          const chunk = file.slice(offset, nextOffset);
          const controller = new AbortController();
          if (uploadId) currentRequests.set(uploadId, controller);
          const response = await fetch(uploadUrl(file), {
            method: "PUT",
            headers: { "Upload-Offset": String(offset) },
            body: chunk,
            signal: controller.signal,
          });
          if (uploadId) currentRequests.delete(uploadId);
          const data = await response.json().catch(() => ({}));

          if (response.status === 409 && typeof data.offset === "number") {
            offset = Math.min(data.offset, file.size);
            updateLocalUploadItem(index, offset, "Syncing offset");
            continue;
          }
          if (!response.ok) {
            throw new Error(data.error || `Upload failed: ${response.status}`);
          }

          offset = data.offset;
          uploadId = data.uploadId || uploadId;
          updateLocalUploadItem(index, offset, data.complete ? "Complete" : "Uploading", data.complete ? "complete" : "active");
        }
      } catch (error) {
        const message = error.name === "AbortError" ? "Cancelled" : (error.message || "Upload failed");
        updateLocalUploadItem(index, offset, message, "failed");
      } finally {
        if (uploadId) currentRequests.delete(uploadId);
      }
    }

    async function uploadSelectedFiles() {
      if (!selectedFiles.length) return;
      uploadBtn.disabled = true;
      clearBtn.disabled = true;
      const files = selectedFiles.slice();
      beginLocalUploadBatch(files);
      try {
        for (const [index, file] of files.entries()) {
          await uploadFile(file, index);
        }
        fileInput.value = "";
        setSelectedFiles([]);
        await loadFiles();
      } finally {
        uploadBtn.disabled = selectedFiles.length === 0;
        clearBtn.disabled = selectedFiles.length === 0;
      }
    }

    fileInput.addEventListener("change", () => setSelectedFiles(fileInput.files));
    folderInput.addEventListener("change", () => setSelectedFiles(folderInput.files));
    clearBtn.addEventListener("click", () => {
      fileInput.value = "";
      folderInput.value = "";
      setSelectedFiles([]);
    });
    uploadBtn.addEventListener("click", uploadSelectedFiles);
    refreshBtn.addEventListener("click", () => loadFiles(currentPath, currentPage).catch((error) => {
      summary.textContent = error.message || "Refresh failed";
    }));
    fileSearch.addEventListener("input", () => loadFiles(currentPath, 1).catch(showFileError));

    window.addEventListener("dragenter", (event) => {
      event.preventDefault();
      dragDepth += 1;
      document.body.classList.add("dragging");
    });
    window.addEventListener("dragover", (event) => event.preventDefault());
    window.addEventListener("dragleave", () => {
      dragDepth = Math.max(0, dragDepth - 1);
      if (!dragDepth) document.body.classList.remove("dragging");
    });
    window.addEventListener("drop", (event) => {
      event.preventDefault();
      dragDepth = 0;
      document.body.classList.remove("dragging");
      if (event.dataTransfer && event.dataTransfer.files.length) {
        setSelectedFiles(event.dataTransfer.files);
      }
    });
    dropZone.addEventListener("dblclick", () => fileInput.click());

    renderSelection();
    renderActiveUploads();
    connectWebSocket();
    loadFiles().catch(showFileError);
  </script>
</body>
</html>
"""
