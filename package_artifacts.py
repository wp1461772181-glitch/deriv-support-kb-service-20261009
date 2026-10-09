"""Build a portable ZIP and SHA-256 manifest using only the standard library."""
from pathlib import Path
import hashlib, zipfile

ROOT=Path(__file__).resolve().parent
ZIP_PATH=ROOT/"support-kb-service.zip"
MANIFEST=ROOT/"MANIFEST.txt"
EXCLUDED={".git",".agents",".codex",".aws","__pycache__","logs","briefs","support-kb-service.zip","MANIFEST.txt"}
EXCLUDED_PATHS={"support-kb-service"}  # stale nested extraction; canonical project is this directory
SENSITIVE_PARTS=("password","secret","token","credential")

def included(path):
    rel=path.relative_to(ROOT)
    if rel.parts and rel.parts[0] in EXCLUDED_PATHS: return False
    if any(part in EXCLUDED for part in rel.parts): return False
    if any("brief" in part.lower() for part in rel.parts): return False
    if any(part.startswith(".env") for part in rel.parts): return False
    if any(any(s in part.lower() for s in SENSITIVE_PARTS) for part in rel.parts): return False
    return path.is_file()

def main():
    files=sorted(p for p in ROOT.rglob("*") if included(p) and p!=ZIP_PATH and p!=MANIFEST)
    lines=[]
    for path in files:
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    MANIFEST.write_text("\n".join(lines)+"\n",encoding="utf-8")
    files.append(MANIFEST)
    with zipfile.ZipFile(ZIP_PATH,"w",zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files): archive.write(path,path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(ZIP_PATH) as archive:
        bad=archive.testzip()
        if bad: raise RuntimeError(f"CRC failure: {bad}")
    print(f"archive={ZIP_PATH.name} files={len(files)} crc=ok sha256={hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest()}")

if __name__=="__main__": main()
