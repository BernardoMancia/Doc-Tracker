import shutil
import sys
from pathlib import Path
from cx_Freeze import setup, Executable

BASE_DIR = Path(__file__).resolve().parent
BUILD_DIR = BASE_DIR / "build"
DIST_DIR = BASE_DIR / "dist"

for d in (BUILD_DIR, DIST_DIR):
    if d.exists():
        shutil.rmtree(d)

build_options = {
    "packages": [
        "asyncio", "json", "csv", "logging", "threading",
        "tkinter", "tkinter.ttk",
        "httpx", "fitz", "docx", "openpyxl",
        "ddgs", "pydantic", "pydantic_settings",
        "sqlalchemy", "aiosqlite",
    ],
    "excludes": [
        "fastapi", "uvicorn", "starlette", "jinja2",
        "apscheduler", "multipart",
        "test", "unittest", "pytest",
    ],
    "include_files": [
        (str(BASE_DIR / "data"), "data"),
    ],
    "build_exe": str(DIST_DIR / "OSINT_DLP_Desktop"),
}

target = Executable(
    script=str(BASE_DIR / "desktop" / "app.py"),
    base="Win32GUI" if sys.platform == "win32" else None,
    target_name="OSINT_DLP_Desktop.exe",
    icon=None,
)

setup(
    name="OSINT & DLP Desktop",
    version="2.1.0",
    description="Consulta OSINT/DLP — Grupo Roullier (Desktop Standalone)",
    options={"build_exe": build_options},
    executables=[target],
)
