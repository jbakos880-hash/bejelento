from flask import request, redirect, send_from_directory, jsonify

def install(app, db, current, error, ROOT):
    @app.before_request
    def admin_canonical():
        if request.path == '/admin' and request.method == 'GET':
            return redirect('/admin/', code=302)
    @app.get('/admin/')
    def admin_home():
        return send_from_directory(ROOT, 'admin.html')
    @app.get('/admin/manifest.webmanifest')
    def admin_manifest():
        return send_from_directory(ROOT/'admin_pwa', 'manifest.webmanifest', mimetype='application/manifest+json')
    @app.get('/admin/sw.js')
    def admin_worker():
        return send_from_directory(ROOT/'admin_pwa', 'sw.js', mimetype='text/javascript')
    @app.get('/admin/pwa/<name>')
    def admin_asset(name):
        if name not in {'admin.js','icon-192.png','icon-512.png','apple-touch-icon.png','offline.html'}:
            return error('Nem található.',404)
        return send_from_directory(ROOT/'admin_pwa',name)
    @app.get('/api/admin-notifications')
    def admin_notifications():
        if not current():return error('Belépés szükséges.',401)
        raw=request.args.get('after')
        if raw is not None and (not raw.isascii() or not raw.isdigit() or len(raw)>18):
            return error('Hibás azonosító.')
        with db() as c:
            latest=c.execute('SELECT COALESCE(MAX(id),0) FROM reports').fetchone()[0]
            count=0 if raw is None else c.execute('SELECT COUNT(*) FROM reports WHERE id>? AND id<=?',(int(raw),latest)).fetchone()[0]
        return jsonify(latest=latest,count=count)
