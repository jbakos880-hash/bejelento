import re

def prepare(db):
    c=db()
    try:
        with c:
            c.execute('BEGIN IMMEDIATE')
            sql=c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='reports'").fetchone()[0]
            if 'AUTOINCREMENT' not in sql.upper():
                if not re.search(r'\bid\s+INTEGER\s+PRIMARY\s+KEY\b',sql,re.I):
                    raise RuntimeError('Nem támogatott reports séma; migráció leállítva.')
                if c.execute("SELECT 1 FROM sqlite_master WHERE name='reports_delete_migration'").fetchone():
                    raise RuntimeError('Foglalt migrációs táblanév.')
                extras=[r[0] for r in c.execute("SELECT sql FROM sqlite_master WHERE tbl_name='reports' AND type IN ('index','trigger') AND sql IS NOT NULL")]
                new=re.sub(r'^(CREATE\s+TABLE\s+)(?:"reports"|`reports`|\[reports\]|reports)(?=\s*\()',r'\1reports_delete_migration',sql,count=1,flags=re.I)
                new=re.sub(r'\bid\s+INTEGER\s+PRIMARY\s+KEY\b','id INTEGER PRIMARY KEY AUTOINCREMENT',new,count=1,flags=re.I)
                if new==sql or 'reports_delete_migration' not in new:raise RuntimeError('Nem támogatott tábladefiníció.')
                c.execute(new)
                columns=','.join('"'+r[1].replace('"','""')+'"' for r in c.execute('PRAGMA table_info(reports)'))
                c.execute('INSERT INTO reports_delete_migration('+columns+') SELECT '+columns+' FROM reports')
                c.execute('DROP TABLE reports')
                c.execute('ALTER TABLE reports_delete_migration RENAME TO reports')
                for statement in extras:c.execute(statement)
            c.execute('CREATE TABLE IF NOT EXISTS report_file_cleanup(filename TEXT PRIMARY KEY,report_id INTEGER NOT NULL)')
    finally:c.close()

def remove_report(db,actor,rid,store):
    c=db()
    try:
        with c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT id FROM reports WHERE id=?',(rid,)).fetchone():return False
            names=[r[0] for r in c.execute('SELECT filename FROM photos WHERE report_id=?',(rid,))]
            if any(not re.fullmatch(r'[0-9a-f]{48}\.jpg',name) for name in names):
                raise ValueError('Nem támogatott képfájlnév; törlés leállítva.')
            for name in names:
                if (store/name).is_symlink():raise ValueError('Nem támogatott képfájl; törlés leállítva.')
                c.execute('INSERT INTO report_file_cleanup(filename,report_id) VALUES(?,?)',(name,rid))
            c.execute('DELETE FROM photos WHERE report_id=?',(rid,))
            c.execute('DELETE FROM reports WHERE id=?',(rid,))
            c.execute('INSERT INTO audit(actor,action,target) VALUES(?,?,?)',(actor,'delete-report',rid))
        return True
    finally:c.close()

def cleanup(db,store,logger):
    c=db()
    try:
        rows=c.execute('SELECT filename FROM report_file_cleanup').fetchall()
        for row in rows:
            name=row[0]
            if not re.fullmatch(r'[0-9a-f]{48}\.jpg',name):continue
            try:
                path=store/name
                if path.is_symlink():raise OSError('Szimbolikus link nem törölhető automatikusan.')
                path.unlink(missing_ok=True)
                with c:c.execute('DELETE FROM report_file_cleanup WHERE filename=?',(name,))
            except OSError:logger.warning('Bejelentési képfájl törlése függőben; újrapróbálás a következő törléskor vagy szerverindításkor.')
    finally:c.close()
