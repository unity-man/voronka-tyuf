# Трёхмерные расчёты в DualSPHysics 5.4 вместе с Project Chrono.
#
# Воронка стеклянная (плотность 2500 кг/м3), масса около 188 г:
#   горло: внутренний радиус 50 мм, конус 60 градусов (стенка под 30 градусов к оси);
#   носик: длина 50 мм, внутренний радиус 4 мм;
#   стенка: 4 мм.
# Бак 180 x 180 мм, высота 320 мм, вода глубиной 150 мм.
# В начале конец носика на 10 мм выше воды, воронку можно наклонить вокруг оси x.
#
# DSPH_HOME - папка DualSPHysics_v5.4 (в ней bin/linux и examples).
#
# Команды:
#   python dualsphysics.py case папка [частица_м] [время_с] [шаг_записи_с] [наклон_град]
#       файлы расчёта: funnel.stl, Funnel_Def.xml, run.sh; потом запустить папка/run.sh
#   python dualsphysics.py series
#       четыре расчёта с наклоном 0, 5, 10, 20 градусов (частица 2,5 мм, 2,5 с) и их обработка
#   python dualsphysics.py post папка
#       движение воронки (out/fi) и уровень воды в четырёх точках бака (out/gauges)
#   python dualsphysics.py video папка
#       видео основного расчёта: срез через ось и графики движения
#   python dualsphysics.py check папка_примера_11_Floating
#       видео проверочного расчёта: тяжёлый цилиндр падает в воду

import glob, math, os, shutil, struct, subprocess, sys
from multiprocessing import get_context
import numpy as np

DSPH = os.environ.get("DSPH_HOME", os.path.expanduser("~/DualSPHysics_v5.4"))
BIN = os.path.join(DSPH, "bin", "linux")
ENV = dict(os.environ, LD_LIBRARY_PATH=BIN)

RI, T, LS, RTOP = 0.004, 0.004, 0.050, 0.050
TA = math.tan(math.radians(30)); TC = T / math.cos(math.radians(30))
RO, HC = RI + T, (RTOP - RI) / TA
Z0, RHO_GLASS = 0.160, 2500.0
TX, TZ, HW = 0.09, 0.32, 0.150

CASE_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<case>
    <casedef>
        <constantsdef>
            <gravity x="0" y="0" z="-9.81" />
            <rhop0 value="1000" />
            <rhopgradient value="2" />
            <hswl value="0" auto="true" />
            <gamma value="7" />
            <speedsystem value="0" auto="true" />
            <coefsound value="10" />
            <speedsound value="0" auto="true" />
            <coefh value="1.0" />
            <cflnumber value="0.2" />
        </constantsdef>
        <mkconfig boundcount="240" fluidcount="9" />
        <geometry>
            <definition dp="{dp}">
                <pointmin x="{lo}" y="{lo}" z="-0.01" />
                <pointmax x="{hi}" y="{hi}" z="{top}" />
            </definition>
            <commands>
                <mainlist>
                    <setshapemode>actual | dp | bound</setshapemode>
                    <setdrawmode mode="full" />
                    <setmkfluid mk="0" />
                    <drawbox>
                        <boxfill>solid</boxfill>
                        <point x="{x0}" y="{x0}" z="0" />
                        <size x="{w}" y="{w}" z="{hw}" />
                    </drawbox>
                    <setmkbound mk="51" />
                    <drawfilestl file="funnel.stl" />
                    <shapeout file="funnel" />
                    <setmkbound mk="0" />
                    <drawbox>
                        <boxfill>all^top</boxfill>
                        <point x="{x0}" y="{x0}" z="0" />
                        <size x="{w}" y="{w}" z="{tz}" />
                    </drawbox>
                    <shapeout file="tank" />
                </mainlist>
            </commands>
        </geometry>
        <floatings>
            <floating mkbound="51" property="pvc">
                <massbody value="{mass:.5f}" />
            </floating>
        </floatings>
        <properties>
            <propertyfile file="Floating_Materials.xml" path="materials" />
            <links>
                <link mkbound="0" property="steel" />
            </links>
        </properties>
    </casedef>
    <execution>
        <special>
            <chrono>
                <savedata value="0.01" />
                <schemescale value="1" />
                <collision activate="true">
                    <distancedp value="0.5" />
                    <contactmethod value="0" />
                </collision>
                <bodyfloating id="funnel" mkbound="51" modelfile="AutoActual" />
                <bodyfixed id="tank" mkbound="0" modelfile="AutoActual" modelnormal="invert" />
            </chrono>
        </special>
        <parameters>
            <parameter key="SavePosDouble" value="0" />
            <parameter key="StepAlgorithm" value="2" />
            <parameter key="Kernel" value="2" />
            <parameter key="ViscoTreatment" value="1" />
            <parameter key="Visco" value="0.02" />
            <parameter key="ViscoBoundFactor" value="1" />
            <parameter key="DensityDT" value="2" />
            <parameter key="DensityDTvalue" value="0.1" />
            <parameter key="Shifting" value="0" />
            <parameter key="RigidAlgorithm" value="3" />
            <parameter key="FtPause" value="0.0" />
            <parameter key="DtIni" value="0" />
            <parameter key="DtMin" value="0" />
            <parameter key="DtAllParticles" value="0" />
            <parameter key="TimeMax" value="{tmax}" />
            <parameter key="TimeOut" value="{tout}" />
            <parameter key="PartsOutMax" value="1" />
            <parameter key="RhopOutMin" value="700" />
            <parameter key="RhopOutMax" value="1300" />
            <simulationdomain>
                <posmin x="default" y="default" z="default" />
                <posmax x="default" y="default" z="default + 20%" />
            </simulationdomain>
        </parameters>
    </execution>
</case>
"""

RUN_SH = """#!/bin/bash
cd "$(dirname "$0")"
B=${DSPH_HOME:-$HOME/DualSPHysics_v5.4}/bin/linux
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$B
$B/GenCase_linux64 Funnel_Def out/Funnel -save:all > log.gencase 2>&1 || exit 1
$B/DualSPHysics5.4_linux64 -gpu out/Funnel out > log.dsph 2>&1
"""


def make_case(case, dp=0.002, tmax=10.0, tout=0.04, tilt_deg=2.0):
    os.makedirs(case, exist_ok=True)
    zj = LS
    zjo = zj + (RO - RI - TC) / TA
    ztop = zj + HC
    poly = [(RI, 0.0), (RO, 0.0), (RO, zjo), (RTOP + TC, ztop), (RTOP, ztop), (RI, zj)]
    tris = []
    for i in range(len(poly)):
        (r1, z1), (r2, z2) = poly[i], poly[(i + 1) % len(poly)]
        for k in range(96):
            a0, a1 = 2 * math.pi * k / 96, 2 * math.pi * (k + 1) / 96
            P = lambda r, z, a: np.array([r * math.cos(a), r * math.sin(a), z])
            A, B, C, D = P(r1, z1, a0), P(r2, z2, a0), P(r2, z2, a1), P(r1, z1, a1)
            tris += [(A, B, C), (A, C, D)]

    zz = np.linspace(0, ztop, 4001); dz = zz[1] - zz[0]
    ri = np.where(zz < zj, RI, RI + (zz - zj) * TA)
    ro = np.where(zz < zjo, RO, np.minimum(RI + (zz - zj) * TA + TC, RTOP + TC))
    area = np.pi * (ro ** 2 - ri ** 2)
    vol = (area * dz).sum(); zcm = (area * zz * dz).sum() / vol
    mass = RHO_GLASS * vol

    c, s = math.cos(math.radians(tilt_deg)), math.sin(math.radians(tilt_deg))
    Rx = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    with open(os.path.join(case, "funnel.stl"), "wb") as f:
        f.write(b"funnel".ljust(80, b" ")); f.write(struct.pack("<I", len(tris)))
        for tri in tris:
            f.write(struct.pack("<3f", 0, 0, 0))
            for v in tri:
                f.write(struct.pack("<3f", *(Rx @ (v - [0, 0, zcm]) + [0, 0, zcm + Z0])))
            f.write(struct.pack("<H", 0))

    xml = CASE_XML.format(dp=dp, lo=-TX - 0.01, hi=TX + 0.01, top=TZ + 0.01, x0=-TX, w=2 * TX, hw=HW, tz=TZ,
                          mass=mass, tmax=tmax, tout=tout)
    open(os.path.join(case, "Funnel_Def.xml"), "w").write(xml)
    open(os.path.join(case, "run.sh"), "w").write(RUN_SH)
    os.chmod(os.path.join(case, "run.sh"), 0o755)
    materials = os.path.join(DSPH, "examples", "chrono", "07_DamBreakCubes", "Floating_Materials.xml")
    if os.path.exists(materials):
        shutil.copy(materials, case)
    print(f"масса {mass*1e3:.1f} г, центр масс {zcm*1e3:.1f} мм над концом носика, "
          f"частиц воды около {(2*TX)**2*HW/dp**3/1e6:.2f} млн")


def tool(name, *args):
    subprocess.run([os.path.join(BIN, name), *args], env=ENV, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def post(case):
    out = os.path.join(case, "out")
    os.makedirs(os.path.join(out, "fi"), exist_ok=True); os.makedirs(os.path.join(out, "gauges"), exist_ok=True)
    data = os.path.join(out, "data")
    tool("FloatingInfo_linux64", "-dirdata", data, "-onlymk:61", "-savemotion", "-savedata", os.path.join(out, "fi", "FloatingInfo"))
    for name, x, y in (("a", 0.065, 0), ("b", 0.085, 0), ("c", 0, 0.085), ("d", -0.085, 0)):
        tool("MeasureTool_linux64", "-dirdata", data, f"-pointsdef:ptels[x={x}:1:{x},y={y}:1:{y},z=0.08:0.001:0.22]",
             "-onlytype:-all,+fluid", "-elevation", "-savecsv", os.path.join(out, "gauges", f"g_{name}"))


def series():
    for tilt in (0, 5, 10, 20):
        case = f"angle_{tilt}"
        make_case(case, 0.0025, 2.5, 0.02, tilt)
        subprocess.run([os.path.join(case, "run.sh")], check=True)
        post(case)


def read_part(path, cols):
    with open(path) as f:
        f.readline(); t = float(f.readline().split(";")[0])
    return t, np.loadtxt(path, delimiter=";", skiprows=4, usecols=cols, ndmin=2)


def encode(frames, mp4, fps):
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-framerate", str(fps),
                    "-i", os.path.join(frames, "f%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", mp4],
                   check=True)
    print(mp4)


def plt_setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    return plt


V = {}


def video_frame(k):
    plt = plt_setup()
    sl, T, Z, TILT, tank, dp = V["slice"], V["T"], V["Z"], V["TILT"], V["tank"], V["dp"]
    t, fl = read_part(os.path.join(sl, f"Fluid_{k:04d}.csv"), (0, 2, 3, 4, 5))
    _, P = read_part(os.path.join(sl, f"Float_{k:04d}.csv"), (0, 1, 2))
    spd = np.sqrt(fl[:, 2] ** 2 + fl[:, 3] ** 2 + fl[:, 4] ** 2)
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
    ax = fig.add_axes([0.03, 0.07, 0.46, 0.85])
    ax.scatter(tank[:, 0] * 1e3, tank[:, 1] * 1e3, s=1.2, c="#666666", lw=0)
    sc = ax.scatter(fl[:, 0] * 1e3, fl[:, 1] * 1e3, s=3.0, c=spd, cmap="YlGnBu", vmin=0, vmax=0.4, lw=0)
    ax.scatter(P[:, 0] * 1e3, P[:, 2] * 1e3, s=0.4, c="#f4a261", alpha=0.25, lw=0)
    m = np.abs(P[:, 1]) < 1.5 * dp
    ax.scatter(P[m, 0] * 1e3, P[m, 2] * 1e3, s=3.0, c="#d9480f", lw=0)
    ax.set_xlim(-95, 95); ax.set_ylim(-5, 325); ax.set_aspect("equal"); ax.set_xlabel("мм")
    ax.set_title(f"срез через ось воронки     t = {t:5.2f} c", loc="left")
    fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.01).set_label("скорость воды, м/с")
    a1 = fig.add_axes([0.60, 0.56, 0.37, 0.34]); a2 = fig.add_axes([0.60, 0.10, 0.37, 0.34])
    a1.plot(T, Z * 1e3, color="#d9480f", alpha=0.3); a1.plot(T[T <= t], Z[T <= t] * 1e3, color="#d9480f", lw=2)
    a1.set_ylabel("центр масс, мм"); a1.grid(alpha=0.3); a1.set_xlim(0, T.max())
    a1.set_title("движение воронки (DualSPHysics + Chrono, 3D)", loc="left", fontsize=11)
    a2.plot(T, TILT, color="#2b6cb0", alpha=0.3); a2.plot(T[T <= t], TILT[T <= t], color="#2b6cb0", lw=2)
    a2.set_ylabel("наклон оси, °"); a2.set_xlabel("t, с"); a2.grid(alpha=0.3); a2.set_xlim(0, T.max())
    fig.text(0.03, 0.965, "Воронка: горло ⌀10 см, носик ⌀8 мм × 50 мм, стенка 4 мм, стекло (188 г); бак 18×18 см, "
             "вода 15 см; частицы 2 мм; старт: 1 см над водой, наклон 2°", fontsize=9.5)
    fig.savefig(os.path.join(V["frames"], f"f{k:04d}.png")); plt.close(fig)


def video(case, dp=0.002):
    out = os.path.join(case, "out"); sl = os.path.join(out, "slice"); frames = os.path.join(out, "frames")
    os.makedirs(sl, exist_ok=True); os.makedirs(frames, exist_ok=True)
    data = os.path.join(out, "data"); band = f"-onlypos:-1:{-0.75*dp}:-1:1:{0.75*dp}:1"
    tool("PartVTK_linux64", "-dirdata", data, "-savecsv", os.path.join(sl, "Fluid"), "-onlytype:-all,+fluid", band, "-vars:-all,+vel")
    tool("PartVTK_linux64", "-dirdata", data, "-savecsv", os.path.join(sl, "Float"), "-onlytype:-all,+floating", "-vars:-all")
    tool("PartVTK_linux64", "-dirdata", data, "-first:0", "-last:0", "-savecsv", os.path.join(sl, "Tank"),
         "-onlytype:-all,+fixed", band, "-vars:-all")
    parts = sorted(int(os.path.basename(p)[6:10]) for p in glob.glob(os.path.join(sl, "Fluid_[0-9]*.csv")))
    T, Z, TILT = [], [], []
    for k in parts:
        t, P = read_part(os.path.join(sl, f"Float_{k:04d}.csv"), (0, 1, 2))
        c = P.mean(0); w, v = np.linalg.eigh(np.cov((P - c).T))
        axis = v[:, 0] if abs(w[0] - w[1]) > abs(w[1] - w[2]) else v[:, 2]
        T.append(t); Z.append(c[2]); TILT.append(np.degrees(np.arccos(abs(axis[2]))))
    V.update(slice=sl, frames=frames, dp=dp, T=np.array(T), Z=np.array(Z), TILT=np.array(TILT),
             tank=read_part(os.path.join(sl, "Tank_0000.csv"), (0, 2))[1])
    with get_context("fork").Pool() as p:
        p.map(video_frame, parts)
    encode(frames, os.path.join(out, "funnel_3d.mp4"), 25)


def check_frame(i):
    plt = plt_setup()
    csv, ft, fz, ref, bound = V["csv"], V["ft"], V["fz"], V["ref"], V["bound"]
    t, fl = read_part(os.path.join(csv, f"Fluid_{i:04d}.csv"), (0, 2, 3, 5))
    _, fb = read_part(os.path.join(csv, f"Float_{i:04d}.csv"), (0, 2))
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
    ax = fig.add_axes([0.03, 0.06, 0.45, 0.86])
    ax.scatter(bound[:, 0], bound[:, 1], s=0.3, c="#555555", lw=0)
    sc = ax.scatter(fl[:, 0], fl[:, 1], s=0.25, c=np.hypot(fl[:, 2], fl[:, 3]), cmap="YlGnBu", vmin=0, vmax=1.5, lw=0)
    ax.scatter(fb[:, 0], fb[:, 1], s=0.6, c="#d9480f", lw=0)
    ax.set_xlim(-5.2, 5.2); ax.set_ylim(-0.2, 15.6); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(f"t = {t:5.2f} s" + ("   (тело удерживается)" if t < 1.0 else ""), loc="left")
    fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.01).set_label("скорость воды, м/с")
    a2 = fig.add_axes([0.58, 0.14, 0.39, 0.72])
    m = ft >= 1.0
    a2.plot(ref[:, 0], ref[:, 1], "o", ms=2.5, color="#2b6cb0", label="Fekken 2004 (эталон)")
    a2.plot((ft[m] - 1.0) * math.sqrt(9.81), fz[m], "-", color="#d9480f", lw=1.2, alpha=0.35)
    mk = m & (ft <= t)
    a2.plot((ft[mk] - 1.0) * math.sqrt(9.81), fz[mk], "-", color="#d9480f", lw=2, label="DualSPHysics")
    a2.set_xlim(0, 15.7); a2.set_ylim(-8.5, 0.5); a2.grid(alpha=0.3)
    a2.set_xlabel("время, t·√(g/R)"); a2.set_ylabel("смещение центра, R")
    a2.legend(loc="lower left", fontsize=10); a2.set_title("Падение цилиндра (ρ = 1,2 ρ воды), 2D")
    fig.savefig(os.path.join(V["frames"], f"f{i:04d}.png")); plt.close(fig)


def check(example):
    out = os.path.join(example, "CaseFloatingSphereVal2D_out")
    frames = os.path.join(out, "frames"); os.makedirs(frames, exist_ok=True)
    fi = np.genfromtxt(os.path.join(out, "floatinginfo", "FloatingInfo_mk61.csv"), delimiter=";", skip_header=1)
    V.update(csv=os.path.join(out, "csv"), frames=frames, ft=fi[:, 1], fz=fi[:, 10] - fi[0, 10],
             ref=np.loadtxt(os.path.join(example, "EXP_FloatingSphereVal2D_Displacement_Fekken2004.txt"), skiprows=2),
             bound=read_part(os.path.join(out, "csv", "Bound_0000.csv"), (0, 2))[1])
    n = len(glob.glob(os.path.join(out, "csv", "Fluid_[0-9]*.csv")))
    with get_context("fork").Pool() as p:
        p.map(check_frame, range(n))
    encode(frames, os.path.join(out, "validation_cylinder.mp4"), 25)


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "case":
        make_case(args[0], *map(float, args[1:]))
    elif cmd == "series":
        series()
    elif cmd == "post":
        post(args[0])
    elif cmd == "video":
        video(args[0])
    elif cmd == "check":
        check(args[0])
