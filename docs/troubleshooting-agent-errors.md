# Agent error troubleshooting (v0.4.7)

## `POST /api/agent/run` returns HTTP 403

In earlier versions, the agent returned 403 when `auto_apply=true` but `AUTO_SUBMIT_ENABLED=false`. That blocked discovery even though only submission was disabled. v0.4.7 lets discovery and application preparation finish, skips browser submission, and returns a clear warning. Automatic submission remains disabled unless configured explicitly.

The individual `/api/applications/{id}/browser-fill` endpoint still returns 403 if a caller explicitly requests final submission while the setting is disabled. This is an intentional safety control.

## Lever source returns HTTP 404

A Lever endpoint such as `/v0/postings/<site-slug>` returns 404 if the configured site slug is invalid or the board no longer exists. v0.4.7 pauses a Lever source after a 404 to avoid repeating the failing request on every search and reports the cause in Source status. Remove the invalid source in Find Jobs and add the correct public site slug, for example the `<site-slug>` part of `https://jobs.lever.co/<site-slug>`.

A placeholder ID such as `agent-bbb724bb6d56` is not a real employer board identifier.


## Windows Playwright error: `NotImplementedError` in `_make_subprocess_transport`

If the log contains `Task exception was never retrieved` from Playwright's `Connection.run()` and a `NotImplementedError` in `asyncio/base_events.py` at `_make_subprocess_transport`, Playwright is being started under a Windows `SelectorEventLoop`. Playwright's async driver uses subprocesses and requires `ProactorEventLoop` on Windows. Uvicorn uses `SelectorEventLoop` in Windows `--reload` or multi-worker mode.

Fix:

1. Stop Uvicorn with Ctrl+C.
2. From `C:\Projects\ai-job-hunter-phase4\backend`, activate the correct virtual environment.
3. Start the browser-automation server with `python run_server.py`. This uses one process and no reload.
4. Leave the frontend running at `http://localhost:5173` and retry the browser workflow.
5. In Settings, click **Check browser setup**. The diagnostic now reports the active event-loop type and the corrective action.

Do not repeatedly reinstall Chromium to fix this specific traceback; the issue is the event loop, not the browser binary.
