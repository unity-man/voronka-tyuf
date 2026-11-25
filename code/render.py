# Трёхмерный кадр основного расчёта DualSPHysics в Blender 4.2 (рис. 4 в работе).
#
# Шаг 1, обычный python: поверхность воды в PLY и положение воронки в каждом кадре.
#   python render.py папка_расчёта
#   (нужен DSPH_HOME, как в dualsphysics.py; результат в папка_расчёта/out/ply и out/funnel_transforms.json)
# Шаг 2, Blender:
#   blender -b -P render.py -- папка_расчёта номер_кадра картинка.png [сэмплы]
#   (для рис. 4 номер кадра 36, это t = 1,44 с)

import json, os, re, sys

try:
    import bpy
except ImportError:
    bpy = None


def read_vtk(path):
    import numpy as np
    b = open(path, "rb").read()
    m = re.search(rb"POINTS (\d+) float\n", b); n = int(m.group(1)); p0 = m.end()
    pts = np.frombuffer(b, ">f4", 3 * n, p0).reshape(n, 3)
    m2 = re.search(rb"POLYGONS (\d+) (\d+)\n", b[p0 + 12 * n:]); nf, size = int(m2.group(1)), int(m2.group(2))
    arr = np.frombuffer(b, ">i4", size, p0 + 12 * n + m2.end())
    if size == 4 * nf and (arr[0::4] == 3).all():
        return pts, arr.reshape(nf, 4)[:, 1:]
    tris, i = [], 0
    while i < size:
        k = arr[i]; idx = arr[i + 1:i + 1 + k]
        tris += [(idx[0], idx[j], idx[j + 1]) for j in range(1, k - 1)]
        i += k + 1
    return pts, np.array(tris)


def write_ply(path, v, f):
    import numpy as np
    with open(path, "wb") as fh:
        fh.write(f"ply\nformat binary_little_endian 1.0\nelement vertex {len(v)}\nproperty float x\nproperty float y\n"
                 f"property float z\nelement face {len(f)}\nproperty list uchar int vertex_indices\nend_header\n".encode())
        fh.write(np.asarray(v, "<f4").tobytes())
        rec = np.zeros(len(f), dtype=[("n", "u1"), ("i", "<i4", 3)]); rec["n"] = 3; rec["i"] = f
        fh.write(rec.tobytes())


def prepare(case):
    import glob, subprocess
    import numpy as np
    out = os.path.join(case, "out")
    tools = os.path.join(os.environ.get("DSPH_HOME", os.path.expanduser("~/DualSPHysics_v5.4")), "bin", "linux")
    env = dict(os.environ, LD_LIBRARY_PATH=tools)
    for d in ("iso", "ply", "rigid"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    subprocess.run([os.path.join(tools, "IsoSurface_linux64"), "-dirdata", "data", "-onlytype:-all,+fluid", "-saveiso", "iso/Water"],
                   cwd=out, env=env, check=True, stdout=subprocess.DEVNULL)
    subprocess.run([os.path.join(tools, "PartVTK_linux64"), "-dirdata", "data", "-savecsv", "rigid/Float",
                    "-onlytype:-all,+floating", "-vars:-all,+idp"], cwd=out, env=env, check=True, stdout=subprocess.DEVNULL)
    for p in sorted(glob.glob(os.path.join(out, "iso", "Water_*.vtk"))):
        write_ply(os.path.join(out, "ply", f"water_{int(os.path.basename(p)[6:10]):04d}.ply"), *read_vtk(p))

    def particles(k):
        a = np.loadtxt(os.path.join(out, "rigid", f"Float_{k:04d}.csv"), delimiter=";", skiprows=4, usecols=(0, 1, 2, 3))
        return a[np.argsort(a[:, 3])][:, :3]

    P0 = particles(0); c0 = P0.mean(0)
    mats, times, tilt = {}, {}, {}
    for p in sorted(glob.glob(os.path.join(out, "rigid", "Float_[0-9]*.csv"))):
        k = int(os.path.basename(p)[6:10]); Pk = particles(k); ck = Pk.mean(0)
        U, _, Vt = np.linalg.svd((P0 - c0).T @ (Pk - ck))
        R = Vt.T @ np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]) @ U.T
        M = np.eye(4); M[:3, :3] = R; M[:3, 3] = ck - R @ c0
        mats[k] = M.tolist(); tilt[k] = float(np.degrees(np.arccos(np.clip(R[2, 2], -1, 1))))
        with open(p) as fh:
            fh.readline(); times[k] = float(fh.readline().split(";")[0])
    json.dump({"matrices": mats, "times": times, "tilt_vs_start_deg": tilt}, open(os.path.join(out, "funnel_transforms.json"), "w"))


def material(name, color, ior, rough, trans=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = ior
    b.inputs["Transmission Weight"].default_value = trans
    return m


def render(case, k, png, samples=64):
    from mathutils import Matrix, Vector
    import math
    out = os.path.join(case, "out")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
    sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1400, 1100
    sc.render.filepath = png

    bpy.ops.wm.stl_import(filepath=os.path.join(case, "funnel.stl"))
    funnel = bpy.context.selected_objects[0]; funnel.data.materials.append(material("glass", (0.92, 0.96, 1.0), 1.5, 0.03))
    funnel.matrix_world = Matrix(json.load(open(os.path.join(out, "funnel_transforms.json")))["matrices"][str(k)])
    bpy.ops.object.shade_smooth()
    bpy.ops.wm.ply_import(filepath=os.path.join(out, "ply", f"water_{k:04d}.ply"))
    bpy.context.selected_objects[0].data.materials.append(material("water", (0.18, 0.48, 0.78), 1.33, 0.02, 0.75))
    bpy.ops.object.shade_smooth()

    tank = material("tank", (0.95, 0.97, 1.0), 1.5, 0.02)
    for x, y, sx, sy in ((-0.092, 0, 0.004, 0.188), (0, 0.092, 0.18, 0.004)):
        bpy.ops.mesh.primitive_cube_add(location=(x, y, 0.16))
        bpy.context.object.scale = (sx / 2, sy / 2, 0.16); bpy.context.object.data.materials.append(tank)
    bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0, -0.002))
    bpy.context.object.data.materials.append(material("floor", (0.85, 0.85, 0.86), 1.45, 0.6, 0.0))

    sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.55, 0.6, 0.68, 1); bg.inputs[1].default_value = 0.7
    bpy.ops.object.light_add(type="AREA", location=(0.3, -0.5, 0.8))
    bpy.context.object.data.energy = 120; bpy.context.object.data.size = 0.6
    bpy.context.object.rotation_euler = (math.radians(40), 0, math.radians(30))
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 2))
    bpy.context.object.data.energy = 2.0; bpy.context.object.rotation_euler = (math.radians(35), math.radians(-20), 0)
    bpy.ops.object.camera_add(location=(0.46, -0.16, 0.30)); cam = bpy.context.object; sc.camera = cam
    cam.data.lens = 55
    cam.rotation_euler = (Vector((0, 0, 0.14)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    if bpy is None:
        prepare(sys.argv[1])
    else:
        args = sys.argv[sys.argv.index("--") + 1:]
        render(args[0], int(args[1]), args[2], *map(int, args[3:]))
