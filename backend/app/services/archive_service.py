import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from collections.abc import Callable

from app.core.config import settings


def _find_rar_tool() -> str | None:
    candidates = [
        shutil.which("7z"),
        shutil.which("7za"),
        shutil.which("unar"),
        shutil.which("bsdtar"),
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _extract_rar_with_tool(
    archive_file: Path,
    dest: Path,
    progress_callback: Callable[[int, str], None] | None = None,
) -> None:
    tool = _find_rar_tool()
    if not tool:
        raise ValueError(
            "RAR extraction is not supported in this environment. Install 7-Zip or unar and try again."
        )

    tool_name = Path(tool).stem.lower()
    if tool_name in {"7z", "7za"}:
        process = subprocess.Popen(
            [tool, "x", str(archive_file), f"-o{dest}", "-y", "-bsp1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        if process.stdout:
            output = ""
            while True:
                chunk = process.stdout.read(1)
                if not chunk:
                    break
                output = (output + chunk)[-80:]
                match = re.search(r"(\d{1,3})%", output)
                if match and progress_callback:
                    progress_callback(
                        min(int(match.group(1)), 100),
                        "Extracting archive contents",
                    )
        if process.wait() != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)
    elif tool_name == "unar":
        subprocess.run([tool, "-o", str(dest), "-f", str(archive_file)], check=True)
    else:
        subprocess.run([tool, "-xf", str(archive_file), "-C", str(dest)], check=True)


def extract_archive(
    archive_path: str,
    destination: str,
    progress_callback: Callable[[int, str], None] | None = None,
) -> Path:
    archive_file = Path(archive_path)
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)

    if archive_file.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive_file, "r") as zf:
            members = zf.infolist()
            if len(members) > settings.MAX_EXTRACTED_FILES:
                raise ValueError("Archive contains too many files.")

            total_size = 0
            for member in members:
                member_path = (dest / member.filename).resolve()
                if not member_path.is_relative_to(dest.resolve()):
                    raise ValueError("Archive contains an unsafe path.")
                if member.is_dir():
                    continue
                total_size += member.file_size
                if total_size > settings.MAX_EXTRACTED_SIZE_MB * 1024 * 1024:
                    raise ValueError("Archive extracted size exceeds the configured limit.")

            total = max(len(members), 1)
            for index, member in enumerate(members, start=1):
                target = (dest / member.filename).resolve()
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
                if progress_callback:
                    progress_callback(round(index / total * 100), f"Extracting {member.filename}")
    elif archive_file.suffix.lower() == ".rar":
        _extract_rar_with_tool(archive_file, dest, progress_callback)
    else:
        raise ValueError("Unsupported archive type.")

    extracted = _find_project_root(dest)
    return extracted


def _find_project_root(base: Path) -> Path:
    project_dirs = {"backend", "frontend", "src", "app"}
    project_files = {"package.json", "requirements.txt", "pyproject.toml", "README.md"}

    for child in base.iterdir():
        if child.is_dir() and child.name in {"backend", "frontend", "src", "app"}:
            return child
        if child.is_file() and child.name in project_files:
            return base

    for current, dirs, files in os.walk(base, topdown=True, followlinks=False):
        dirs[:] = [directory for directory in dirs if directory.lower() not in _IGNORED_DIRS]
        current_path = Path(current)
        for directory in dirs:
            if directory in project_dirs:
                return current_path / directory
        if any(file_name in project_files for file_name in files):
            return current_path

    return base


_IGNORED_DIRS = {
    "node_modules",
    ".venv",
    "dist",
    "build",
    "__pycache__",
    ".git",
    "venv",
    "coverage",
}


def safe_list_project_files(
    root: Path,
    progress_callback: Callable[[int, str], None] | None = None,
) -> list[str]:
    discovered: list[Path] = []

    for current, dirs, file_names in os.walk(root, topdown=True, followlinks=False):
        dirs[:] = [
            directory
            for directory in dirs
            if directory.lower() not in _IGNORED_DIRS
            and not (Path(current) / directory).is_symlink()
        ]
        current_path = Path(current)
        for file_name in file_names:
            path = current_path / file_name
            if path.is_symlink():
                continue
            try:
                discovered.append(path)
            except OSError:
                continue

    files: list[str] = []
    total = max(len(discovered), 1)
    for index, path in enumerate(discovered, start=1):
        try:
            relative_path = path.relative_to(root).as_posix()
            files.append(relative_path)
            if progress_callback:
                progress_callback(round(index / total * 100), f"Testing {relative_path}")
        except OSError:
            continue

    return files
