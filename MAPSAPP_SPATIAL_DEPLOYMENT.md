# Mapsapp Spatial Analysis Deployment

The spatial-analysis integration is additive. Existing mapsapp pages and URLs
remain in place, while the new page is available at:

```text
/mapsapp/spatial-analysis/
```

## Local verification

Run commands from the repository root unless noted otherwise.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe sensdweb\manage.py check
.\.venv\Scripts\python.exe sensdweb\manage.py migrate --plan
.\.venv\Scripts\python.exe sensdweb\manage.py migrate
cd sensdweb
..\.venv\Scripts\python.exe manage.py test
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Do not commit `.env`, license files, database passwords, or encryption keys.
Existing `DJANGO_SECRET_KEY` and `SALT_KEY` values must be preserved to read
existing encrypted records.

## Merge to main

After reviewing the feature branch:

```powershell
git status
git add .gitignore requirements.txt requirements-aws.txt MAPSAPP_SPATIAL_DEPLOYMENT.md sensdweb
git commit -m "Integrate encrypted mapsapp spatial analysis"
git push -u origin feature/mapsapp-spatial-analysis
```

Merge the reviewed branch through GitHub. Do not add the source ZIP to the
commit.

## EC2 deployment

Take an RDS snapshot before applying the migration. On the EC2 application
server:

```bash
cd /srv/sensd
git fetch origin
git switch main
git pull --ff-only origin main
source .venv/bin/activate
python -m pip install -r requirements-aws.txt
python sensdweb/manage.py check
python sensdweb/manage.py migrate --plan
python sensdweb/manage.py migrate
python sensdweb/manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl status gunicorn --no-pager
sudo nginx -t
```

The migration creates only these tables:

- `mapsapp_uploadeddataset`
- `mapsapp_uploadedfeature`
- `mapsapp_analysisrun`

Uploaded datasets are linked to the authenticated SENSD user. User-provided
names, filenames, fields, feature properties, parameters, and summaries are
encrypted. PostGIS geometry remains queryable and receives a spatial index.

The Gurobi license is separate from this mapsapp functionality. Confirm the
Gunicorn service receives `GRB_LICENSE_FILE` before testing optimization.
