# Staffly Transfer Setup (Windows, with existing data)

Use this when moving Staffly to another PC and keeping all current data.

## 1) On old PC: package project + DB (exclude dev/runtime junk)

```powershell
cd C:\Projects

# Create clean staging folder
Remove-Item -Recurse -Force .\Staffly-staging -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path .\Staffly-staging | Out-Null

# Copy project while excluding heavy/unneeded folders
robocopy .\Staffly .\Staffly-staging /E /XD .venv .git __pycache__ .pytest_cache .mypy_cache .ruff_cache dist build temp

# Create transfer zip from staging
Compress-Archive -Path .\Staffly-staging\* -DestinationPath .\Staffly-transfer.zip -Force

# Optional cleanup
Remove-Item -Recurse -Force .\Staffly-staging
```

Copy `Staffly-transfer.zip` to the new PC (USB, network share, cloud drive, etc.).

## 2) On new PC: install prerequisites

```powershell
winget install -e --id AstralSh.uv
uv python install 3.11
```

If `winget` is not available, install uv from: https://docs.astral.sh/uv/getting-started/installation/

## 3) On new PC: extract and open project

```powershell
cd C:\Projects
Expand-Archive -Path .\Staffly-transfer.zip -DestinationPath .\Staffly -Force
cd .\Staffly
```

## 4) Sync dependencies

```powershell
uv sync
```

## 5) Ensure DB file is present (your existing data)

```powershell
New-Item -ItemType Directory -Force -Path .\data | Out-Null
Test-Path .\data\staffly.db
```

Expected: `True`

- If `False`, copy your backup DB file into `data\staffly.db`.

## 6) Run app

```powershell
uv run staffly
```

## Optional checks

### Check that DB is the copied one (size/time)

```powershell
Get-Item .\data\staffly.db | Select-Object FullName, Length, LastWriteTime
```

### Start with clean empty DB (only if needed)

```powershell
Remove-Item .\data\staffly.db -Force
uv run staffly
```

## Notes

- Staffly uses DB path: `data\staffly.db`
- First run prints: `Initializing database at: ...\data\staffly.db`
- No build step needed for this flow.
