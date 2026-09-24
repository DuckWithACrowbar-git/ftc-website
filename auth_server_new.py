#!/usr/bin/env python3
# auth_server_flask.py
import os
import threading
import http.server
import socketserver
from flask import Flask, request, redirect

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

# Initialize Flask, mapping static files to the current working directory 
# (mimicking SimpleHTTPRequestHandler file serving)
app = Flask(__name__, static_folder=".", static_url_path="")

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

def get_client_ip():
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr

# =====================
# REQUEST INTERCEPTOR (Protecting /media)
# =====================
@app.before_request
def protect_media():
    path = request.path
    if path == "/media" or path.startswith("/media/"):
        client = get_client_ip()
        if client not in load_allowed():
            return redirect("/index.html", code=302)

# =====================
# ROUTES
# =====================
@app.route("/login", methods=["GET", "POST"])
def login_route():
    if request.method == "POST":
        password = request.form.get("password", "")
        client = get_client_ip()

        if password == PASSWORD:
            add_allowed(client)
            return redirect("/media/", code=302)
        else:
            return redirect("/login.html?login=failed", code=302)
            
    # GET /login -> Redirect to /login.html (301)
    return redirect("/login.html", code=301)

# Note: Flask automatically handles all other static files (like /index.html, 
# /login.html, and media assets) through static_folder="."

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

def run_http_redirect():
    httpd = socketserver.TCPServer(("", HTTP_PORT), RedirectHandler)
    print(f"[HTTP] Redirecting port {HTTP_PORT} -> HTTPS")
    httpd.serve_forever()

# =====================
# MAIN
# =====================
if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Start port 80 HTTP redirect server in a background thread
    threading.Thread(target=run_http_redirect, daemon=True).start()
    
    print(f"[HTTPS] Serving Flask on port {HTTPS_PORT}")
    
    # Run the Flask development/production server with SSL context
    app.run(
        host="0.0.0.0", 
        port=HTTPS_PORT, 
        ssl_context=(CERT_FILE, KEY_FILE)
    )