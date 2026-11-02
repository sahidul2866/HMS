"""Run local ERP integration tests in disposable schemas of a dedicated test DB."""
import os
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'backend'))
from app.core.config import get_settings
from sqlalchemy.engine import make_url
from sqlalchemy import create_engine, text

url=make_url(os.environ.get('HMS_TEST_DATABASE_URL') or get_settings().database_url).set(database='hms_erp_test') if not os.environ.get('HMS_TEST_DATABASE_URL') else make_url(os.environ['HMS_TEST_DATABASE_URL'])
if url.host not in {'localhost','127.0.0.1'} or 'test' not in (url.database or ''):
    sys.exit('ERP tests require a local PostgreSQL database with test in its name.')
try:
    engine=create_engine(url)
    with engine.connect() as connection:connection.execute(text('SELECT 1'))
    engine.dispose()
except Exception:
    sys.exit('Create the local hms_erp_test database with the development database user as owner, or set HMS_TEST_DATABASE_URL to an existing local test database. Credentials are not printed.')
env=os.environ.copy();env['PYTHONPATH']=str(root/'backend');env['HMS_TEST_DATABASE_URL']=url.render_as_string(hide_password=False)
sys.exit(subprocess.run([sys.executable,'-m','pytest',str(root/'backend/tests'),'-q'],cwd=root,env=env).returncode)
