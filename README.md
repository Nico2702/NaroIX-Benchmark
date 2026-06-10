# NaroIX Benchmark Series

A Streamlit dashboard for the NaroIX benchmark index construction. Runs entirely on your local Windows machine — no login or secrets required.

## Prerequisites

- Windows 10/11
- Python 3.11+
- A virtual environment with the dependencies from [requirements.txt](requirements.txt) installed (a `venv/` folder is included).

## Run locally (Windows PowerShell)

### 1. Activate the virtual environment

```powershell
.\venv\Scripts\activate
```

> If PowerShell blocks the script with an execution-policy error, run this once in the same terminal, then retry:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

Once active, your prompt is prefixed with `(venv)`.

### 2. Start the app

```powershell
streamlit run naroix_benchmark.py
```

Streamlit prints a local URL (default <http://localhost:8501>) and opens it in your browser automatically.

## First-time setup (only if the venv is missing)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Notes

- **No authentication.** The app runs open on localhost — no GitHub login or `secrets.toml` needed.
- **Master File loading.** On first upload, a large `.xlsx` master file is parsed once (using the fast `calamine` engine) and then cached for the session. Restarting Streamlit clears the cache, so the file is re-parsed on the next run.
- **Stopping the app.** Press `Ctrl+C` in the terminal.
