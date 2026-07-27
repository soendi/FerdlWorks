import os
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import tempfile
import shutil
from lib.logger import get_logger
from lib.database import get_db, DB_PATH

CLIENT_SECRETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class _RedirectHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        code = query.get("code", [None])[0]
        if code:
            self.server.auth_code = code
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Authentifizierung erfolgreich! Sie k\xf6nnen das Fenster schlie\xdfen.</h2></body></html>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Fehler bei der Authentifizierung.</h2></body></html>")

    def log_message(self, format, *args):
        pass


def _start_local_server(port=18080):
    server = HTTPServer(("127.0.0.1", port), _RedirectHandler)
    server.auth_code = None
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()
    return server


def _get_redirect_uri(port=18080):
    return f"http://127.0.0.1:{port}"


# ===================== GOOGLE DRIVE =====================

def gdrive_backup(settings):
    logger = get_logger()
    client_id = settings.get("gdrive_client_id", "")
    client_secret = settings.get("gdrive_client_secret", "")
    refresh_token = settings.get("gdrive_refresh_token", "")
    if not client_id or not client_secret:
        logger.info("Google Drive: Nicht konfiguriert")
        return False, "Google Drive nicht konfiguriert (Client-ID fehlt)"
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        return False, "google-api-python-client nicht installiert"

    try:
        if refresh_token:
            creds = Credentials.from_authorized_user_info({
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "token_uri": "https://oauth2.googleapis.com/token",
            })
        else:
            return False, "Nicht autorisiert. Bitte zuerst einrichten."
        service = build("drive", "v3", credentials=creds)
        folder_name = "FerdlWorks Backup"
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, spaces="drive").execute()
        items = results.get("files", [])
        if items:
            folder_id = items[0]["id"]
        else:
            folder_meta = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
            folder = service.files().create(body=folder_meta, fields="id").execute()
            folder_id = folder["id"]
        from datetime import datetime
        backup_name = f"FerdlWorks_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, backup_name)
        db = get_db()
        db.backup_to(temp_path)
        media = MediaFileUpload(temp_path, mimetype="application/octet-stream")
        service.files().create(body={"name": backup_name, "parents": [folder_id]},
                               media_body=media).execute()
        os.unlink(temp_path)
        logger.info(f"Google Drive Backup: {backup_name}")
        return True, f"Backup {backup_name} nach Google Drive hochgeladen."
    except Exception as ex:
        logger.error(f"Google Drive Fehler: {ex}")
        return False, f"Fehler: {ex}"


def gdrive_authorize():
    logger = get_logger()
    secrets_file = os.path.join(CLIENT_SECRETS_DIR, "gdrive_client_secret.json")
    if not os.path.exists(secrets_file):
        return False, "Bitte legen Sie gdrive_client_secret.json im data/-Ordner ab.\n\n" \
                       "Erstellen Sie ein OAuth2-Client-ID-Dokument unter:\n" \
                       "https://console.cloud.google.com/apis/credentials\n" \
                       "und speichern Sie es als gdrive_client_secret.json"
    try:
        with open(secrets_file) as f:
            secrets = json.load(f)
        client_id = secrets.get("installed", {}).get("client_id", "")
        project_id = secrets.get("installed", {}).get("project_id", "")
        auth_uri = secrets.get("installed", {}).get("auth_uri", "https://accounts.google.com/o/oauth2/auth")
        token_uri = secrets.get("installed", {}).get("token_uri", "https://oauth2.googleapis.com/token")
        client_secret = secrets.get("installed", {}).get("client_secret", "")
        redirect_uris = secrets.get("installed", {}).get("redirect_uris", [])
        port = 18080
        redirect_uri = _get_redirect_uri(port)
        auth_url = (f"{auth_uri}?client_id={client_id}&redirect_uri={redirect_uri}"
                    f"&scope=https://www.googleapis.com/auth/drive.file"
                    f"&response_type=code&access_type=offline&prompt=consent")
        server = _start_local_server(port)
        webbrowser.open(auth_url)
        server.handle_request()
        code = server.auth_code
        server.server_close()
        if not code:
            return False, "Autorisierung abgebrochen"
        import requests
        token_resp = requests.post(token_uri, data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }, timeout=30)
        token_data = token_resp.json()
        refresh_token = token_data.get("refresh_token", "")
        if not refresh_token:
            return False, f"Kein Refresh-Token erhalten: {token_data.get('error_description', '')}"
        db = get_db()
        db.settings_set_multi({
            "gdrive_client_id": client_id,
            "gdrive_client_secret": client_secret,
            "gdrive_refresh_token": refresh_token,
        })
        logger.info("Google Drive autorisiert")
        return True, "Google Drive erfolgreich autorisiert!"
    except Exception as ex:
        logger.error(f"Google Drive Autorisierung: {ex}")
        return False, f"Fehler: {ex}"


# ===================== MICROSOFT ONEDRIVE =====================

def onedrive_backup(settings):
    logger = get_logger()
    client_id = settings.get("onedrive_client_id", "")
    refresh_token = settings.get("onedrive_refresh_token", "")
    if not client_id or not refresh_token:
        return False, "OneDrive nicht konfiguriert"
    try:
        import msal
        import requests
    except ImportError:
        return False, "msal nicht installiert"
    try:
        app = msal.PublicClientApplication(client_id, authority="https://login.microsoftonline.com/common")
        result = app.acquire_token_by_refresh_token(refresh_token, scopes=["Files.ReadWrite"])
        if "access_token" not in result:
            return False, f"Token-Fehler: {result.get('error_description', '')}"
        access_token = result["access_token"]
        folder_name = "FerdlWorks Backup"
        from datetime import datetime
        backup_name = f"FerdlWorks_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, backup_name)
        db = get_db()
        db.backup_to(temp_path)
        headers = {"Authorization": f"Bearer {access_token}"}
        folder_url = "https://graph.microsoft.com/v1.0/me/drive/special/approot:/" + folder_name
        folder_resp = requests.get(folder_url, headers=headers, timeout=15)
        if folder_resp.status_code == 404:
            requests.post("https://graph.microsoft.com/v1.0/me/drive/special/approot/children",
                          headers={**headers, "Content-Type": "application/json"},
                          json={"name": folder_name, "folder": {}}, timeout=15)
        upload_url = f"https://graph.microsoft.com/v1.0/me/drive/special/approot:/{folder_name}/{backup_name}:/content"
        with open(temp_path, "rb") as f:
            requests.put(upload_url, headers=headers, data=f, timeout=60)
        os.unlink(temp_path)
        logger.info(f"OneDrive Backup: {backup_name}")
        return True, f"Backup {backup_name} nach OneDrive hochgeladen."
    except Exception as ex:
        logger.error(f"OneDrive Fehler: {ex}")
        return False, f"Fehler: {ex}"


def onedrive_authorize():
    logger = get_logger()
    secrets_file = os.path.join(CLIENT_SECRETS_DIR, "onedrive_client_id.json")
    if not os.path.exists(secrets_file):
        return False, "Bitte legen Sie onedrive_client_id.json im data/-Ordner ab.\n\n" \
                       "Erstellen Sie eine App-Registrierung unter:\n" \
                       "https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps\n" \
                       "{\"client_id\": \"...\"}\n" \
                       "als onedrive_client_id.json speichern."
    try:
        with open(secrets_file) as f:
            data = json.load(f)
        client_id = data.get("client_id", "")
        if not client_id:
            return False, "Keine Client-ID in onedrive_client_id.json"
        import msal
        app = msal.PublicClientApplication(client_id, authority="https://login.microsoftonline.com/common")
        port = 18081
        redirect_uri = _get_redirect_uri(port)
        auth_url = app.get_authorization_request_url(
            scopes=["Files.ReadWrite", "offline_access"],
            redirect_uri=redirect_uri,
        )
        server = _start_local_server(port)
        webbrowser.open(auth_url)
        server.handle_request()
        code = server.auth_code
        server.server_close()
        if not code:
            return False, "Autorisierung abgebrochen"
        result = app.acquire_token_by_authorization_code(code, scopes=["Files.ReadWrite", "offline_access"],
                                                          redirect_uri=redirect_uri)
        if "refresh_token" not in result:
            return False, f"Kein Refresh-Token: {result.get('error_description', '')}"
        db = get_db()
        db.settings_set_multi({
            "onedrive_client_id": client_id,
            "onedrive_refresh_token": result["refresh_token"],
        })
        logger.info("OneDrive autorisiert")
        return True, "OneDrive erfolgreich autorisiert!"
    except Exception as ex:
        logger.error(f"OneDrive Autorisierung: {ex}")
        return False, f"Fehler: {ex}"
