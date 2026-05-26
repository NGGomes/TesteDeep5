""

from __future__ import annotations

import json
import subprocess
import tempfile
import shutil
import uuid
from pathlib import Path
from flask import Flask, request, send_file, jsonify
try:
  from flask_cors import CORS
  _HAS_CORS = True
except ImportError:
  _HAS_CORS = False
  print("[Texer] WARNING: flask-cors not installed — CORS headers disabled. "
        "Install with: pip install flask-cors")
import os
import sys

_HERE = Path(__file__).parent
# server_texer.py lives in soc-dashboard/server/ — project root is two levels up
_PROJECT_ROOT = _HERE.parent.parent

if str(_PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(_PROJECT_ROOT))

# Also support AGENT2_REPORTS_DIR override via environment variable
# (set automatically by shared_config, or manually if running standalone)
_env_reports_dir = os.environ.get("AGENT2_REPORTS_DIR", "")

try:
  from shared_config import AGENT2_REPORTS_DIR, TEXER_PORT, TEXER_HOST, TEXER_COMPILE_TIMEOUT, TEXER_COMPILE_RUNS
  # Override from env var if explicitly set (useful for non-standard layouts)
  if _env_reports_dir:
    AGENT2_REPORTS_DIR = Path(_env_reports_dir)
except ImportError:
  AGENT2_REPORTS_DIR = Path(_env_reports_dir) if _env_reports_dir else _PROJECT_ROOT / "reports" / "agent2"
  TEXER_PORT = int(os.environ.get("TEXER_PORT", "5002"))
  TEXER_HOST = os.environ.get("TEXER_HOST", "localhost")
  TEXER_COMPILE_TIMEOUT = int(os.environ.get("TEXER_COMPILE_TIMEOUT", "60"))
  TEXER_COMPILE_RUNS = int(os.environ.get("TEXER_COMPILE_RUNS", "2"))

app = Flask(__name__)
if _HAS_CORS:
  CORS(app)

PORT = TEXER_PORT
HOST = TEXER_HOST
TEMP_DIR = Path(tempfile.gettempdir()) / "redshift_texer"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_tex(file_param: str) -> Path | None:
  """
  Resolve a tex file from a name or path.
  Accepts:
    - bare filename: 'report_abc.tex' or 'report_abc.pdf'
    - relative path: 'agent2/report_abc.tex'
    - absolute path inside AGENT2_REPORTS_DIR
  Always strips directory traversal attempts.
  """
  # Take only the filename component — prevent path traversal
  name = Path(file_param).name
  if not name:
    return None

  # Accept .pdf input — derive .tex name
  if name.endswith(".pdf"):
    name = name[:-4] + ".tex"
  elif not name.endswith(".tex"):
    name = name + ".tex"

  candidate = AGENT2_REPORTS_DIR / name
  return candidate if candidate.exists() else None


def _compile_tex(tex_path: Path) -> Path | None:
  """
  Compile a .tex file (TEXER_COMPILE_RUNS passes) and return the PDF path,
  or None on failure. Always cleans up the temp directory.
  """
  work_dir = TEMP_DIR / str(uuid.uuid4())
  work_dir.mkdir(parents=True)
  try:
    temp_tex = work_dir / tex_path.name
    shutil.copy2(tex_path, temp_tex)

    for i in range(TEXER_COMPILE_RUNS):
      result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        cwd=work_dir,
        capture_output=True,
        text=True,
        timeout=TEXER_COMPILE_TIMEOUT,
      )
      if i == TEXER_COMPILE_RUNS - 1 and result.returncode != 0:
        log_file = work_dir / tex_path.name.replace(".tex", ".log")
        log_tail = ""
        if log_file.exists():
          log_tail = log_file.read_text(encoding="utf-8", errors="replace")[-2000:]
        raise RuntimeError(f"pdflatex failed (exit {result.returncode}):\n{log_tail}")

    pdf_path = work_dir / tex_path.name.replace(".tex", ".pdf")
    if pdf_path.exists() and pdf_path.stat().st_size > 1000:
      # Move PDF to a stable temp location before returning
      out_pdf = TEMP_DIR / f"{tex_path.stem}_{uuid.uuid4().hex[:8]}.pdf"
      shutil.copy2(pdf_path, out_pdf)
      return out_pdf
    return None
  finally:
    shutil.rmtree(work_dir, ignore_errors=True)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/debug", methods=["GET"])
def debug():
  tex_files = []
  if AGENT2_REPORTS_DIR.exists():
    tex_files = [f.name for f in AGENT2_REPORTS_DIR.glob("*.tex")]
  return jsonify({
    "agent2_reports_dir": str(AGENT2_REPORTS_DIR),
    "reports_dir_exists": AGENT2_REPORTS_DIR.exists(),
    "tex_files_found": len(tex_files),
    "tex_files": tex_files[:10],
    "project_root": str(_PROJECT_ROOT),
    "pdflatex": shutil.which("pdflatex") or "not found",
  })


@app.route("/health", methods=["GET"])
def health():
  return jsonify({
    "status": "ok",
    "texer": "running",
    "reports_dir": str(AGENT2_REPORTS_DIR),
    "pdflatex": shutil.which("pdflatex") or "not found",
    "compile_timeout_s": TEXER_COMPILE_TIMEOUT,
    "compile_runs": TEXER_COMPILE_RUNS,
  })


@app.route("/render-pdf", methods=["GET"])
def render_pdf_get():
  """
  GET /render-pdf?file=<name_or_path>
  Compile the .tex and stream the resulting PDF.
  """
  file_param = request.args.get("file", "")
  if not file_param:
    return jsonify({"error": "Missing 'file' parameter"}), 400

  tex_path = _resolve_tex(file_param)
  if tex_path is None:
    return jsonify({"error": f"File not found: {file_param}"}), 404

  try:
    pdf_path = _compile_tex(tex_path)
    if pdf_path and pdf_path.exists():
      return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=tex_path.stem + ".pdf",
      )
    return jsonify({"error": "PDF compilation produced no output"}), 500
  except subprocess.TimeoutExpired:
    return jsonify({"error": "pdflatex timed out (60s)"}), 500
  except FileNotFoundError:
    return jsonify({"error": "pdflatex not installed. Install TeX Live or MiKTeX."}), 500
  except RuntimeError as exc:
    return jsonify({"error": str(exc)}), 500
  except Exception as exc:
    return jsonify({"error": str(exc)}), 500


@app.route("/render", methods=["POST"])
def render_pdf_post():
  """
  POST /render  {file: "<filename.tex>"}
  Same as GET /render-pdf but via POST body.
  """
  data = request.get_json(silent=True) or {}
  file_param = data.get("file", "")
  if not file_param:
    return jsonify({"error": "Missing 'file' in request body"}), 400
  return render_pdf_get.__wrapped__(file_param) if hasattr(render_pdf_get, '__wrapped__') \
    else app.test_client().get(f"/render-pdf?file={file_param}")


@app.route("/list", methods=["GET"])
def list_reports():
  """List all report files in AGENT2_REPORTS_DIR."""
  if not AGENT2_REPORTS_DIR.exists():
    return jsonify({
      "files": [],
      "reports_dir": str(AGENT2_REPORTS_DIR),
      "error": "Directory does not exist",
    })
  tex_files  = sorted([f.name for f in AGENT2_REPORTS_DIR.glob("*.tex")],  reverse=True)
  json_files = sorted([f.name for f in AGENT2_REPORTS_DIR.glob("*.json")], reverse=True)[:10]
  md_files   = sorted([f.name for f in AGENT2_REPORTS_DIR.glob("*.md")],   reverse=True)[:5]
  return jsonify({
    "reports_dir": str(AGENT2_REPORTS_DIR),
    "tex_files": tex_files,
    "json_files": json_files,
    "md_files": md_files,
    "total_tex": len(tex_files),
  })


if __name__ == "__main__":
  print(f"[Texer] Starting on http://{HOST}:{PORT}")
  print(f"[Texer] Reports directory: {AGENT2_REPORTS_DIR}")
  print(f"[Texer] Temp directory:    {TEMP_DIR}")
  print(f"[Texer] Compile timeout:   {TEXER_COMPILE_TIMEOUT}s × {TEXER_COMPILE_RUNS} passes")
  pdflatex = shutil.which("pdflatex")
  if not pdflatex:
    print("[Texer] WARNING: pdflatex not found — PDF rendering will fail.")
    print("[Texer]          Install TeX Live: sudo apt install texlive-full")
  else:
    print(f"[Texer] pdflatex: {pdflatex}")
  app.run(host=HOST, port=PORT, debug=False, threaded=True)