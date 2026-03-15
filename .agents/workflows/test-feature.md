---
description: How to test a new feature in the browser
---

# Testing New Features

## Important: Server Configuration

> **The webapp runs on port 8080, NOT port 5000.**

The server (`server.py`) runs at `http://127.0.0.1:8080/`.

When testing any new feature in the browser, **always** navigate to:
```
http://127.0.0.1:8080/
```

**NEVER** use port 5000. Flask's default port is 5000, but this project is configured to use **8080**.

## Steps

1. Ensure the server is running: `python server.py` (in `d:\CW\inventory management system`)
2. Open or navigate the browser to `http://127.0.0.1:8080/`
3. Navigate to the relevant page/tab for the feature being tested
4. Verify the feature visually and functionally
5. Take screenshots as needed to confirm the result
