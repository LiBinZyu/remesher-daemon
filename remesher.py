import os
import subprocess
import yaml
import tempfile
import shutil

with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

xremesh_exe = config["paths"]["xremesh_executable"]
blender_exe = config["paths"]["blender_executable"]

def get_fbx_triangle_count_blender(fbx_path):
    """
    用Blender无头统计FBX文件中的三角面数量。
    """
    import sys
    import tempfile

    script = f"""
import bpy
import sys
bpy.ops.wm.read_factory_settings(use_empty=True)
try:
    bpy.ops.import_scene.fbx(filepath=r"{fbx_path}")
except Exception as e:
    print("FBX import failed:", e)
    sys.exit(2)
triangle_count = 0
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        for poly in obj.data.polygons:
            if poly.loop_total == 3:
                triangle_count += 1
# fallback: 如果没有三角面，使用所有面数
if triangle_count == 0:
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            triangle_count += len(obj.data.polygons)
print(triangle_count)
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(script)
        script_path = f.name
    try:
        result = subprocess.run(
            [blender_exe, "--background", "--python", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8"
        )
        # 取最后一行数字
        lines = result.stdout.strip().splitlines()
        for line in reversed(lines):
            if line.strip().isdigit():
                return int(line.strip())
        # fallback
        return 5000
    finally:
        os.remove(script_path)

def run_xremesh(input_fbx, output_fbx):
    """
    调用 xremesh.exe 对FBX文件进行重拓扑。
    """
    # 用Blender统计三角面数
    triangle_count = get_fbx_triangle_count_blender(input_fbx)
    if triangle_count > 100000:
        target_quad_count = max(1, int(triangle_count * 0.05))
    elif triangle_count > 20000:
        target_quad_count = max(1, int(triangle_count * 0.1))
    else:
        target_quad_count = max(1, int(triangle_count * 0.25))

    # 创建临时设置文件和进度文件
    temp_dir = tempfile.mkdtemp(prefix="xremesh_")
    settings_path = os.path.join(temp_dir, "RetopoSettings.txt")
    progress_path = os.path.join(temp_dir, "progress.txt")

    # 写入设置文件（按要求参数）
    with open(settings_path, "w", encoding="utf-8") as f:
        f.write("HostApp=Daemon\n")
        f.write(f'FileIn="{os.path.abspath(input_fbx)}"\n')
        f.write(f'FileOut="{os.path.abspath(output_fbx)}"\n')
        f.write(f'ProgressFile="{progress_path}"\n')
        f.write(f"TargetQuadCount={target_quad_count}\n")
        f.write("CurvatureAdaptivness=20\n")
        f.write("ExactQuadCount=1\n")
        f.write("UseVertexColorMap=0\n")
        f.write("UseMaterialIds=0\n")
        f.write("UseIndexedNormals=0\n")
        f.write("AutoDetectHardEdges=0\n")

    # 调用 xremesh.exe
    try:
        result = subprocess.run(
            [xremesh_exe, "-s", settings_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8"
        )
        if result.returncode != 0:
            raise RuntimeError(f"xremesh failed: {result.stderr}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
