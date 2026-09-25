from flask import Flask, render_template, request, redirect, session, send_from_directory, abort, jsonify
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import os

PORT=1234
PASSWORD_HASH=generate_password_hash("changeme")
SECRET_KEY="replace-with-random-secret"
MEDIA_ROOT=Path("media").resolve()

app=Flask(__name__)
app.secret_key=SECRET_KEY
app.config["PERMANENT_SESSION_LIFETIME"]=timedelta(hours=24)

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

if __name__=='__main__':
    app.run(host='0.0.0.0',port=PORT,threaded=True)
