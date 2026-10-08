# PeerToCP: A WebRTC-Based Real-Time Collaborative Code Editor and Shared Shell

The English edition of my bachelor's thesis (Faculty of Computer Science,
Universitas Indonesia, December 2022; supervisor: Muhammad Hafizhuddin Hilman,
Ph.D.).

**[Download the PDF](https://github.com/hockyy/peertocp-thesis/releases/latest/download/peertocp-thesis.pdf)**

PeerToCP is a local-first collaborative code editor with a shared shell: one
user runs a program, and everyone in the room can type into it. The thesis
builds it three ways (client-server operational transformation, client-server
CRDT, and peer-to-peer CRDT over WebRTC) and benchmarks them with groups of 2,
4 and 8 users for correctness, latency, and CPU, memory and network use. The
peer-to-peer CRDT is the fastest for up to eight users and barely loads its
server; the client-server CRDT scales better with group size; the OT variant's
protocol saturates the network under heavy editing.

## Layout

| Path | What |
|---|---|
| `main.tex` | The thesis: title page, front matter, chapters, references |
| `thesis.sty` | Its look (Libertinus, colored headings, booktabs, listings) |
| `chapters/` | One file per chapter, plus abstract, acknowledgements and appendix |
| `figures/` | Figures: TikZ diagrams (`.tex`), charts (`.pdf`), screenshots (`.png`) |
| `plots/` | `make_figures.py`, which redraws every benchmark chart from the raw data |
| `references.bib` | Bibliography (APA style, via apacite) |
| `tools/package_arxiv.py` | Builds the PDF and the arXiv upload |
| `TRANSLATION_NOTES.md` | Glossary and conventions of the English edition |

## Building

With [Tectonic](https://tectonic-typesetting.github.io/) (it fetches packages
and runs BibTeX by itself):

```sh
tectonic main.tex
```

With TeX Live, as arXiv does: `pdflatex main`, `bibtex main`, then
`pdflatex main` twice.

`python tools/package_arxiv.py --texbin DIR` (the folder with TeX Live's
`pdflatex` and `bibtex`; or `--tectonic PATH`) builds
`dist/peertocp-thesis.pdf` and `dist/peertocp-thesis-arxiv.zip` (the sources,
`main.bbl` and only the figures in use) for upload.

The benchmark charts come from the raw measurements in
[peertocp-benchmark](https://github.com/hockyy/peertocp-benchmark); see
[`plots/README.md`](plots/README.md).

## The code

- [hockyy/peertocp](https://github.com/hockyy/peertocp): the application; one
  branch per variant (`crdt-p2p`, `crdt-cs`, `ot-cs`)
- [hockyy/y-webrtc](https://github.com/hockyy/y-webrtc) and
  [hockyy/y-websocket](https://github.com/hockyy/y-websocket): the modified Yjs
  network providers
- [hockyy/peertocp-ot-server](https://github.com/hockyy/peertocp-ot-server): the
  OT server
- [hockyy/peertocp-benchmark](https://github.com/hockyy/peertocp-benchmark): raw
  benchmark data and the original analysis notebook

## About this edition

The thesis was written and examined in Indonesian, as *PeerToCP: Editor Kode
dan Shared Shell Kolaboratif dalam Waktu Nyata Berbasis WebRTC*. This edition
was translated with the assistance of Claude (Anthropic) and checked by the
author. The study, its experiments and its results are unchanged. The edition
also corrects a few factual slips in the background chapters, redraws every
chart from the raw data, and adds explanatory diagrams and screenshots.

## License

© 2022, 2026 Hocky Yudhiono. The thesis, its figures and the scripts in this
repository are licensed under the [Creative Commons Attribution 4.0
International License](LICENSE) (CC BY 4.0).
