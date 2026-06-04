# Open Source Release Checklist

Use this before publishing the repository.

## Must Not Publish

- `.env.local`
- `reports/`
- `build/`
- `dist/`
- `data/raw/`
- `data/tmp/`
- `data/external/`
- `data/history/`
- local full CSV exports such as `data/search_results.realtime-ai.csv`
- private spreadsheets downloaded from browsers or marketplaces

## Safe To Publish

- source code under `shopping_intel/` and `scripts/`
- tests under `tests/`
- `data/*.sample.csv`
- `data/*.template.csv`
- config files without secrets
- documentation files

## Before First Push

```powershell
py -m unittest discover -s tests
py -m shopping_intel.cli --config config.example.json --out reports/latest
rg -n "sk-|ghp_|github_pat|AIza|Bearer " -g "!data/**" -g "!reports/**" -g "!build/**" -g "!dist/**"
git status --ignored
```

If any ignored local data appears under staged files, unstage it before pushing.
