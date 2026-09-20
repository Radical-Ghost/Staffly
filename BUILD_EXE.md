# Build Staffly EXE

Use the existing PyInstaller spec (already configured for single-file output and report assets):

```bash
uv run pyinstaller --noconfirm --clean Staffly.spec
```

Output:
- `dist\Staffly.exe`

Notes:
- This is an all-in-one executable (`EXE` in `Staffly.spec`).
- If you only want to rebuild without cleaning, remove `--clean`.
