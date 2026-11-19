from pathlib import Path
from flask import request,jsonify,send_from_directory
from delete_core import prepare,remove_report,cleanup

def install(app,db,protected,error,ROOT):
    store=Path(app.config['DATA_DIR'])/'photos'
    if store.is_symlink():raise RuntimeError('A fotómappa nem lehet szimbolikus link a törlési modulban.')
    prepare(db)
    cleanup(db,store,app.logger)
    @app.get('/delete-admin.js')
    def delete_script():return send_from_directory(ROOT,'delete-admin.js')
    @app.post('/api/delete-report')
    @protected(owner=True)
    def delete_report(u):
        d=request.get_json()
        rid=d.get('id')
        if type(rid) is not int or not 0<rid<2**63 or d.get('confirmation')!=str(rid):
            return error('A törléshez adja meg pontosan a bejelentés azonosítóját.')
        try:
            if not remove_report(db,u['id'],rid,store):return error('A bejelentés már nem található.',404)
        except ValueError as exc:return error(str(exc),409)
        except Exception:
            app.logger.exception('Bejelentés törlése sikertelen.')
            return error('Nem sikerült törölni. Frissítse a listát az állapot ellenőrzéséhez.',500)
        cleanup(db,store,app.logger)
        c=db()
        try:pending=c.execute('SELECT COUNT(*) FROM report_file_cleanup WHERE report_id=?',(rid,)).fetchone()[0]
        finally:c.close()
        return jsonify(ok=True,id=rid,pending_files=pending)
