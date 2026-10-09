"""Validate Git publication candidates without displaying credential values."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BLOCKED_DIRS = {"node_modules", ".venv", "venv", "dist", "build", "backups", ".runtime",
                ".idea", ".workbuddy", ".mypy_cache", "__pycache__", "test-results", "playwright-report"}
PATTERNS = [re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
            re.compile(r"mysql\+\w+://[^\s/'\"]+:[^\s/@'\"]+@")]


def main() -> int:
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                            cwd=ROOT, check=True, capture_output=True)
    files = sorted(set(name for name in result.stdout.decode("utf-8").split("\0") if name))
    failures = []
    private_values = []
    for local in (ROOT / "customer-service-backend/.env", ROOT / "ecommerce-service-backend/.env"):
        if not local.exists():
            continue
        for line in local.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip().upper() in {"LLM_API_KEY", "DATABASE_URL", "AVATAR_ACCESS_KEY_SECRET"}:
                value = value.strip().strip("\"'")
                if len(value) >= 16 and "TODO_" not in value:
                    private_values.append(value)
    for name in files:
        path = Path(name)
        if set(path.parts) & BLOCKED_DIRS or (path.name.startswith(".env") and path.name != ".env.example") or path.suffix in {".key", ".pem", ".log", ".pyc"}:
            failures.append(f"{name}: excluded local file present in candidates")
            continue
        data = (ROOT / path).read_bytes()
        if b"\0" in data:
            continue
        for number, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), start=1):
            known_private = any(value in line for value in private_values)
            suspicious = any(pattern.search(line) for pattern in PATTERNS) and not any(marker in line for marker in ("TODO_", "<REDACTED>", "test-only", "dummy", "example"))
            if known_private or suspicious:
                failures.append(f"{name}:{number}: possible credential; value suppressed")
    for failure in failures:
        print(failure)
    print(f"Checked {len(files)} publication candidates; {len(failures)} problems.")
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
