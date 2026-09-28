from flask import Flask, render_template, request, redirect, session, send_from_directory, abort, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from random import random, randrange
import os

# Changeable variables
REQUESTS_PER_MIN = 60


# Static Variables
PORT=1234
PASSWORD_HASH=generate_password_hash("changeme")
SECRET_KEY=str(random()+random()-random()+randrange(1,999999))
MEDIA_ROOT=Path("media").resolve()

app=Flask(__name__)
app.secret_key=SECRET_KEY
app.config["PERMANENT_SESSION_LIFETIME"]=timedelta(hours=24)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[f"{REQUESTS_PER_MIN} per minute"],
    storage_uri="memory://")

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
def ratelimit(error):
    return render_template("429.html", rqm=REQUESTS_PER_MIN, ip=request.remote_addr)

@app.errorhandler(404)
def notfound(error):
    return render_template("404.html")

if __name__=='__main__':
    app.run(host='0.0.0.0',port=PORT,threaded=True)
