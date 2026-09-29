from flask import Flask, render_template, request, redirect, session, send_from_directory, abort, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_ipban import IpBan
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from random import random, randrange
from hashlib import sha256
import os

# Changeable variables
REQUESTS_PER_MIN = 60


# Static Variables
PORT=4321
PASSWORD_HASH=generate_password_hash("changeme")
MEDIA_ROOT=Path("media").resolve()
ip_ban = IpBan(ban_seconds=86400)

#Calculation for secret key
sc_value = str(random() + random() - random() + randrange(1,9999)).replace(".","").encode("utf-8")
sc_value = sha256(sc_value).hexdigest()
SECRET_KEY = sc_value


app=Flask(__name__)
app.secret_key=SECRET_KEY
app.config["PERMANENT_SESSION_LIFETIME"]=timedelta(hours=24)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[f"{REQUESTS_PER_MIN} per minute"],
    storage_uri="memory://")

ip_ban.init_app(app)


MEDIA_ROOT.mkdir(exist_ok=True)

@app.before_request
def refresh():
    if session.get("authenticated"):
        session.permanent=True
        session.modified=True

def auth():
    return session.get('authenticated') is True

def safe_path(sub=''):
    p=(MEDIA_ROOT/sub).resolve()
    if not str(p).startswith(str(MEDIA_ROOT)):
        abort(403)
    return p

@app.route('/')
def root():
    return redirect('/media') if auth() else redirect('/login')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        if check_password_hash(PASSWORD_HASH,request.form.get('password','')):
            session.clear();session['authenticated']=True;session.permanent=True
            return redirect('/media')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear();return redirect('/login')

@app.route('/api/list')
def listing():
    if not auth(): abort(401)
    sub=request.args.get('path','')
    p=safe_path(sub)
    out=[]
    for f in sorted(p.iterdir(), key=lambda x:(not x.is_dir(),x.name.lower())):
        out.append({'name':f.name,'dir':f.is_dir(),'size':f.stat().st_size})
    return jsonify(out)

@app.route('/media')
@limiter.limit("180 per minute", override_defaults=True)
def media():
    if not auth(): return redirect('/login')
    return render_template('media.html')

@app.route('/upload',methods=['POST'])
def upload():
    if not auth(): abort(401)
    sub=request.form.get('path','')
    p=safe_path(sub)
    file=request.files['file']
    file.save(p/secure_filename(file.filename))
    return '',204

@app.route('/mkdir',methods=['POST'])
def mkdir():
    if not auth(): abort(401)
    safe_path(request.form.get('path','')).mkdir(exist_ok=True)
    return '',204

@app.route('/download/<path:file>')
def download(file):
    if not auth(): abort(401)
    target=safe_path(file)
    return send_from_directory(target.parent,target.name,as_attachment=True)

@app.route('/file/<path:file>')
def file(file):
    if not auth(): abort(401)
    target=safe_path(file)
    return send_from_directory(target.parent,target.name)

@app.route("/ping")
def ping():
    return "PONG"

@app.route("/robots.txt")
def robots():
    return send_file('robots.txt', as_attachment=False)


# Error handlers
@app.errorhandler(429)
def ratelimit(e):
    ip = request.remote_addr
    ip_ban.add(ip=ip)
    ip_status = ip_ban.get_ip(ip)
    current_count = ip_status.get("count", 0) if ip_status else 0
    if current_count >= 5:
        ip_ban.block(ip, permanent=False)
        return render_template("ratelimit2.html", rqm=REQUESTS_PER_MIN), 429
    return render_template("ratelimit1.html", rqm=REQUESTS_PER_MIN, ip=request.remote_addr), 429

@app.errorhandler(404)
def notfound(e):
    return render_template("404.html")

if __name__=='__main__':
    app.run(host='0.0.0.0',port=PORT,threaded=True)
