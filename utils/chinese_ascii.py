import os
import json
import re

# 映射文件路径，可根据需要调整
MAPPING_FILE = os.path.join(os.path.dirname(__file__), "chinese_ascii_map.json")

_ascii_re = re.compile(r"^ch_(\w+)$")

# 内存映射表
_ascii_map = {}
_chinese_map = {}

def _load_map():
    global _ascii_map, _chinese_map
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            _ascii_map = data.get("ascii_map", {})
            _chinese_map = data.get("chinese_map", {})
    else:
        _ascii_map = {}
        _chinese_map = {}

def _save_map():
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "ascii_map": _ascii_map,
            "chinese_map": _chinese_map
        }, f, ensure_ascii=False, indent=2)

def to_ascii(name):
    """
    中文名转ascii（如'结节'->'ch_e7bb93e7ab8b'），并记录映射。
    非中文名直接返回。
    """
    _load_map()
    if name in _ascii_map:
        return _ascii_map[name]
    # 检查是否包含中文
    if re.search(r"[\u4e00-\u9fff]", name):
        hexstr = name.encode("utf-8").hex()
        ascii_name = f"ch_{hexstr}"
        _ascii_map[name] = ascii_name
        _chinese_map[ascii_name] = name
        _save_map()
        return ascii_name
    else:
        return name

def from_ascii(ascii_name):
    """
    ascii名还原为中文名（如'ch_e7bb93e7ab8b'->'结节'），否则原样返回。
    """
    _load_map()
    if ascii_name in _chinese_map:
        return _chinese_map[ascii_name]
    m = _ascii_re.match(ascii_name)
    if m:
        try:
            hexstr = m.group(1)
            name = bytes.fromhex(hexstr).decode("utf-8")
            # 反向注册
            _ascii_map[name] = ascii_name
            _chinese_map[ascii_name] = name
            _save_map()
            return name
        except Exception:
            return ascii_name
    return ascii_name

def clear_map():
    """清空映射表（测试用）"""
    global _ascii_map, _chinese_map
    _ascii_map = {}
    _chinese_map = {}
    if os.path.exists(MAPPING_FILE):
        os.remove(MAPPING_FILE)
