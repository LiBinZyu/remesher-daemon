import os
import subprocess
import yaml

with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

blender_exe = config["paths"]["blender_executable"]

def convert_to_fbx(obj_path, fbx_path):
    """
    使用Blender将OBJ转换为FBX。
    """
    script = f"""
import bpy
import sys

# 清空场景
bpy.ops.wm.read_factory_settings(use_empty=True)

# 导入OBJ
try:
    bpy.ops.wm.obj_import(filepath=r"{obj_path}", use_split_objects=True, use_split_groups=False, import_vertex_groups=True)
except Exception as e:
    print("OBJ import failed:", e)
    sys.exit(2)

# 只选择所有MESH对象
mesh_objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
if not mesh_objs:
    print("No mesh objects found after OBJ import.")
    sys.exit(3)
for obj in bpy.context.scene.objects:
    obj.select_set(obj.type == 'MESH')
bpy.context.view_layer.objects.active = mesh_objs[0]

# 导出FBX
try:
    bpy.ops.export_scene.fbx(filepath=r"{fbx_path}", use_selection=True)
except Exception as e:
    print("FBX export failed:", e)
    sys.exit(4)
"""
    _run_blender_script(script, obj_path, fbx_path)

def convert_to_obj(fbx_path, obj_path):
    """
    使用Blender将FBX转换为OBJ。
    """
    script = f"""
import bpy
import sys

# 清空场景
bpy.ops.wm.read_factory_settings(use_empty=True)

# 导入FBX
try:
    bpy.ops.import_scene.fbx(filepath=r"{fbx_path}")
except Exception as e:
    print("FBX import failed:", e)
    sys.exit(2)

# 只选择所有MESH对象
mesh_objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
if not mesh_objs:
    print("No mesh objects found after FBX import.")
    sys.exit(3)
for obj in bpy.context.scene.objects:
    obj.select_set(obj.type == 'MESH')
bpy.context.view_layer.objects.active = mesh_objs[0]

# 导出OBJ
try:
    bpy.ops.wm.obj_export(filepath=r"{obj_path}", export_selected_objects=True, apply_modifiers=True, export_normals=True)
except Exception as e:
    print("OBJ export failed:", e)
    sys.exit(4)
"""
    _run_blender_script(script, fbx_path, obj_path)

def _run_blender_script(script, src_path, dst_path):
    """
    在Blender中运行给定的Python脚本（无头模式），并将stdout/stderr记录到日志文件。
    """
    import tempfile
    import os
    workdir = os.path.dirname(os.path.abspath(dst_path))
    log_path = os.path.join(workdir, "blender_convert.log")
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(script)
        script_path = f.name
    try:
        with open(log_path, "a", encoding="utf-8") as logf:
            logf.write(f"\n--- Blender conversion: {src_path} -> {dst_path} ---\n")
            result = subprocess.run(
                [blender_exe, "--background", "--python", script_path],
                stdout=logf,
                stderr=logf,
                encoding="utf-8"
            )
            if result.returncode != 0:
                raise RuntimeError(f"Blender conversion failed, see {log_path}")
    finally:
        os.remove(script_path)
