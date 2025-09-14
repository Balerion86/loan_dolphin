#!/usr/bin/env python3
import argparse
import html
import os
from pathlib import Path

# Which files to embed (relative to --src)
DEFAULT_GLOBS = [
    "app.py",
    "core/**/*.py",
    "charts/**/*.py",
    "ui/**/*.py",
    ".streamlit/config.toml",
]

# CDN versions (adjust if needed)
STLITE_VERSION = "0.89.1"  # stlite browser build
# Tip: you don't need "streamlit" itself in requirements for stlite
DEFAULT_REQUIREMENTS = ["pandas", "plotly"]

HTML_TEMPLATE = """<!doctype html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>{title}</title>
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@{ver}/build/stlite.css" />
    <script type="module" src="https://cdn.jsdelivr.net/npm/@stlite/browser@{ver}/build/stlite.js"></script>
  </head>
  <body>
    <streamlit-app>
{files}
      <app-requirements>
{requirements}
      </app-requirements>
    </streamlit-app>
  </body>
</html>
"""

APPFILE_TEMPLATE = """      <app-file name="{name}"{entry}>
{content}
      </app-file>
"""

def read_requirements(src_dir: Path) -> str:
    req = src_dir / "requirements.txt"
    if req.exists():
        text = req.read_text(encoding="utf-8").strip()
        # Remove 'streamlit' if present; stlite bundles it
        lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lower().startswith("streamlit")]
        return "\n".join(lines) or "\n".join(DEFAULT_REQUIREMENTS)
    return "\n".join(DEFAULT_REQUIREMENTS)

def collect_files(src_dir: Path, patterns) -> list[Path]:
    seen = set()
    out = []
    for pat in patterns:
        for p in src_dir.glob(pat):
            if p.is_file():
                rp = p.relative_to(src_dir)
                if rp not in seen:
                    seen.add(rp)
                    out.append(rp)
    # Ensure app.py is first
    out.sort()
    out = sorted(out, key=lambda p: (0 if p.as_posix()=="app.py" else 1, p.as_posix()))
    return out

def to_appfile_tag(src_dir: Path, rel_path: Path) -> str:
    text = (src_dir / rel_path).read_text(encoding="utf-8")
    # Escape for HTML text node
    esc = html.escape(text)
    entry = " entrypoint" if rel_path.as_posix() == "app.py" else ""
    # Make sure parent dirs exist implicitly: stlite infers from name
    return APPFILE_TEMPLATE.format(name=rel_path.as_posix(), entry=entry, content=indent(esc, 8))

def indent(s: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in s.splitlines())

def build_html(src_dir: Path, title: str) -> str:
    files = collect_files(src_dir, DEFAULT_GLOBS)
    if not any(p.as_posix() == "app.py" for p in files):
        raise SystemExit("app.py not found in --src")

    file_tags = []
    for rp in files:
        file_tags.append(to_appfile_tag(src_dir, rp))
    req_text = read_requirements(src_dir)

    return HTML_TEMPLATE.format(
        title=html.escape(title),
        ver=STLITE_VERSION,
        files="\n".join(file_tags),
        requirements=indent(req_text, 8),
    )

def main():
    ap = argparse.ArgumentParser(description="Build a single-file stlite HTML for loan_dolphin.")
    ap.add_argument("--src", type=Path, default=Path("loan_dolphin"), help="Source app folder (contains app.py).")
    ap.add_argument("--out", type=Path, default=Path("loan_dolphin_standalone.html"), help="Output HTML file.")
    ap.add_argument("--title", type=str, default="loan_dolphin (stlite)", help="HTML <title>.")
    args = ap.parse_args()

    html_text = build_html(args.src, args.title)
    args.out.write_text(html_text, encoding="utf-8")
    print(f"✅ Wrote {args.out} (open in a modern browser with internet access).")

if __name__ == "__main__":
    main()
