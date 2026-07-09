"""Local spike: drive a real browser-use apply for one application.

This is the development harness for the Phase-2 browser backbone — it is NOT part of CI
(it needs a real browser/display and a valid assisted-login session for the platform).

Prerequisites:
  * A real Chrome/Chromium available to browser-use (headful or Xvfb).
  * The target application's user has a saved platform session
    (CredentialStore.save_session_cookies) and an LLM key (CredentialStore.put_llm_key).

Usage (from backend/):
    BROWSER__LIVE_APPLY=true PYTHONPATH=. python scripts/spike_apply.py <application_id>
"""

from __future__ import annotations

import asyncio
import sys

from app.core.automation.runtime.apply import ApplyPrerequisiteError, run_apply
from app.db.session import async_session_factory
from app.models.application import Application


async def main(application_id: str) -> int:
    async with async_session_factory() as db:
        app = await db.get(Application, application_id)
        if app is None:
            print(f"Application {application_id} not found")
            return 1
        try:
            result = await run_apply(db, app)
        except ApplyPrerequisiteError as exc:
            print(f"PREREQUISITE MISSING: {exc}")
            return 2
        print("RESULT:", result.model_dump())
        return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/spike_apply.py <application_id>")
        raise SystemExit(1)
    raise SystemExit(asyncio.run(main(sys.argv[1])))
