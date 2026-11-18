"""One-time, explicit import into an empty Supabase schema; never logs secrets."""
import os
import sqlite3
import sys

import psycopg
from psycopg import sql

TABLES=('users','health_assessments','family_connections','reviews','workspace_items','user_preferences')


def main(path):
    source=sqlite3.connect(f'file:{os.path.abspath(path)}?mode=ro',uri=True)
    with psycopg.connect(os.environ['DATABASE_URL'],sslmode='require') as target:
        for table in TABLES:
            count=target.execute(sql.SQL('SELECT count(*) FROM medpredict.{}').format(sql.Identifier(table))).fetchone()[0]
            if count: raise RuntimeError('The target must be empty. Nothing has been imported.')
        existing={x[0] for x in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in TABLES:
            if table not in existing: continue
            cursor=source.execute(f'SELECT * FROM {table}')
            columns=[x[0] for x in cursor.description]
            statement=sql.SQL('INSERT INTO medpredict.{} ({}) VALUES ({})').format(sql.Identifier(table),
                sql.SQL(',').join(map(sql.Identifier,columns)),sql.SQL(',').join(sql.Placeholder()*len(columns)))
            rows=cursor.fetchall()
            if rows: target.cursor().executemany(statement,rows)
            if 'id' in columns:
                target.execute(sql.SQL("SELECT setval(pg_get_serial_sequence(%s,'id'),COALESCE(MAX(id),1),COUNT(*)>0) FROM medpredict.{}").format(sql.Identifier(table)),(f'medpredict.{table}',))
    source.close()
    print('Import committed. Verify account login and History before changing the deployment.')

if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Usage: python db/import_sqlite.py PATH_TO_BACKUP')
    main(sys.argv[1])
