"""Application entrypoints for API and UI."""

import os


def api_app():
    # Lazy import to avoid heavy imports on module load
    from job_application_automation.src.interfaces.api import create_app

    return create_app()


def run_streamlit() -> None:
    # Run the Streamlit UI app (organized under interfaces)
    os.execvp(
        "streamlit",
        [
            "streamlit",
            "run",
            "job_application_automation/src/interfaces/ui_app.py",
            "--server.port",
            "8501",
            "--server.address",
            "0.0.0.0",
        ],
    )


