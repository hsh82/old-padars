"""Explicit fresh stage2.kara.loc installer. DB root credential arrives via stdin only.

Run from the isolated Bench sites/; never run against an existing site.
"""
import json,secrets,sys,os
from pathlib import Path
import frappe,padars
from frappe.installer import _new_site
site='stage2.kara.loc'
assert str(Path(padars.__file__).resolve()).startswith('/workspace/frappe-bench/apps/padars/')
assert not Path(site).exists(), 'Refusing to overwrite an existing site'
root_password=sys.stdin.read().strip()
assert root_password
password=secrets.token_urlsafe(24)
private=Path('/workspace/private');private.mkdir(mode=0o700,exist_ok=True)
os.chmod(private,0o700)
credentials=private/'staging2-credentials.json'
credentials.write_text(json.dumps({'site':site,'accounts':{'Administrator':{'password':password,'purpose':'Company administrator; do not give this account to school customers'}}},indent=2))
os.chmod(credentials,0o600)
try:
 frappe.init(site,new_site=True)
 _new_site(db_name=None,site=site,db_root_username='root',db_root_password=root_password,admin_password=password,db_host='global-db',db_port=3306,mariadb_user_host_login_scope='%',install_apps=['erpnext','education','padars'],force=False,verbose=False)
 assert len(frappe.get_all('Role Profile',filters={'name':['like','Padars %']}))==12
 frappe.db.commit()
 print('PASS: isolated Staging 2 installed with all 12 Role Profiles; credentials saved privately')
except Exception as exc:
 print('INSTALL BLOCKER:',type(exc).__name__,str(exc).replace(root_password,'[redacted]').replace(password,'[redacted]')[:500])
 sys.exit(1)
finally:frappe.destroy()
config=Path(site)/'site_config.json';settings=json.loads(config.read_text());settings.update({'mute_emails':1,'host_name':'http://stage2.kara.loc','developer_mode':0,'allow_tests':False,'padars_staging_demo':1})
config.write_text(json.dumps(settings,indent=2));os.chmod(config,0o600)
