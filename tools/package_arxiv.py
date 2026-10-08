"""Build the thesis and package the arXiv upload.

usage: python tools/package_arxiv.py [--texbin DIR | --tectonic PATH] [--out DIR]

Builds main.tex, either the way arXiv does (pdflatex, bibtex, pdflatex x2, with
the TeX Live binaries in --texbin) or with Tectonic, then writes
DIR/peertocp-thesis.pdf and DIR/peertocp-thesis-arxiv.zip: main.tex, thesis.sty,
main.bbl, references.bib, every chapter, and only the figures the chapters use.
arXiv compiles the zip with pdfLaTeX.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPHIC_EXTS = (".pdf", ".png", ".jpg", ".jpeg")
SKIP = shutil.ignore_patterns(".git", "dist", "plots", "tools", "*.md", "LICENSE", ".gitignore")


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def strip_comments(tex):
    return re.sub(r"(?<!\\)%.*", "", tex)


def sources():
    """Every .tex file the document pulls in, starting from main.tex."""
    seen, todo = [], ["main.tex"]
    while todo:
        rel = todo.pop()
        if rel in seen:
            continue
        seen.append(rel)
        tex = strip_comments(read(os.path.join(ROOT, rel)))
        for _, name in re.findall(r"\\(input|include)\{([^}]+)\}", tex):
            child = name if name.endswith(".tex") else name + ".tex"
            if os.path.exists(os.path.join(ROOT, child)):
                todo.append(child)
    return seen


def graphics(tex_files):
    found = []
    for rel in tex_files:
        tex = strip_comments(read(os.path.join(ROOT, rel)))
        for name in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex):
            base, ext = os.path.splitext(name)
            candidates = [name] if ext else [base + e for e in GRAPHIC_EXTS]
            hit = next((c for c in candidates if os.path.exists(os.path.join(ROOT, c))), None)
            if hit is None:
                sys.exit(f"missing graphic: {name} (in {rel})")
            if hit not in found:
                found.append(hit)
    return found


def run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        sys.stdout.write(result.stdout[-4000:] + result.stderr[-4000:])
        sys.exit(f"failed: {' '.join(cmd)}")


def report(log):
    for pattern in (r"^! .*", r"LaTeX Warning: (?:Reference|Citation) .* undefined.*",
                    r"Package natbib Warning: Citation .* undefined.*", r"^Overfull \\hbox.*",
                    r"LaTeX Font Warning: .*"):
        for line in re.findall(pattern, log, flags=re.M):
            print("warning:", line)


def build(args, outdir):
    with tempfile.TemporaryDirectory() as tmp:
        if args.texbin:
            work = os.path.join(tmp, "src")
            shutil.copytree(ROOT, work, ignore=SKIP)
            exe = ".exe" if os.name == "nt" else ""
            pdflatex = [os.path.join(args.texbin, "pdflatex" + exe), "-interaction=nonstopmode",
                        "-halt-on-error", "main.tex"]
            run(pdflatex, work)
            run([os.path.join(args.texbin, "bibtex" + exe), "main"], work)
            run(pdflatex, work)
            run(pdflatex, work)
        else:
            work = tmp
            run([args.tectonic, os.path.join(ROOT, "main.tex"), "--outdir", tmp,
                 "--keep-intermediates", "--keep-logs"], ROOT)
        report(read(os.path.join(work, "main.log")))
        shutil.copy(os.path.join(work, "main.pdf"), os.path.join(outdir, "peertocp-thesis.pdf"))
        shutil.copy(os.path.join(work, "main.bbl"), os.path.join(ROOT, "main.bbl"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--texbin", help="directory with pdflatex and bibtex (TeX Live)")
    parser.add_argument("--tectonic", default=shutil.which("tectonic") or "tectonic")
    parser.add_argument("--out", default=os.path.join(ROOT, "dist"))
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    build(args, args.out)
    tex = sources()
    files = tex + ["thesis.sty", "main.bbl", "references.bib"] + graphics(tex)
    zip_path = os.path.join(args.out, "peertocp-thesis-arxiv.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            z.write(os.path.join(ROOT, rel), rel.replace(os.sep, "/"))
    size = os.path.getsize(zip_path)
    print(f"{len(files)} files, {size / 1e6:.1f} MB -> {zip_path}")
    print(f"pdf -> {os.path.join(args.out, 'peertocp-thesis.pdf')}")


if __name__ == "__main__":
    main()
