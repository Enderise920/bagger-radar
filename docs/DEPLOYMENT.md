# Private deployment checklist

## Before the first push

- [ ] Confirm `.env` and `.streamlit/secrets.toml` are ignored.
- [ ] Run `python -m unittest tests.test_yahoo_migration -v`.
- [ ] Run `python -m py_compile app/dashboard.py backend/yahoo_provider.py backend/migrate_yahoo.py`.
- [ ] Start the app locally and open all application sections.
- [ ] Review `data/yahoo_migration_status.json`.
- [ ] Do not publish old vendor data unless redistribution is permitted.

## GitHub

```powershell
git init
git add .
git status
git commit -m "Prepare BAGGER RADAR Yahoo migration"
git branch -M main
git remote add origin https://github.com/USERNAME/bagger-radar.git
git push -u origin main
```

Inspect `git status` before committing. `.env` must never appear in the staged file list.

## Streamlit Community Cloud

- Repository: your private GitHub repository.
- Branch: `main`.
- Main file: `app/dashboard.py`.
- Secrets: add only optional provider credentials the application actually needs.
- After deployment, inspect logs for missing packages, invalid paths, or memory limits.

Keep the application private until source terms, redistribution rights, full-universe coverage, missing-data behavior, and score drift have been reviewed.
