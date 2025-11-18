#!/usr/bin/env python3
# auth_server.py
import http.server
import socketserver
import urllib.parse
import os
import threading

PORT = 80
ALLOWED_FILE = "allowed_ips.txt"
PASSWORD = os.environ.get("SITE_PASSWORD", "R0b0t1nTh3c1ub")  # <-- change password here if necessary
LOCK = threading.Lock()

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

class AuthHandler(http.server.SimpleHTTPRequestHandler):
    # Get client IP: prefer X-Forwarded-For if present (useful behind reverse proxy)
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
                # successful -> redirect to /media/
                self.send_response(302)
                self.send_header("Location", "/media/")
                self.end_headers()
            else:
                # failed -> redirect back to root (you can add query params for UI)
                self.send_response(302)
                self.send_header("Location", "/login.html?login=failed")
                self.end_headers()
        else:
            # fallback to normal behavior
            super().do_POST()

    def do_GET(self):
        # protect any path under /media
        parsed = urllib.parse.urlparse(self.path)
        p = parsed.path
        if p == "/media" or p.startswith("/media/"):
            client = self.client_ip()
            if not self.is_allowed_ip(client):
                # redirect to login page
                self.send_response(302)
                self.send_header("Location", "/index.html")
                self.end_headers()
                return
        # otherwise serve files normally
        super().do_GET()

if __name__ == "__main__":
    Handler = AuthHandler
    # serve the current working directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at port {PORT}. Media protected; allowed file: {ALLOWED_FILE}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down")
            httpd.server_close()
