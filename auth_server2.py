#!/usr/bin/env python3
# auth_server.py
import http.server
import socketserver
import urllib.parse
import os
import threading
import ssl

# =====================
# CONFIG
# =====================
HTTP_PORT = 80
HTTPS_PORT = 443

DOMAIN = "harmonyinnovationrobotics.duckdns.org"  # <-- CHANGE THIS

CERT_FILE = f"/etc/letsencrypt/live/{DOMAIN}/fullchain.pem"
KEY_FILE = f"/etc/letsencrypt/live/{DOMAIN}/privkey.pem"

ALLOWED_FILE = "allowed_ips.txt"
PASSWORD = os.environ.get("SITE_PASSWORD", "testpass")
LOCK = threading.Lock()

# =====================
# IP ALLOW LIST
# =====================
def load_allowed():
    if not os.path.exists(ALLOWED_FILE):
        return set()
    with open(ALLOWED_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def add_allowed(ip):
    with LOCK:
        allowed = load_allowed()
        if ip in allowed:
            return
        allowed.add(ip)
        with open(ALLOWED_FILE, "a") as f:
            f.write(ip + "\n")

# =====================
# HTTPS AUTH HANDLER
# =====================
class AuthHandler(http.server.SimpleHTTPRequestHandler):

    def client_ip(self):
        xff = self.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        return self.client_address[0]

    def is_allowed_ip(self, ip):
        return ip in load_allowed()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/login":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = urllib.parse.parse_qs(body)
            password = data.get("password", [""])[0]
            client = self.client_ip()

            if password == PASSWORD:
                add_allowed(client)
                self.send_response(302)
                self.send_header("Location", "/media/")
                self.end_headers()
            else:
                self.send_response(302)
                self.send_header("Location", "/login.html?login=failed")
                self.end_headers()
        else:
            super().do_POST()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        p = parsed.path

        # /login -> /login.html
        if p == "/login":
            self.send_response(301)
            self.send_header("Location", "/login.html")
            self.end_headers()
            return

        # protect /media
        if p == "/media" or p.startswith("/media/"):
            client = self.client_ip()
            if not self.is_allowed_ip(client):
                self.send_response(302)
                self.send_header("Location", "/index.html")
                self.end_headers()
                return

        super().do_GET()

# =====================
# HTTP -> HTTPS REDIRECT
# =====================
class RedirectHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        host = self.headers.get("Host", DOMAIN)
        self.send_response(301)
        self.send_header("Location", f"https://{host}{self.path}")
        self.end_headers()

    def log_message(self, format, *args):
        return  # silence logs

# =====================
# SERVERS
# =====================
def run_https():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    httpd = socketserver.TCPServer(("", HTTPS_PORT), AuthHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    print(f"[HTTPS] Serving on port {HTTPS_PORT}")
    httpd.serve_forever()

def run_http_redirect():
    httpd = socketserver.TCPServer(("", HTTP_PORT), RedirectHandler)
    print(f"[HTTP] Redirecting port {HTTP_PORT} -> HTTPS")
    httpd.serve_forever()

# =====================
# MAIN
# =====================
if __name__ == "__main__":
    threading.Thread(target=run_http_redirect, daemon=True).start()
    run_https()
