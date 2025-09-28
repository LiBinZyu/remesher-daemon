import os
import shutil
import glob
import yaml
import logging

from utils.zip import unzip_file, zip_folder
from converter import convert_to_fbx, convert_to_obj
from remesher import run_xremesh
from utils.chinese_ascii import to_ascii

with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

work_dir = config["paths"]["work_dir"]
output_dir = config["paths"]["output_dir"]

logger = logging.getLogger("remesher-daemon")

def process_task(task):
    """
    处理单个任务。成功时正常返回，失败时抛出异常。
    任务结束后无论成功失败都会清理wip目录。
    """
    from cleanup import cleanup_workdir

    uuid = task["uuid"]
    source_zip = task["source_path"]
    task_work_dir = os.path.join(work_dir, uuid)
    os.makedirs(task_work_dir, exist_ok=True)

    try:
        # 1. 解压
        unzip_file(source_zip, task_work_dir)

        # 2. 查找所有 .obj 文件
        obj_files = glob.glob(os.path.join(task_work_dir, "**", "*.obj"), recursive=True)
        if not obj_files:
            raise Exception("No .obj files found in zip.")

        processed = []
        failed = []

        # 新建结构化子目录
        blenderfbx_dir = os.path.join(task_work_dir, "blenderfbx")
        xremeshfbx_dir = os.path.join(task_work_dir, "xremeshfbx")
        blenderobj_dir = os.path.join(task_work_dir, "blenderobj")
        os.makedirs(blenderfbx_dir, exist_ok=True)
        os.makedirs(xremeshfbx_dir, exist_ok=True)
        os.makedirs(blenderobj_dir, exist_ok=True)

        # 记录ascii与原始名映射
        ascii2orig = {}

        for obj_path in obj_files:
            original_base = os.path.splitext(os.path.basename(obj_path))[0]
            ascii_base = to_ascii(original_base)
            ascii2orig[ascii_base] = original_base
            # 路径分配
            fbx_path = os.path.join(blenderfbx_dir, f"{ascii_base}.fbx")
            fbx_remesh_path = os.path.join(xremeshfbx_dir, f"{ascii_base}_remeshed.fbx")
            obj_out_path = os.path.join(blenderobj_dir, f"{original_base}_remeshed.obj")
            try:
                # 3. 转换到FBX
                convert_to_fbx(obj_path, fbx_path)
                # 4. Remesh
                run_xremesh(fbx_path, fbx_remesh_path)
                # 5. 转回OBJ
                convert_to_obj(fbx_remesh_path, obj_out_path)
                processed.append(obj_out_path)
            except Exception as e:
                logger.error(f"Failed to process {obj_path}: {e}", exc_info=True)
                failed.append(obj_path)

        if not processed:
            raise Exception("All .obj files failed to process.")

        # 6. zip前将blenderobj目录下ascii名_remeshed.*文件名还原为中文名_remeshed.*
        for fname in os.listdir(blenderobj_dir):
            fpath = os.path.join(blenderobj_dir, fname)
            # 只处理文件
            if not os.path.isfile(fpath):
                continue
            # 检查是否ascii名_remeshed
            for ascii_base, original_base in ascii2orig.items():
                prefix = f"{ascii_base}_remeshed"
                if fname.startswith(prefix):
                    new_fname = fname.replace(prefix, f"{original_base}_remeshed", 1)
                    new_fpath = os.path.join(blenderobj_dir, new_fname)
                    os.rename(fpath, new_fpath)
                    break

        # 7. 只打包 blenderobj 目录下的所有文件到zip根目录
        zip_name = f"{uuid}_out.zip"
        zip_path = os.path.join(task_work_dir, zip_name)
        zip_folder(blenderobj_dir, zip_path)

        # 8. 移动到输出目录
        os.makedirs(output_dir, exist_ok=True)
        shutil.move(zip_path, os.path.join(output_dir, zip_name))
    finally:
        cleanup_workdir(uuid)
        from cleanup import cleanup_ascii_map
        cleanup_ascii_map()
