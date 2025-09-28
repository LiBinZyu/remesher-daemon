import os
import shutil
import logging
import yaml

from db.database import mark_processing_as_failed

with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

work_dir = config["paths"]["work_dir"]
logger = logging.getLogger("remesher-daemon")

def cleanup_stale_tasks():
    """
    启动时将所有PROCESSING任务重置为FAILED。
    """
    count = mark_processing_as_failed()
    logger.info(f"Cleanup: {count} stale PROCESSING tasks set to FAILED.")

def cleanup_workdir(uuid):
    """
    删除指定任务的工作目录。
    """
    dir_path = os.path.join(work_dir, uuid)
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path, ignore_errors=True)
        logger.info(f"Cleaned up workdir: {dir_path}")

def cleanup_ascii_map():
    """
    清理中文-ASCII映射表（调用utils.chinese_ascii.clear_map）。
    """
    try:
        from utils import chinese_ascii
        chinese_ascii.clear_map()
        logger.info("Cleaned up ascii map via clear_map()")
    except Exception as e:
        logger.error(f"Failed to cleanup ascii map: {e}")
