# English edition: notes

The Indonesian original is [hockyy/skripsi](https://github.com/hockyy/skripsi)
(`thesis.tex`, chapters in `src/01-body/`, figures in `assets/skripsi/`). This
repository is the English edition only. These notes record how it was made, so
later changes stay consistent.

## What changed from the original

- **Text:** translated into natural academic English, and restructured where
  English convention differs (the introduction's objectives and benefits became
  one section with a contribution list).
- **Corrections:** factual slips in the background chapters (Chapter 2, and
  Chapter 4's description of the libraries) were corrected, and the description
  of the experiments was checked against the code in
  [hockyy/peertocp](https://github.com/hockyy/peertocp) and the data in
  [hockyy/peertocp-benchmark](https://github.com/hockyy/peertocp-benchmark):
  Scenario 1 grows each document by about 5 characters per second (not 15),
  only the first two clients of each run were monitored, and the client-server
  CRDT server carries 1.4 to 2.6 times a peer's traffic (the original had the
  comparison the other way round). The experiments, their numbers and the
  conclusions are unchanged.
- **Figures:** every benchmark chart is redrawn from the raw data by
  `plots/make_figures.py` (same processing as the original notebook; its
  `--check` reproduces the original summary CSVs exactly), three summary charts
  were added, the figures with Indonesian text were redrawn in TikZ, and new
  diagrams and screenshots were added (below).
- **Omitted:** the cover, the approval, originality and publication-consent
  pages, and the Indonesian abstract.

## Conventions

- First person only in the acknowledgements; elsewhere "this thesis", "this
  study" or the passive. US spelling (behavior, signaling).
- English technical terms are not italicized (the original italicized them as
  foreign words). Italics mark emphasis and a term's first definition.
- The three variants are always "client-server OT", "client-server CRDT" and
  "peer-to-peer CRDT" (branches `ot-cs`, `crdt-cs`, `crdt-p2p`).
- Captions are sentences ending in a period; a caption longer than one sentence
  gets a short title for the lists: `\caption[Short title]{Full caption.}`.
- Tables use `booktabs` (no vertical rules); numbers of 1,000 and more get a
  thousands separator (`12{,}962.05`); outgoing network rates are positive.
- Labels keep the original keys (`bab:2`, `sec:evaluasi`, `fig:2-23`, ...).

## Figures

| File | Origin |
|---|---|
| `rich-text.tex`, `research-flow.tex`, `activity-diagram.tex` | TikZ redraws of `richtext.jpg`, `Metode_Penelitian.pdf`, `Activity_Diagram.pdf` |
| `webrtc-signaling.tex`, `crdt-insert.tex`, `components.tex`, `request-run.tex` | New TikZ diagrams |
| `app-main-window.png`, `app-shared-shell.png` | Screenshots from the PeerToCP README, cropped |
| `ot-transform.pdf`, `ot-snowball.pdf` | `OT.pdf`, `Snowball.pdf` |
| `arch-crdt-p2p.pdf`, `arch-crdt-cs.pdf`, `arch-ot-cs.pdf` | `Arsitektur_WebRTC_CRDT.pdf`, `Arsitektur_WebSocket_CRDT.pdf`, `Arsitektur_WebSocket_OT.pdf` |
| `ot-sync-1.png`, `ot-sync-2.png`, `crdt-sync-1..3.png`, `mesh-vs-star.png` | `ot1/2.png`, `crdt1..3.png`, `Compare.png` |
| `s1-*.pdf`, `s3-*.pdf`, `s4-*.pdf`, `summary-*.pdf` | Drawn by `plots/make_figures.py`; see [`plots/README.md`](plots/README.md) |

The TikZ figures are bare `tikzpicture`s pulled into a `figure` with
`\input{figures/<name>}`; they use the colors defined in `thesis.sty`
(`accent`, `accentlight`, `rulegray`, `codebg`).

## Glossary

| Indonesian | English |
|---|---|
| waktu nyata | real-time (adj.), in real time (adv.) |
| penyuntingan, menyunting | editing, edit |
| editor kode kolaboratif | collaborative code editor |
| *shell* bersama | shared shell |
| kelompok jaringan | network group |
| ruangan | room |
| pengguna | user |
| klien | client |
| *peer* / rekan | peer |
| replika data | data replica |
| konsistensi / konvergen | consistency / converge |
| resolusi (konflik) | (conflict) resolution |
| sumber daya, *resource* | resources (resource usage) |
| variasi (PeerToCP) | variant |
| pemrograman kompetitif | competitive programming |
| kompilasi, kompilator | compilation, compiler |
| skenario (pengujian) | (test) scenario |
| tolok ukur, *benchmarking* | benchmark, benchmarking |
| latensi | latency |
| skalabilitas | scalability |
| aspek *lightweight*, *correctness*, ... | the lightweight, correctness, ... aspect |
| sinkronisasi | synchronization |
| *signalling server* | signaling server |
| penelitian terkait | related work |
| saran | future work |
| studi literatur | literature review |
| rata-rata | mean |
