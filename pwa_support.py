from flask import send_from_directory

def install(app,ROOT):
    @app.get('/manifest.webmanifest')
    def pwa_manifest():return send_from_directory(ROOT/'pwa','manifest.webmanifest',mimetype='application/manifest+json')
    @app.get('/sw.js')
    def pwa_worker():
        r=send_from_directory(ROOT/'pwa','sw.js',mimetype='text/javascript');r.headers['Service-Worker-Allowed']='/';return r
    @app.get('/pwa/<path:name>')
    def pwa_assets(name):
        if name not in {'icon-192.png','icon-512.png','apple-touch-icon.png','offline.html','pwa.js'}:return {'error':'Nem található.'},404
        return send_from_directory(ROOT/'pwa',name)
