# Осесимметричные расчёты в OpenFOAM v2412 (interFoam: вода и воздух, натяжение 0,072 Н/м, краевой угол 30 градусов).
# Расчёт идёт в клине 5 градусов вокруг оси воронки. Удобно запускать в docker-образе opencfd/openfoam-default:2412:
#   docker run --rm -v $PWD:/work opencfd/openfoam-default:2412 bash -lc "cd /work/папка && ./Allrun"
#
# Две воронки:
#   малая закреплённая (заполнение): горло 60 мм, конус 60 градусов, носик 40 мм с внутренним радиусом 2,5 мм,
#     стенка 1,5 мм; бак радиусом 50 мм, вода на 15 мм выше дна конуса; сетка 0,5 мм;
#   стеклянная воронка из dualsphysics.py (колебания): движется только по вертикали, сетка деформируется вместе с ней,
#     бак той же площади, что 180 x 180 мм, глубина под носиком 130 мм.
#
# Команды:
#   python openfoam.py fill папка [время_с] [шаг_записи_с] [радиус_скругления_кромки_м]
#   python openfoam.py heave папка [время_с] [шаг_записи_с] [подъём_над_равновесием_м] [ячейка_м] [процессоры] [носик_открыт_0_1]
#   python openfoam.py fill-level папка таблица.csv      уровень внутри закреплённой воронки по времени
#   python openfoam.py levels папка таблица.csv          вода внутри движущейся воронки по времени
#   python openfoam.py fill-video папка                   видео заполнения: вода и завихренность
#   python openfoam.py heave-video папка видео.mp4 [заголовок]
# Allrun в папке расчёта строит сетку, считает и пишет центры и объёмы ячеек для обработки.

import math, os, re, subprocess, sys
from multiprocessing import get_context
import numpy as np

TA = math.tan(math.radians(30))
COMMON = "    front { type wedge; }\n    back { type wedge; }\n    axis { type empty; }\n"

SCHEMES = """
ddtSchemes { default Euler; }
gradSchemes { default Gauss linear; }
divSchemes
{
    div(rhoPhi,U) Gauss linearUpwind grad(U);
    div(phi,alpha) Gauss vanLeer;
    div(phirb,alpha) Gauss linear;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
"""

SOLUTION = """
solvers
{{
    "alpha.water.*" {{ nAlphaCorr 2; nAlphaSubCycles 1; cAlpha 1; MULESCorr yes; nLimiterIter 5;
                      solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0; }}
    "pcorr.*" {{ solver GAMG; smoother DIC; tolerance 1e-5; relTol 0; }}
    p_rgh {{ solver GAMG; smoother DIC; tolerance 1e-7; relTol 0.05; }}
    p_rghFinal {{ $p_rgh; relTol 0; }}
    "U.*" {{ solver smoothSolver; smoother symGaussSeidel; tolerance 1e-6; relTol 0; }}
}}
PIMPLE {{ {pimple} }}
relaxationFactors {{ equations {{ ".*" 1; }} }}
"""

TRANSPORT = """
phases (water air);
water { transportModel Newtonian; nu 1e-06; rho 1000; }
air   { transportModel Newtonian; nu 1.48e-05; rho 1; }
sigma 0.072;
"""

MESH = """#!/bin/bash
cd "$(dirname "$0")"
rm -rf 0 processor* && cp -r 0.orig 0
blockMesh > log.blockMesh 2>&1
setExprFields -dict system/setExprFieldsDict.marker > log.marker 2>&1
topoSet > log.topoSet 2>&1
subsetMesh fluid -patch funnel -overwrite > log.subsetMesh 2>&1
rm -f 0/wallMarker 0/cellMap 0/pointMap 0/faceMap 0/patchMap
"""


def write(case, rel, cls, body):
    path = os.path.join(case, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    head = f"FoamFile {{ version 2.0; format ascii; class {cls}; object {os.path.basename(rel)}; }}\n"
    open(path, "w").write(head + body + "\n")


def write_case(case, radius, height, cell, solid, inside, water_level, control, nproc, decomposition, pimple, moving=None):
    nr, ny = round(radius / cell), round(height / cell)
    c, s = math.cos(math.radians(2.5)), math.sin(math.radians(2.5))
    write(case, "system/blockMeshDict", "dictionary", f"""
scale 1;
vertices ( (0 0 0) ({radius*c} 0 {-radius*s}) ({radius*c} {height} {-radius*s}) (0 {height} 0) ({radius*c} 0 {radius*s}) ({radius*c} {height} {radius*s}) );
blocks ( hex (0 1 2 3 0 4 5 3) ({nr} {ny} 1) simpleGrading (1 1 1) );
edges ();
boundary
(
    front {{ type wedge; faces ((0 1 2 3)); }}
    back  {{ type wedge; faces ((0 3 5 4)); }}
    axis  {{ type empty; faces ((0 3 3 0)); }}
    tank  {{ type wall;  faces ((1 4 5 2)); }}
    bottom {{ type wall; faces ((0 4 1 0)); }}
    atmosphere {{ type patch; faces ((3 2 5 3)); }}
    funnel {{ type wall; faces (); }}
);
""")
    write(case, "system/setExprFieldsDict.marker", "dictionary",
          f"expressions ( wallMarker {{ field wallMarker; dimensions [0 0 0 0 0 0 0]; expression #{{ ({solid}) ? 1 : 0 #}}; }} );")
    write(case, "system/setExprFieldsDict", "dictionary",
          f"expressions ( alpha.water {{ field alpha.water; dimensions [0 0 0 0 0 0 0]; "
          f"expression #{{ (pos().y() < {water_level} && !({inside})) ? 1 : 0 #}}; }} );")
    write(case, "system/topoSetDict", "dictionary", """
actions
(
    { name solid; type cellSet; action new; source fieldToCell; field wallMarker; min 0.5; max 1.5; }
    { name fluid; type cellSet; action new; source cellToCell; sets (solid); }
    { name fluid; type cellSet; action invert; }
);
""")
    write(case, "system/controlDict", "dictionary", "\napplication interFoam;\n" + control)
    write(case, "system/decomposeParDict", "dictionary", f"numberOfSubdomains {nproc};\n{decomposition}\n")
    write(case, "system/fvSchemes", "dictionary", SCHEMES)
    write(case, "system/fvSolution", "dictionary", SOLUTION.format(pimple=pimple))
    write(case, "constant/g", "uniformDimensionedVectorField", "dimensions [0 1 -2 0 0 0 0];\nvalue (0 -9.81 0);")
    write(case, "constant/transportProperties", "dictionary", TRANSPORT)
    write(case, "constant/turbulenceProperties", "dictionary", "simulationType laminar;")

    write(case, "0.orig/alpha.water", "volScalarField", f"""dimensions [0 0 0 0 0 0 0]; internalField uniform 0;
boundaryField {{
{COMMON}    tank {{ type zeroGradient; }} bottom {{ type zeroGradient; }}
    atmosphere {{ type inletOutlet; inletValue uniform 0; value uniform 0; }}
    funnel {{ type constantAlphaContactAngle; theta0 30; limit gradient; value uniform 0; }}
}}""")
    write(case, "0.orig/wallMarker", "volScalarField", f"""dimensions [0 0 0 0 0 0 0]; internalField uniform 0;
boundaryField {{
{COMMON}    ".*" {{ type calculated; value uniform 0; }}
}}""")
    wall = "movingWallVelocity; value uniform (0 0 0)" if moving else "noSlip"
    write(case, "0.orig/U", "volVectorField", f"""dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 0);
boundaryField {{
{COMMON}    tank {{ type noSlip; }} bottom {{ type noSlip; }}
    funnel {{ type {wall}; }}
    atmosphere {{ type pressureInletOutletVelocity; value uniform (0 0 0); }}
}}""")
    write(case, "0.orig/p_rgh", "volScalarField", f"""dimensions [1 -1 -2 0 0 0 0]; internalField uniform 0;
boundaryField {{
{COMMON}    tank {{ type fixedFluxPressure; value uniform 0; }} bottom {{ type fixedFluxPressure; value uniform 0; }}
    funnel {{ type fixedFluxPressure; value uniform 0; }}
    atmosphere {{ type totalPressure; p0 uniform 0; }}
}}""")

    run = MESH
    if moving:
        write(case, "constant/dynamicMeshDict", "dictionary", moving)
        write(case, "0.orig/pointDisplacement", "pointVectorField", f"""dimensions [0 1 0 0 0 0 0]; internalField uniform (0 0 0);
boundaryField {{
{COMMON}    tank {{ type fixedValue; value uniform (0 0 0); }}
    bottom {{ type fixedValue; value uniform (0 0 0); }}
    atmosphere {{ type fixedValue; value uniform (0 0 0); }}
    funnel {{ type calculated; value uniform (0 0 0); }}
}}""")
        run += "cp 0.orig/pointDisplacement 0/\n"
    run += f"""setExprFields > log.setExprFields 2>&1
checkMesh > log.checkMesh 2>&1
decomposePar > log.decomposePar 2>&1
mpirun -np {nproc} interFoam -parallel > log.interFoam 2>&1
reconstructPar > log.reconstructPar 2>&1
postProcess -func writeCellCentres > log.cellCentres 2>&1
postProcess -func writeCellVolumes > log.cellVolumes 2>&1
"""
    open(os.path.join(case, "Allrun"), "w").write(run)
    os.chmod(os.path.join(case, "Allrun"), 0o755)


def fill_case(case, end=10.0, write_step=0.04, fillet=0.0):
    y0, ls, ri, ro = 0.040, 0.040, 0.0025, 0.0040
    tw = 0.0015 / math.cos(math.radians(30))
    yj = y0 + ls; ytop = yj + (0.030 - ri) / TA
    x, y = "pos().x()", "pos().y()"
    edge = f"({x}-{ri+fillet})*({x}-{ri+fillet}) + ({y}-{y0+fillet})*({y}-{y0+fillet}) > {fillet*fillet}"
    solid = (f"({y} >= {y0} && {y} <= {yj} && {x} >= {ri} && {x} <= {ro} && !({x} < {ri+fillet} && {y} < {y0+fillet} && {edge})) || "
             f"({y} > {yj} && {y} <= {ytop} && {x} >= {ri}+({y}-{yj})*{TA} && {x} <= {ri}+({y}-{yj})*{TA}+{tw})")
    inside = f"({y} >= {y0} && {y} <= {yj} && {x} < {ri}) || ({y} > {yj} && {x} < {ri}+({y}-{yj})*{TA})"
    control = (f"startFrom latestTime; startTime 0; stopAt endTime; endTime {end};\n"
               f"deltaT 1e-5; writeControl adjustable; writeInterval {write_step}; purgeWrite 0;\n"
               "writeFormat ascii; writePrecision 6; writeCompression off; timeFormat general; timePrecision 6;\n"
               "runTimeModifiable yes; adjustTimeStep yes; maxCo 0.5; maxAlphaCo 0.5; maxDeltaT 3e-4;\n")
    write_case(case, 0.05, 0.14, 0.0005, solid, inside, yj + 0.015, control, 4, "method scotch;",
               "momentumPredictor no; nOuterCorrectors 1; nCorrectors 2; nNonOrthogonalCorrectors 0;")


def heave_case(case, end=3.0, write_step=0.02, lift=0.015, cell=0.001, nproc=8, open_spout=0):
    ri, t, ls, rtop = 0.004, 0.004, 0.050, 0.050
    ro, tw, hc = ri + t, t / math.cos(math.radians(30)), (rtop - ri) / TA
    mass, zcm, draft = 0.188, 0.0927, 0.1152
    radius = 0.18 / math.sqrt(math.pi)
    y0 = 0.13 + lift; yj, ytop = y0 + ls, y0 + ls + hc
    height = round((ytop + 0.10) / cell) * cell
    x, y = "pos().x()", "pos().y()"
    solid = (f"({y} >= {y0} && {y} <= {yj} && {x} <= {ro} && {x} >= {ri if open_spout else 0}) || "
             f"({y} > {yj} && {y} <= {ytop} && {x} >= {ri}+({y}-{yj})*{TA} && {x} <= {ri}+({y}-{yj})*{TA}+{tw})")
    inside = f"{y} > {yj} && {x} < {ri}+({y}-{yj})*{TA}"
    control = (f"startFrom latestTime; startTime 0; stopAt endTime; endTime {end};\n"
               f"deltaT 1e-5; writeControl adjustable; writeInterval {write_step}; purgeWrite 0;\n"
               "writeFormat ascii; writePrecision 8; writeCompression off; timeFormat general; timePrecision 6;\n"
               "runTimeModifiable yes; adjustTimeStep yes; maxCo 0.3; maxAlphaCo 0.3; maxDeltaT 5e-4;\n")
    moving = f"""
dynamicFvMesh dynamicMotionSolverFvMesh;
motionSolverLibs (rigidBodyMeshMotion);
motionSolver rigidBodyMotion;
rigidBodyMotionCoeffs
{{
    report on;
    solver {{ type Newmark; }}
    accelerationRelaxation 0.7;
    bodies
    {{
        funnel
        {{
            type rigidBody;
            parent root;
            mass {mass * 5 / 360:.8e};
            centreOfMass (0 0 0);
            inertia (1e-7 0 0 1e-7 0 1e-7);
            transform (1 0 0 0 1 0 0 0 1) (0 {y0 + zcm:.6f} 0);
            joint {{ type Py; }}
            patches (funnel);
            innerDistance 0.004;
            outerDistance {0.045 if open_spout else 0.04};
        }}
    }}
}}
"""
    write_case(case, radius, height, cell, solid, inside, 0.13 + draft, control, nproc, f"method simple;\ncoeffs {{ n (1 {nproc} 1); }}",
               "momentumPredictor yes; nOuterCorrectors 3; nCorrectors 1; nNonOrthogonalCorrectors 0; correctPhi yes; "
               "moveMeshOuterCorrectors yes;", moving)


def field(path, vector=False):
    text = open(path).read()
    m = re.search(r"internalField\s+nonuniform\s+List<\w+>\s*(\d+)\s*\(", text)
    n = int(m.group(1)); body = text[m.end():]
    if vector:
        rows = re.findall(r"\(([^()]*)\)", body[:body.index("boundaryField")])
        return np.array([list(map(float, r.split())) for r in rows[:n]])
    return np.array(body[:body.index(")")].split(), dtype=float)[:n]


def times(case, need="C"):
    return sorted((d for d in os.listdir(case) if re.fullmatch(r"[0-9.e-]+", d) and float(d) > 0
                   and os.path.exists(os.path.join(case, d, need))), key=float)


def fill_level(case, out):
    y0, yj, ri = 0.04, 0.08, 0.0025
    C = field(os.path.join(case, "0", "C"), True); x, y = C[:, 0], C[:, 1]
    inside = ((y >= y0) & (y <= yj) & (x < ri)) | ((y > yj) & (x < ri + (y - yj) * TA))
    ts = times(case, "alpha.water")
    vol = np.array([(field(os.path.join(case, t, "alpha.water"))[inside] * x[inside]).sum() for t in ts])
    np.savetxt(out, np.c_[np.array(ts, float), vol / vol[-1]], delimiter=",", header="t_s,fill_fraction", comments="")


def funnel_height(case):
    num = r"-?\d+\.?\d*(?:e[-+]?\d+)?"
    tl, yl, t = [], [], None
    for line in open(os.path.join(case, "log.interFoam")):
        if line.startswith("Time ="):
            t = float(line.split()[2])
        elif "Centre of rotation" in line and t is not None:
            tl.append(t); yl.append(float(re.findall(num, line)[1]))
    tl, i = np.unique(np.array(tl), return_index=True)
    return tl, np.array(yl)[i]


def levels(case, out):
    ri, ls, zcm = 0.004, 0.050, 0.0927
    tl, yl = funnel_height(case)
    rows = []
    for ts in times(case, "V"):
        t = float(ts); yc = np.interp(t, tl, yl); yj = yc - zcm + ls
        C = field(os.path.join(case, ts, "C"), True); a = field(os.path.join(case, ts, "alpha.water"))
        V = field(os.path.join(case, ts, "V")) * 360.0 / 5.0
        x, y = C[:, 0], C[:, 1]
        inside = (y > yj) & (x < ri + (y - yj) * TA)
        vol = (a[inside] * V[inside]).sum()
        h = ((vol * 3 * TA / math.pi + ri ** 3) ** (1 / 3) - ri) / TA
        rows.append((t, yc, vol * 1e6, h * 1e3, y[(x > 0.095) & (a > 0.5)].max()))
    np.savetxt(out, np.array(rows), delimiter=",", comments="", fmt="%.5f",
               header="t_s,centre_m,water_inside_cm3,inside_level_mm,outside_level_m")


def plt_setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    return plt


def encode(frames, mp4, fps):
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-framerate", str(fps),
                    "-i", os.path.join(frames, "f%04d.png"), "-pix_fmt", "yuv420p",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", mp4], check=True)
    print(mp4)


V = {}


def heave_frame(k):
    from scipy.spatial import cKDTree
    plt = plt_setup()
    t = V["times"][k]; d = os.path.join(V["case"], t)
    C = field(os.path.join(d, "C"), True); a = field(os.path.join(d, "alpha.water"))
    s = np.linalg.norm(field(os.path.join(d, "U"), True), axis=1)
    gx = np.arange(0.00025, 0.1016, 0.0005); gy = np.arange(0.060, 0.300, 0.0005)
    X, Y = np.meshgrid(gx, gy); dist, idx = cKDTree(C[:, :2]).query(np.c_[X.ravel(), Y.ravel()])
    img = np.where((a[idx] > 0.5)[:, None], plt.cm.Blues(0.35 + 0.6 * np.clip(s[idx] / 0.3, 0, 1))[:, :3], [0.97, 0.97, 0.98])
    img[dist > 0.0014] = (0.36, 0.36, 0.38)
    img = img.reshape(len(gy), len(gx), 3)
    fig, ax = plt.subplots(figsize=(7.2, 7.2), dpi=120)
    ax.imshow(np.concatenate([img[:, ::-1], img], axis=1), origin="lower", extent=(-101.6, 101.6, 60, 300), interpolation="nearest")
    ax.set_xlabel("r, мм"); ax.set_ylabel("высота, мм")
    ax.set_title(f"{V['title']}, t = {float(t):.2f} с".replace(".", ","), fontsize=11)
    fig.tight_layout(); fig.savefig(os.path.join(V["frames"], f"f{k:04d}.png")); plt.close(fig)


def heave_video(case, mp4, title="OpenFOAM"):
    frames = os.path.join(case, "frames"); os.makedirs(frames, exist_ok=True)
    V.update(case=case, frames=frames, title=title, times=times(case))
    with get_context("fork").Pool() as p:
        p.map(heave_frame, range(len(V["times"])))
    encode(frames, mp4, 10)


def fill_frame(k):
    from matplotlib.colors import ListedColormap
    plt = plt_setup()
    case, nr, ny, cell, solid, I, J = V["case"], V["nr"], V["ny"], V["cell"], V["solid"], V["I"], V["J"]
    t = V["times"][k]
    a = field(os.path.join(case, t, "alpha.water")); U = field(os.path.join(case, t, "U"), True)

    def grid(vals):
        g = np.full((ny, nr), np.nan); g[J, I] = vals; return g

    def mirror(g):
        return np.concatenate([g[:, ::-1], g], axis=1)

    A, Ux, Uy = grid(a), grid(U[:, 0]), grid(U[:, 1])
    w = np.gradient(np.nan_to_num(Ux), cell, axis=0) - np.gradient(np.nan_to_num(Uy), cell, axis=1)
    w[solid] = np.nan; w[A < 0.5] = np.nan
    ext = [-nr * cell * 1e3, nr * cell * 1e3, 0, ny * cell * 1e3]
    wall = ListedColormap(["#333333"])
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
    ax = fig.add_axes([0.02, 0.05, 0.40, 0.86])
    Am, Sm = mirror(A), mirror(solid.astype(float))
    ax.imshow(np.where(np.isnan(Am), 0, Am), origin="lower", extent=ext, cmap="Blues", vmin=0, vmax=1.6, interpolation="nearest")
    ax.imshow(np.ma.masked_where(Sm < 0.5, Sm), origin="lower", extent=ext, cmap=wall, interpolation="nearest")
    ax.set_title(f"вода / воздух      t = {float(t):5.2f} c", loc="left"); ax.set_xlabel("мм"); ax.set_ylim(20, 140)
    ax2 = fig.add_axes([0.47, 0.05, 0.50, 0.86])
    Wm = mirror(w); Wm[:, :nr] *= -1
    im = ax2.imshow(Wm, origin="lower", extent=ext, cmap="RdBu_r", vmin=-60, vmax=60, interpolation="nearest")
    ax2.imshow(np.ma.masked_where(Sm < 0.5, Sm), origin="lower", extent=ext, cmap=wall, interpolation="nearest")
    ax2.contour(np.linspace(ext[0], ext[1], 2 * nr), np.linspace(0, ext[3], ny), np.nan_to_num(Am), levels=[0.5],
                colors="#0b3d91", linewidths=1.0)
    ax2.set_xlim(-22, 22); ax2.set_ylim(30, 112)
    ax2.set_title("вихри: завихренность ω (1/с); линия — граница воды", loc="left", fontsize=10)
    fig.colorbar(im, ax=ax2, fraction=0.035, pad=0.01).set_label("ω, 1/с")
    fig.text(0.02, 0.965, "Малая закреплённая воронка, осесимметричный расчёт OpenFOAM (interFoam): вода + воздух, "
             "σ = 0,072 Н/м, угол смачивания 30°, сетка 0,5 мм.", fontsize=10)
    fig.savefig(os.path.join(V["frames"], f"f{k:04d}.png")); plt.close(fig)


def fill_video(case):
    cell, nr, ny = 0.0005, 100, 280
    C = field(os.path.join(case, "0", "C"), True)
    I = np.clip(np.round(C[:, 0] / cell - 0.5).astype(int), 0, nr - 1)
    J = np.clip(np.round(C[:, 1] / cell - 0.5).astype(int), 0, ny - 1)
    solid = np.ones((ny, nr), bool); solid[J, I] = False
    frames = os.path.join(case, "frames"); os.makedirs(frames, exist_ok=True)
    V.update(case=case, frames=frames, cell=cell, nr=nr, ny=ny, I=I, J=J, solid=solid,
             times=[t for t in times(case, "alpha.water") if os.path.exists(os.path.join(case, t, "U"))])
    with get_context("fork").Pool(6) as p:
        p.map(fill_frame, range(len(V["times"])))
    encode(frames, os.path.join(case, "fill.mp4"), 25)


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "fill":
        fill_case(args[0], *map(float, args[1:]))
    elif cmd == "heave":
        heave_case(args[0], *map(float, args[1:5]), *map(int, args[5:]))
    elif cmd == "fill-level":
        fill_level(*args)
    elif cmd == "levels":
        levels(*args)
    elif cmd == "fill-video":
        fill_video(args[0])
    elif cmd == "heave-video":
        heave_video(*args)
