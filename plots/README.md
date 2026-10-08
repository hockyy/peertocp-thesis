# Benchmark charts

`make_figures.py` draws the benchmark charts of the English edition as vector
PDFs in `../figures/`, from the raw benchmark data of
<https://github.com/hockyy/peertocp-benchmark> (netdata CSVs and the peers'
logs). It reproduces the processing of that repository's notebook,
`benchmark-vis.ipynb`; `--check` recomputes every row of the repository's
summary CSVs (`log-scenario-*.csv`) and prints the largest difference (0 today).
It needs only Python 3.9+, numpy and matplotlib 3.7+.

```sh
git clone https://github.com/hockyy/peertocp-benchmark
python make_figures.py peertocp-benchmark --check
```

## What it makes

| PDF | Chart | Replaces |
|---|---|---|
| `s1-n8-peers-cpu.pdf` | Scenario 1, n = 8: CPU of clients 1 and 2 | `bench-c2-o19.png` |
| `s1-n8-peers-memory.pdf` | Scenario 1, n = 8: memory of clients 1 and 2 | `bench-c2-o21.png` |
| `s1-n8-peers-network-in.pdf` | Scenario 1, n = 8: data received by clients 1 and 2 | `bench-c2-o23.png` |
| `s1-n8-server-network-in.pdf` | Scenario 1, n = 8: data received by the servers (log scale) | `bench-c2-o24.png` |
| `s1-n8-peers-network-out.pdf` | Scenario 1, n = 8: data sent by clients 1 and 2 (log scale) | `bench-c2-o25.png` |
| `s3-n8-latency-others.pdf` | Scenario 3, n = 8: latency of updates from the other users | `bench-c7-o5.png` |
| `s4-n8-latency-others.pdf` | Scenario 4, n = 8: latency of updates from the other users | `bench-c9-o5.png` |
| `s3-n8-latency-self.pdf` | Scenario 3, n = 8: latency of a user's own updates | `bench-c12-o5.png` |
| `s4-n8-latency-self.pdf` | Scenario 4, n = 8: latency of a user's own updates | `bench-c13-o5.png` |
| `summary-latency.pdf` | Mean latency against n, scenarios 3 and 4, from others and own | new (Tables `tab:latency-3`, `tab:latency-4`) |
| `summary-s1-clients.pdf` | Scenario 1: mean CPU, memory, network in and out of the clients against n | new (Table `tab:resource-client-1`) |
| `summary-s1-server.pdf` | Scenario 1: the same for the server (signaling server for P2P CRDT) | new (Table `tab:resource-server-1`) |

## How the numbers are made

- **Resources** (cell 1 of the notebook): netdata recorded clients 1 and 2 and
  the server of every run, once a second. Time 0 is the "Test Start" line of the
  peers' logs; a chart spans 10 s before it to 10 s after the last "Exit Test".
  A mean covers the first 200, 110, 130 and 120 s of scenarios 1 to 4. Memory is
  relative to the sample 1 s before the start. Network is netdata's `system.ip`
  (the whole machine) in kbit/s. netdata logs sent data as negative numbers (the
  tables in Chapter 5 keep that sign); the charts show the rate sent as a
  positive number (`SENT_AS_POSITIVE` in the script).
- **Latency** (cells 7, 9, 12, 13): every peer logs a latency for each update it
  applies, tagged with the user who made it. A peer's latencies are keyed by when
  they were logged, in ms after its first one, and pooled across peers at equal
  offsets. The mean is the mean over offsets of each offset's mean; the line
  shows each offset's median for every k-th offset only (k = 36 for "from others"
  at n = 8, 11 for scenario 3's own updates, every offset for scenario 4's).
- Each summary chart's points are those same means; a client point is the mean
  of clients 1 and 2 (as in Table `tab:resource-client-1`), its thin bar the two
  clients' values.

Colors are fixed per variant everywhere: client-server CRDT blue, peer-to-peer
CRDT vermillion, client-server OT green (Okabe-Ito, colorblind-safe). Charts are
6.3 in (16 cm) wide, with no title: the caption carries the scenario and n.
