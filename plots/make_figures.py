#!/usr/bin/env python3
"""Benchmark charts for the English edition of the PeerToCP thesis.

Redraws the nine benchmark charts of the thesis as vector PDFs and adds three
summary charts, all from the raw benchmark data
(https://github.com/hockyy/peertocp-benchmark) with the processing of that
repository's notebook, benchmark-vis.ipynb:

* resource charts (notebook cell 1): netdata samples between 10 s before the
  test start and 10 s after its end; the mean covers the first MEAN_WINDOW
  seconds of the test; memory is shown relative to the sample 1 s before the
  start;
* latency charts (cells 7, 9, 12, 13): each peer's latencies keyed by the time
  they were logged, in ms after that peer's first one; latencies logged at the
  same offset on different peers are pooled; the mean is the mean over offsets
  of each offset's mean; the line is each offset's median, thinned out.

    python make_figures.py DATA_DIR [--out FIG_DIR] [--check]

DATA_DIR is a checkout of peertocp-benchmark. FIG_DIR defaults to ../figures
next to this script. --check also recomputes every row of the repository's
summary CSVs (log-scenario-*.csv) and prints how far off it is.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import datetime as dt
import functools
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter  # noqa: E402

# --------------------------------------------------------------- the benchmark

PEER_COUNTS = (2, 4, 8)
VARIANTS = ("crdt-cs", "crdt-p2p", "ot")
# netdata recorded peer 1, peer 2 and the server of every run. The client-server
# CRDT server's files are named crdt-cs in scenario 1 and crdt-ws in the others.
MONITORED_PEERS = (1, 2)
SERVER_FILES = {"crdt-cs": ("crdt-cs", "crdt-ws"), "crdt-p2p": ("crdt-p2p",), "ot": ("ot-ws",)}
# The means cover the first MEAN_WINDOW[s] seconds of scenario s (notebook: test_duration).
MEAN_WINDOW = {1: 200, 2: 110, 3: 130, 4: 120}
# Memory is shown relative to the 10th sample, 1 s before the test start.
MEM_BASELINE_INDEX = 9
# netdata logs sent traffic as negative kbit/s; the charts show the rate sent.
SENT_AS_POSITIVE = True

METRICS = {  # metric: (netdata CSV prefix, column)
    "cpu": ("cpu", 1),
    "mem": ("mem", 1),
    "net-in": ("network", 1),
    "net-out": ("network", 2),
}

# -------------------------------------------------------------------- the look

NAME = {"crdt-cs": "Client-server CRDT", "crdt-p2p": "Peer-to-peer CRDT", "ot": "Client-server OT"}
SERVER_NAME = {"crdt-cs": "server", "crdt-p2p": "signaling server", "ot": "server"}
# Okabe-Ito blue, vermillion and bluish green: the notebook's blue/orange/green, colorblind-safe.
COLOR = {"crdt-cs": "#0072B2", "crdt-p2p": "#D55E00", "ot": "#009E73"}
PEER_STYLE = {1: "-", 2: (0, (3.5, 1.5))}
YLABEL = {
    "cpu": "CPU utilization (% of one core)",
    "mem": "Memory, relative to start (MiB)",
    "net-in": "Network in (kbit/s)",
    "net-out": "Network out (kbit/s)",
    "latency": "Latency (ms)",
}
WIDTH = 6.3  # inches: the 16 cm text width

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "axes.edgecolor": "#555555",
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "axes.grid": True,
    "grid.color": "#dddddd",
    "grid.linewidth": 0.5,
    "axes.axisbelow": True,
    "legend.frameon": False,
    "legend.handlelength": 2.6,
    "legend.columnspacing": 1.6,
    "pdf.fonttype": 42,  # TrueType fonts, no Type 3
    "savefig.dpi": 300,
})

NOTES: dict[str, None] = {}  # oddities met while reading the data, in order


def note(text: str) -> None:
    NOTES.setdefault(text, None)


# ---------------------------------------------------------------- reading data

LOG_TIME = "%Y-%m-%d %H:%M:%S.%f"


def log_seconds(stamp: str) -> int:
    """A log timestamp ("2022-11-02 18:04:00.001", UTC) in whole seconds."""
    return calendar.timegm(dt.datetime.strptime(stamp, LOG_TIME).timetuple())


def log_millis(stamp: str) -> int:
    t = dt.datetime.strptime(stamp, LOG_TIME)
    return (calendar.timegm(t.timetuple()) * 1_000_000 + t.microsecond) // 1000


def run_dir(data: Path, scenario: int, n: int, variant: str) -> Path:
    return data / f"s{scenario}" / f"n{n:02}" / variant


@functools.lru_cache(maxsize=None)
def peer_log(data: Path, scenario: int, n: int, variant: str, peer: int) -> str:
    logs = sorted((run_dir(data, scenario, n, variant) / f"peer-{peer}").glob("*.log"))
    if len(logs) != 1:
        sys.exit(f"expected one log in {run_dir(data, scenario, n, variant) / f'peer-{peer}'}, found {len(logs)}")
    return logs[0].read_text(encoding="utf-8", errors="replace")


@functools.lru_cache(maxsize=None)
def test_period(data: Path, scenario: int, n: int, variant: str) -> tuple[int, int]:
    """Start and end of a run in UTC seconds, from its peers' logs.

    Every peer logs the same "Test Start" second. The end is the latest "Exit
    Test"; a peer without one, or more than 10 s before the latest so far, is
    noted (the notebook printed "Doesn't end!" for both)."""
    run = f"s{scenario}/n{n:02}/{variant}"
    start = end = None
    for peer in range(1, n + 1):
        text = peer_log(data, scenario, n, variant, peer)
        found = re.search(r"\[(.+?)\].+Test Start", text)
        if found is None:
            sys.exit(f"{run}/peer-{peer}: no 'Test Start' line")
        peer_start = log_seconds(found.group(1))
        start = peer_start if start is None else start
        if peer_start != start:
            sys.exit(f"{run}: peers started at different seconds ({start}, {peer_start})")
        found = re.search(r"\[(.+?)\].+Exit Test", text)
        if found is None:
            note(f"{run}/peer-{peer}: no 'Exit Test' line (the run did not end on this peer)")
            continue
        peer_end = log_seconds(found.group(1))
        end = peer_end if end is None else max(end, peer_end)
        if end - peer_end > 10:
            note(f"{run}/peer-{peer}: exited {end - peer_end} s before an earlier peer")
    if end is None:
        sys.exit(f"{run}: no peer logged 'Exit Test'")
    return start, end


@functools.lru_cache(maxsize=None)
def resource_series(data: Path, scenario: int, n: int, variant: str, metric: str) -> dict:
    """{instance: (x, y)} of one netdata metric of a run (notebook cell 1).

    Instances are "peer-1", "peer-2" and "server". x is in seconds after 10 s
    before the test start, so the test starts at x = 10."""
    start, end = test_period(data, scenario, n, variant)
    prefix, column = METRICS[metric]
    x_min, x_max = start - 10, end + 10
    series = {}
    for path in sorted(run_dir(data, scenario, n, variant).glob(f"{prefix}-*.csv")):
        instance = re.fullmatch(rf"{prefix}-(.+?)\.csv", path.name).group(1)
        if instance in SERVER_FILES[variant]:
            instance = "server"
        elif not re.fullmatch(r"peer-\d+", instance):
            note(f"s{scenario}/n{n:02}/{variant}: unexpected file {path.name}")
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))[1:]
        points = sorted((int(r[0]) - x_min, float(r[column])) for r in rows if x_min <= int(r[0]) <= x_max)
        x = np.array([p[0] for p in points], dtype=float)
        y = np.array([p[1] for p in points], dtype=float)
        if metric == "mem":
            y = y - y[MEM_BASELINE_INDEX]
        series[instance] = (x, y)
    return series


def in_window(x: np.ndarray, y: np.ndarray, scenario: int) -> np.ndarray:
    return y[(x >= 10) & (x <= 10 + MEAN_WINDOW[scenario])]


def own_id(text: str, scenario: int) -> str:
    """The id a peer tags its own updates with: of its text (scenario 3) or its shell (4)."""
    marker = "Inserting test" if scenario == 3 else "spawning"
    own = None
    for line in text.split("\n"):
        if marker in line:
            own = line.split()[-1]
    if own is None:
        sys.exit(f"a scenario {scenario} log has no '{marker}' line")
    return own


def logged_latency(line: str, scenario: int) -> tuple[str, int, int] | None:
    """(source id, latency ms, logged at ms) of a latency line, else None.

    Scenario 3 lines end "<ms> <source id>", scenario 4 lines "shellProcess,<source id>,<ms>"."""
    words = line.split()
    try:
        if scenario == 3:
            source, latency = words[-1], int(words[-2])
        else:
            fields = words[-1].split(",")
            source = fields[1]
            if fields[0] != "shellProcess":
                return None
            latency = int(fields[2])
        logged = log_millis((words[0] + " " + words[1]).strip("[").strip("]"))
    except (IndexError, ValueError):
        return None
    return source, latency, logged


@functools.lru_cache(maxsize=None)
def latency_by_offset(data: Path, scenario: int, n: int, variant: str, own: bool) -> dict:
    """{offset ms: [latency ms, ...]} of a run, pooled over its n peers.

    own=False keeps the updates a peer received from the others, own=True the
    ones it made itself. A peer's offsets count from its own first latency; a
    second latency logged in the same ms on one peer replaces the first."""
    test_period(data, scenario, n, variant)  # the peers' start check
    pooled: dict[int, list[int]] = {}
    for peer in range(1, n + 1):
        text = peer_log(data, scenario, n, variant, peer)
        me = own_id(text, scenario)
        latest: dict[int, int] = {}
        for line in text.split("\n"):
            parsed = logged_latency(line, scenario)
            if parsed is not None and (parsed[0] == me) == own:
                latest[parsed[2]] = parsed[1]
        times = sorted(latest)
        for t in times:
            pooled.setdefault(t - times[0], []).append(latest[t])
    return pooled


def thinning_step(scenario: int, n: int, own: bool) -> int:
    """Every how many offsets the latency line is drawn (notebook cells 7, 9, 12, 13)."""
    if not own:
        return int(n ** 2.5) // 5
    return int(n ** 1.5) // 2 if scenario == 3 else 1


def latency_stats(pooled: dict) -> dict:
    per_offset = [float(np.average(pooled[t])) for t in sorted(pooled)]
    return {
        "avg": float(np.average(per_offset)),
        "med": float(np.median(per_offset)),
        "p90": float(np.percentile(per_offset, 90)),
        "max": float(np.max(per_offset)),
        "min": float(np.min(per_offset)),
    }


# ------------------------------------------------------------------- the charts

def mean_text(value: float) -> str:
    return f"mean {value:,.2f}" if abs(value) < 1 else f"mean {value:,.1f}"


def sign(metric: str) -> float:
    return -1.0 if metric == "net-out" and SENT_AS_POSITIVE else 1.0


def log_axis(ax) -> None:
    """A log y axis with plain-number labels at the decades (network rates span 10 to 10^6 kbit/s)."""
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 1 else f"{v:g}"))
    ax.yaxis.set_minor_formatter(NullFormatter())


def save(fig, out: Path, name: str) -> Path:
    path = out / name
    fig.savefig(path, metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)
    print(f"wrote {path}")
    return path


def resource_figure(data: Path, out: Path, name: str, scenario: int, n: int, metric: str,
                    side: str, log: bool = False) -> dict:
    """One netdata metric over time for the monitored peers (side="peers") or the servers."""
    fig, ax = plt.subplots(figsize=(WIDTH, 3.4), layout="constrained")
    handles, means = [], {}
    instances = [f"peer-{p}" for p in MONITORED_PEERS] if side == "peers" else ["server"]
    for variant in VARIANTS:
        series = resource_series(data, scenario, n, variant, metric)
        for instance in instances:
            x, y = series[instance]
            mean = float(np.average(in_window(x, y, scenario)))
            means[(variant, instance)] = mean
            if side == "peers":
                peer = int(instance.split("-")[1])
                label = f"{NAME[variant]}, peer {peer} ({mean_text(sign(metric) * mean)})"
                style, width = PEER_STYLE[peer], 0.9
            else:
                label = f"{NAME[variant]} {SERVER_NAME[variant]} ({mean_text(sign(metric) * mean)})"
                style, width = "-", 1.1
            (line,) = ax.plot(x - 10, sign(metric) * y, color=COLOR[variant], linestyle=style,
                              linewidth=width, label=label)
            handles.append(line)
    ax.set_xlabel("Time since test start (s)")
    ax.set_ylabel(YLABEL[metric])
    ax.set_xticks(np.arange(0, 300, 30))
    ax.set_xlim(-10, max(h.get_xdata().max() for h in handles))
    if log:
        log_axis(ax)
    # Legend above the plot: one column per monitored peer, one row per variant.
    ncol = len(instances) if side == "peers" else 1
    order = [handles[i * len(instances) + j] for j in range(len(instances)) for i in range(len(VARIANTS))]
    fig.legend(handles=order, loc="outside upper left", ncol=ncol)
    save(fig, out, name)
    return means


def latency_figure(data: Path, out: Path, name: str, scenario: int, n: int, own: bool) -> dict:
    """Latency over a run, per variant: each offset's median, thinned out as in the notebook."""
    fig, ax = plt.subplots(figsize=(WIDTH, 3.4), layout="constrained")
    stats, end = {}, 0.0
    step = thinning_step(scenario, n, own)
    for variant in VARIANTS:
        pooled = latency_by_offset(data, scenario, n, variant, own)
        stats[variant] = latency_stats(pooled)
        offsets = sorted(pooled)[::step]
        medians = [float(np.median(pooled[t])) for t in offsets]
        ax.plot(np.array(offsets) / 1000, medians, color=COLOR[variant], linewidth=0.6 if step == 1 else 0.9,
                label=f"{NAME[variant]} ({mean_text(stats[variant]['avg'])})")
        end = max(end, offsets[-1] / 1000)
    ax.set_xlabel("Time since first update (s)")
    ax.set_ylabel(YLABEL["latency"])
    ax.set_xticks(np.arange(0, end + 1, 10))
    ax.set_xlim(0, end)
    ax.set_ylim(bottom=0)
    fig.legend(loc="outside upper left", ncol=2)
    save(fig, out, name)
    return stats


def n_axis(ax) -> None:
    ax.set_xscale("log", base=2)
    ax.set_xticks(PEER_COUNTS, [str(n) for n in PEER_COUNTS])
    ax.minorticks_off()
    ax.set_xlim(1.7, 9.4)
    ax.grid(axis="x", visible=False)


def variant_legend(fig, extra: list | None = None) -> None:
    handles = [Line2D([], [], color=COLOR[v], marker="o", markersize=4.5, linewidth=1.4, label=NAME[v])
               for v in VARIANTS] + (extra or [])
    fig.legend(handles=handles, loc="outside upper center", ncol=len(handles),
               handlelength=2.0, columnspacing=1.2)


def summary_latency(data: Path, out: Path) -> dict:
    """Mean latency against n: scenarios 3 and 4, updates from the others and own updates."""
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, 4.6), layout="constrained", sharex=True)
    panels = [
        (3, False, "(a) Scenario 3, text editor: from other users"),
        (3, True, "(b) Scenario 3, text editor: own updates"),
        (4, False, "(c) Scenario 4, shell: from other users"),
        (4, True, "(d) Scenario 4, shell: own updates"),
    ]
    values = {}
    for ax, (scenario, own, title) in zip(axes.flat, panels):
        for variant in VARIANTS:
            means = [latency_stats(latency_by_offset(data, scenario, n, variant, own))["avg"] for n in PEER_COUNTS]
            values[(scenario, own, variant)] = means
            ax.plot(PEER_COUNTS, means, color=COLOR[variant], marker="o", markersize=4.5, linewidth=1.4)
        ax.set_title(title, loc="left")
        ax.set_ylim(bottom=0)
        n_axis(ax)
    for ax in axes[:, 0]:
        ax.set_ylabel("Mean latency (ms)")
    for ax in axes[1]:
        ax.set_xlabel("Number of users $n$")
    variant_legend(fig)
    save(fig, out, "summary-latency.pdf")
    return values


def summary_resources(data: Path, out: Path, side: str, log_metrics: tuple, scenario: int = 1) -> dict:
    """Mean resource use against n in one scenario: the monitored clients' mean or the server.

    The metrics in log_metrics, which span orders of magnitude, get a log axis."""
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, 4.6), layout="constrained", sharex=True)
    panels = [("cpu", "(a) CPU"), ("mem", "(b) Memory"), ("net-in", "(c) Network in"), ("net-out", "(d) Network out")]
    dodge = {"crdt-cs": 2 ** -0.06, "crdt-p2p": 1.0, "ot": 2 ** 0.06}
    values = {}
    for ax, (metric, title) in zip(axes.flat, panels):
        lowest = np.inf
        for variant in VARIANTS:
            per_n = []
            for n in PEER_COUNTS:
                series = resource_series(data, scenario, n, variant, metric)
                instances = [f"peer-{p}" for p in MONITORED_PEERS] if side == "clients" else ["server"]
                per_n.append([sign(metric) * float(np.average(in_window(*series[i], scenario))) for i in instances])
            values[(metric, variant)] = per_n
            lowest = min(lowest, min(min(v) for v in per_n))
            xs = [n * dodge[variant] for n in PEER_COUNTS]
            ax.plot(xs, [np.mean(v) for v in per_n], color=COLOR[variant], marker="o", markersize=4.5,
                    linewidth=1.4, zorder=3)
            if side == "clients":  # the two monitored clients, joined
                ax.vlines(xs, [min(v) for v in per_n], [max(v) for v in per_n], color=COLOR[variant],
                          linewidth=0.9, alpha=0.55, zorder=2)
        ax.set_title(title, loc="left")
        ax.set_ylabel(YLABEL[metric])
        if metric in log_metrics:
            log_axis(ax)
            ax.set_ylim(bottom=10 ** np.floor(np.log10(lowest)))  # start at a labelled decade
        elif ax.get_ylim()[0] > 0:
            ax.set_ylim(bottom=0)
        n_axis(ax)
    for ax in axes[1]:
        ax.set_xlabel("Number of users $n$")
    extra = []
    if side == "clients":
        extra = [Line2D([], [], color="#777777", linestyle="None", marker="|", markersize=9,
                        markeredgewidth=0.9, label="range of clients 1 and 2")]
    variant_legend(fig, extra)
    save(fig, out, f"summary-s{scenario}-{side}.pdf")
    return values


# ---------------------------------------------------------------- the figures

REDRAWS = [  # original PNG, new PDF, chart
    ("bench-c2-o19.png", "s1-n8-peers-cpu.pdf", ("resource", 1, 8, "cpu", "peers", False)),
    ("bench-c2-o21.png", "s1-n8-peers-memory.pdf", ("resource", 1, 8, "mem", "peers", False)),
    ("bench-c2-o23.png", "s1-n8-peers-network-in.pdf", ("resource", 1, 8, "net-in", "peers", False)),
    ("bench-c2-o24.png", "s1-n8-server-network-in.pdf", ("resource", 1, 8, "net-in", "server", True)),
    ("bench-c2-o25.png", "s1-n8-peers-network-out.pdf", ("resource", 1, 8, "net-out", "peers", True)),
    ("bench-c7-o5.png", "s3-n8-latency-others.pdf", ("latency", 3, 8, False)),
    ("bench-c9-o5.png", "s4-n8-latency-others.pdf", ("latency", 4, 8, False)),
    ("bench-c12-o5.png", "s3-n8-latency-self.pdf", ("latency", 3, 8, True)),
    ("bench-c13-o5.png", "s4-n8-latency-self.pdf", ("latency", 4, 8, True)),
]


def make_all(data: Path, out: Path) -> None:
    for _png, pdf, chart in REDRAWS:
        if chart[0] == "resource":
            resource_figure(data, out, pdf, *chart[1:])
        else:
            latency_figure(data, out, pdf, *chart[1:])
    summary_latency(data, out)
    summary_resources(data, out, "clients", log_metrics=("net-out",))
    summary_resources(data, out, "server", log_metrics=("net-in", "net-out"))


# ------------------------------------------------------------------- the check

def check(data: Path) -> bool:
    """Recompute every row of the repository's summary CSVs; print the worst difference."""
    worst, rows = 0.0, 0
    parameter = {"cpu": "cpu", "mem": "mem", "network-in": "net-in", "network-out": "net-out"}
    for scenario in (1, 2, 3, 4):
        with (data / f"log-scenario-{scenario}.csv").open(newline="", encoding="utf-8") as f:
            for row in list(csv.DictReader(f)):
                peers = row["parameter"].endswith("-peers")
                metric = parameter[row["parameter"].removesuffix("-peers")]
                n, instance = int(row["peer number"]), row["instance"]
                if peers:
                    variant = next(v for v in VARIANTS if instance.endswith("-" + v))
                    key = instance.removesuffix("-" + variant)
                else:
                    variant = next(v for v in VARIANTS if instance in SERVER_FILES[v])
                    key = "server"
                y = in_window(*resource_series(data, scenario, n, variant, metric)[key], scenario)
                ours = {"avg": np.average(y), "med": np.median(y), "max": np.max(y), "min": np.min(y)}
                for stat, value in ours.items():
                    worst = max(worst, abs(value - float(row[stat])))
                rows += 1
    for scenario, word in ((3, "three"), (4, "four")):
        for own, kind in ((False, "latency"), (True, "self-latency")):
            with (data / f"log-scenario-{word}-{kind}.csv").open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    stats = latency_stats(latency_by_offset(data, scenario, int(row["peer number"]), row["instance"], own))
                    for stat, column in (("avg", "avg"), ("med", "med"), ("p90", "90th percentile"),
                                         ("max", "max"), ("min", "min")):
                        worst = max(worst, abs(stats[stat] - float(row[column])))
                    rows += 1
    ok = worst < 1e-6
    print(f"check: {rows} rows of the summary CSVs recomputed, largest difference {worst:.3g}"
          + ("" if ok else "  <-- MISMATCH"))
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("data", type=Path, help="checkout of github.com/hockyy/peertocp-benchmark")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "figures",
                        help="folder for the PDFs (default: ../figures)")
    parser.add_argument("--check", action="store_true", help="recompute the repository's summary CSVs")
    args = parser.parse_args()
    data = args.data.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    make_all(data, args.out)
    ok = check(data) if args.check else True
    for text in NOTES:
        print(f"note: {text}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
