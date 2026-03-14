# Changelog: `start_server.bat` — One-Click Server Launcher

**Date:** 2026-03-13

## What Was Added

Created `start_server.bat` in the project root — a portable batch file that starts the inventory management server with a single double-click.

## How It Works

| Step | Action |
|------|--------|
| **1** | Automatically `cd` into the folder where the `.bat` file lives (`%~dp0`), so it works no matter where the project folder is placed on the mini PC. |
| **2** | Checks if Python is installed and available in `PATH`. Shows a clear error if not. |
| **3** | Checks if Flask is installed. If not, automatically runs `pip install flask` to install it. |
| **4** | Launches `python server.py`, which starts the server on `http://localhost:8080`. |
| **5** | If the server exits or crashes, the window stays open so you can read error messages. |

## Prerequisites on the Mini PC

- **Python 3.x** must be installed with **"Add Python to PATH"** checked during installation.
- Internet connection on first run (only if Flask needs to be installed).

## Usage

1. Copy the entire `inventory management system` folder to the mini PC.
2. Double-click `start_server.bat`.
3. Wait for the server to start — the console will show `http://localhost:8080`.
4. Open a browser and navigate to `http://localhost:8080`.

## File

- [`start_server.bat`](file:///d:/CW/inventory%20management%20system/start_server.bat)
