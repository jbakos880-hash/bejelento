from flask import send_from_directory

def install(app,ROOT):
    @app.get('/admin-filters.js')
    def admin_filters_script():return send_from_directory(ROOT,'admin-filters.js')
