CATEGORIES=['Úthiba, kátyú','Közvilágítás','Illegális hulladék','Zöldterület, fa','Közterületi berendezés','Egyéb probléma']
STATUSES=['Beérkezett','Folyamatban','Megoldva','Elutasítva']
class Conflict(Exception):pass

def prepare(db):
    c=db()
    try:
        with c:
            c.execute('BEGIN IMMEDIATE')
            cols={r[1] for r in c.execute('PRAGMA table_info(reports)')}
            for name,definition in [('public_summary',"TEXT NOT NULL DEFAULT ''"),('public_location',"TEXT NOT NULL DEFAULT ''"),('published','INTEGER NOT NULL DEFAULT 0'),('publication_version','INTEGER NOT NULL DEFAULT 0')]:
                if name not in cols:c.execute('ALTER TABLE reports ADD COLUMN '+name+' '+definition)
    finally:c.close()

def metadata(db,rid):
    c=db()
    try:
        row=c.execute('SELECT public_summary,public_location,published,publication_version FROM reports WHERE id=?',(rid,)).fetchone()
        return dict(row) if row else None
    finally:c.close()

def publish(db,actor,rid,version,action,summary='',location=''):
    if action not in ('publish','withdraw'):raise ValueError('Hibás művelet.')
    if type(version) is not int or version<0:raise ValueError('Hibás verzió.')
    if action=='publish':
        if not isinstance(summary,str) or not 10<=len(summary.strip())<=1500:raise ValueError('Az összefoglaló 10–1500 karakter legyen.')
        if not isinstance(location,str) or not 3<=len(location.strip())<=200:raise ValueError('A nyilvános helyszín 3–200 karakter legyen.')
    c=db()
    try:
        with c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT publication_version FROM reports WHERE id=?',(rid,)).fetchone()
            if not old:return None
            if old[0]!=version:raise Conflict('A közzétételi adatokat közben módosították. Töltse újra a közzétételi mezőket.')
            if action=='publish':
                c.execute('UPDATE reports SET public_summary=?,public_location=?,published=1,publication_version=publication_version+1 WHERE id=?',(summary.strip(),location.strip(),rid))
            else:c.execute('UPDATE reports SET published=0,publication_version=publication_version+1 WHERE id=?',(rid,))
            c.execute('INSERT INTO audit(actor,action,target) VALUES(?,?,?)',(actor,'publication:'+action,rid))
        return metadata(db,rid)
    finally:c.close()

def public_rows(db,category='',status='',before=None):
    if category and category not in CATEGORIES:raise ValueError('Hibás kategória.')
    if status and status not in STATUSES:raise ValueError('Hibás állapot.')
    if before is not None and (type(before) is not int or not 0<before<2**63):raise ValueError('Hibás lapozási azonosító.')
    where=['published=1'];args=[]
    for field,value in [('category',category),('status',status)]:
        if value:where.append(field+'=?');args.append(value)
    if before is not None:where.append('id<?');args.append(before)
    c=db()
    try:
        rows=[dict(r) for r in c.execute('SELECT id,category,status,created,public_summary AS summary,public_location AS location FROM reports WHERE '+' AND '.join(where)+' ORDER BY id DESC LIMIT 21',args)]
        more=len(rows)>20;rows=rows[:20]
        return {'items':rows,'next_before':rows[-1]['id'] if more else None}
    finally:c.close()
