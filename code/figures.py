# Графики для работы из таблиц в папке data.
# Запуск: python figures.py data папка_для_картинок

import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

FONTS = "/System/Library/Fonts/Supplemental/"
if os.path.exists(FONTS + "Times New Roman.ttf"):
    for f in ("Times New Roman.ttf", "Times New Roman Italic.ttf"):
        font_manager.fontManager.addfont(FONTS + f)
    plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams.update({"font.size": 12, "axes.linewidth": 0.8, "axes.grid": True, "grid.alpha": 0.3, "savefig.dpi": 250,
                     "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "legend.fontsize": 10})
COLORS = ["#1f4e79", "#c0504d", "#4f9a3a", "#8064a2", "#e08a1e"]
TILT = {"main": 2, "angle_0": 0, "angle_5": 5, "angle_10": 10, "angle_20": 20}
comma = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",").replace("-", "−"))

data, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)


def motion(run):
    a = np.genfromtxt(f"{data}/motion_{run}.csv", delimiter=";", skip_header=1, usecols=range(17))
    return a[:, 1], a[:, 10], -(TILT[run] + a[:, 14])


def gauge(point):
    a = np.genfromtxt(f"{data}/gauges_main_{point}.csv", delimiter=";", skip_header=4, usecols=(1, 2))
    return a[:, 0], (a[:, 1] - 0.151) * 1e3


def save(fig, ax, name):
    ax.xaxis.set_major_formatter(comma); ax.yaxis.set_major_formatter(comma)
    fig.tight_layout(); fig.savefig(f"{out}/{name}.png"); plt.close(fig)


fig, ax = plt.subplots(figsize=(4.6, 2.6))
t, z, _ = motion("main"); t2, z2, _ = motion("angle_0"); z_eq = z[-50:].mean()
ax.plot(t, (z - z_eq) * 1e3, COLORS[0], lw=1.3, label="DualSPHysics, частицы 2 мм")
ax.plot(t2, (z2 - z_eq) * 1e3, COLORS[1], lw=1.0, ls="--", label="DualSPHysics, частицы 2,5 мм")
of = np.loadtxt(f"{data}/heave_openfoam.csv", delimiter=",", skiprows=1)
ax.plot(of[:, 0] + 1.27, of[:, 1] * 1e3, COLORS[2], lw=1.2, label="OpenFOAM (старт на 1,27 с)")
ax.set_xlim(0, 4.2); ax.set_ylim(-45, 60)
ax.set_xlabel("t, с"); ax.set_ylabel("от равновесия, мм"); ax.legend()
save(fig, ax, "f_heave")

fig, ax = plt.subplots(figsize=(4.6, 2.6))
for color, (run, label) in zip(COLORS, (("angle_0", "0°"), ("main", "2°"), ("angle_5", "5°"), ("angle_10", "10°"), ("angle_20", "20°"))):
    t, _, tilt = motion(run)
    ax.plot(t[t <= 2.5], tilt[t <= 2.5], color=color, lw=1.2, label=label)
ax.set_xlabel("t, с"); ax.set_ylabel("наклон оси, °")
ax.legend(ncol=5, loc="lower center", bbox_to_anchor=(0.5, 0.98), title="начальный наклон", title_fontsize=10,
          handlelength=1.2, columnspacing=1.0)
save(fig, ax, "f_tilt")

fig, ax = plt.subplots(figsize=(4.6, 2.6))
ta, ha = gauge("a"); tb, hb = gauge("b")
ax.plot(ta, ha, COLORS[1], lw=1.0, label="у ободка, r = 65 мм")
ax.plot(tb, hb, COLORS[0], lw=1.2, label="у стенки бака, r = 85 мм")
ax.axhline(5.8, color="0.35", lw=0.9, ls=":", label="подъём на 188 см³ (5,8 мм)")
ax.set_xlim(0, 4.2); ax.set_ylim(-6, 32)
ax.set_xlabel("t, с"); ax.set_ylabel("уровень воды, мм"); ax.legend(loc="upper right")
save(fig, ax, "f_waves")

fig, ax = plt.subplots(figsize=(4.6, 2.6))
for color, (edge, label) in zip(COLORS, (("sharp", "острая кромка"), ("round", "скруглённая, R = 1,4 мм"))):
    a = np.loadtxt(f"{data}/fill_{edge}.csv", delimiter=",", skiprows=1)
    ax.plot(a[:, 0], a[:, 1] * 100, color=color, lw=1.3, label=label)
ax.set_xlim(0, 1.0); ax.set_ylim(0, 115)
ax.set_xlabel("t, с"); ax.set_ylabel("уровень внутри, %"); ax.legend(loc="lower right")
save(fig, ax, "f_vortex")

fig, ax = plt.subplots(figsize=(4.6, 2.6))
v = np.genfromtxt(f"{data}/validation_cylinder.csv", delimiter=";", skip_header=1)
ref = np.loadtxt(f"{data}/reference_fekken2004.txt", skiprows=2)
m = v[:, 1] >= 1.0
ax.plot(ref[:, 0], ref[:, 1], "o", ms=2.2, color=COLORS[0], label="эталонное решение")
ax.plot((v[m, 1] - 1.0) * np.sqrt(9.81), v[m, 10] - v[0, 10], color=COLORS[1], lw=1.4, label="DualSPHysics")
ax.set_xlim(0, 8); ax.set_ylim(-4.2, 0.3)
ax.set_xlabel("t·√(g/R)"); ax.set_ylabel("смещение центра / R"); ax.legend()
save(fig, ax, "f_valid")

fig, ax = plt.subplots(figsize=(4.6, 2.6))
s = np.loadtxt(f"{data}/sinking_openfoam.csv", delimiter=",", skiprows=1)
h1, = ax.plot(s[:, 0], (s[:, 1] - 0.2253) * 1e3, COLORS[0], lw=1.3, label="высота воронки")
ax.set_xlabel("t, с"); ax.set_ylabel("от равновесия, мм"); ax.set_ylim(-16, 24)
right = ax.twinx()
h2, = right.plot(s[:, 0], s[:, 2], COLORS[1], lw=1.3, label="вода внутри")
right.set_ylabel("вода внутри, см³"); right.set_ylim(0, 100); right.grid(False)
right.spines["right"].set_visible(True); right.yaxis.set_major_formatter(comma)
ax.legend(handles=[h1, h2], loc="upper right", ncol=2)
save(fig, ax, "f_open")
