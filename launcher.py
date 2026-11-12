import os
import sys
from pathlib import Path


def resource_path(name: str) -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / name)


def main():
    # Make bundled FFmpeg available to the app's subprocess calls.
    ffmpeg_dir = resource_path("ffmpeg")
    if os.path.isdir(ffmpeg_dir):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    app_file = resource_path("app.py")

    from streamlit.web import cli as stcli
    sys.argv = [
        "streamlit", "run", app_file,
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
        "--server.address=127.0.0.1",
    ]
    stcli.main()


if __name__ == "__main__":
    main()
