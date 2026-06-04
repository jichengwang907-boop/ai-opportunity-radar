# Contributing

Thanks for improving AI Opportunity Radar.

## Local Setup

```powershell
py -m unittest discover -s tests
py -m shopping_intel.cli --config config.example.json --out reports/latest
```

The core project uses only the Python standard library. PyInstaller is optional and only needed for building the Windows desktop executable.

## Contribution Guidelines

- Keep secrets out of commits. Use `.env.local`, never tracked files.
- Do not commit generated reports, raw platform data, or local research exports.
- Prefer small, focused changes.
- Add or update tests when changing scoring, import, or report behavior.
- Use official APIs or exported CSV data. Do not add code that bypasses platform access controls.

## Useful Areas

- New public-signal collectors
- Better source health and retry handling
- More sample datasets
- Desktop UI improvements
- Product data cleanup MVP
- Invoice/receipt/statement organizer MVP

## Pull Request Checklist

- Tests pass with `py -m unittest discover -s tests`.
- No `.env.local`, API keys, raw data, or generated reports are included.
- README or docs are updated if behavior changes.
