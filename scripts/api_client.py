"""Small authenticated HTTP caller for local validation; never logs credentials."""
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]


class ApiClient:
    def __init__(self, base):
        self.base = base.rstrip("/")
        url = urlsplit(self.base)
        if url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
            raise ValueError("Use an origin without credentials, query or path.")
        if url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1"}):
            raise ValueError("Credentials require HTTPS except on this computer's loopback interface.")
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self.csrf = ""

    def request(self, path, fields=None):
        headers = {"Accept": "application/json"}
        if fields is not None:
            headers.update({"Content-Type": "application/json", "X-CSRF-Token": self.csrf})
        request = Request(self.base + path, data=json.dumps(fields).encode() if fields is not None else None, headers=headers)
        try:
            with self.opener.open(request, timeout=15) as response:
                return response.status, response.read()
        except HTTPError as response:
            return response.code, response.read()

    def login(self, account="technician", credentials_file=None):
        url = urlsplit(self.base)
        if credentials_file is None and url.hostname in {"localhost", "127.0.0.1"}:
            credentials_file = ROOT / f".env.accounts-{url.port or 80}.json"
        if credentials_file is None:
            raise SystemExit("Supply an explicit private credentials file for a shared HTTPS check.")
        path = Path(credentials_file)
        if os.name != "nt" and path.stat().st_mode & 0o077:
            raise SystemExit("Credentials file must be owner-readable only (chmod 600).")
        data = json.loads(path.read_text())
        if urlsplit(data["base_url"]).netloc != url.netloc:
            raise SystemExit("Credentials are bound to a different host/port. Refusing to send them.")
        identity = data[account]
        status, body = self.request("/api/auth/login", {"username": identity["username"], "password": identity["password"]})
        if status != 200:
            raise SystemExit(f"Sign-in failed (HTTP {status}). Check the private account settings; no values printed.")
        session = json.loads(body)
        if session["user"]["must_change_password"]:
            raise SystemExit("Choose the account's personal password in Aeris before using API validation.")
        self.csrf = session["csrf_token"]

    def logout(self):
        self.request("/api/auth/logout", {})
