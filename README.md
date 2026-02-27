# Quinix Workers - Auto Absence Request Processor

Pure Python automation that logs in and processes absence requests across multiple browser windows.

## Quick Start

1. **Set number of workers** (line 11 in `quinix_dashboard_auto.py`):
   ```python
   NUM_WORKERS = 6  # Change this to 7, 8, 10, etc.
   ```

2. **Run the script**:
   ```bash
   .\venv\Scripts\python.exe quinix_dashboard_auto.py
   ```

3. **Monitor progress** in the web dashboard that opens automatically

## How It Works

- **Dynamic worker assignment**: Each worker automatically takes from their position in the list
  - With 6 workers: positions 0/6, 1/6, 2/6, 3/6, 4/6, 5/6
  - With 7 workers: positions 0/7, 1/7, 2/7, 3/7, 4/7, 5/7, 6/7
  - With 10 workers: positions 0/10, 1/10, 2/10... etc.

- **No collisions**: Workers automatically spread across the list and adjust as it shrinks

- **Auto-login**: Logs into all workers through Microsoft SSO automatically

- **Sidebar handling**: Automatically reopens notification panel if it closes

## Recommended Settings

- **6-10 workers**: Best balance of speed vs. resources
- **10-20 workers**: Requires 16GB+ RAM, risk of rate limiting
- **20+ workers**: Not recommended (server blocking risk)

## Files

- `quinix_dashboard_auto.py` - Main automation script
- `dashboard.html` - Web dashboard (opens automatically)
- `password.txt` - Your password (in .gitignore)
- `EdgeProfile1-N/` - Browser profiles (auto-created)

## Tips

- Windows can stack on top of each other - they won't freeze
- Press CTRL+C to stop and close all browsers
- Dashboard updates every 2 seconds
- Check terminal for detailed logs
