import configparser
from ast import literal_eval
from typing import Any

def load_config(config_path: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.optionxform = str  # 对键key的大小写进行区分
    config.read(config_path, encoding='utf-8')
    return config

def get_section_dict(config: configparser.ConfigParser, section: str) -> dict[str, Any]:
    """
    读取整个section，并自动解析值
    
    返回 dict，适合一次性提取字段组
    """
    if section not in config:
        raise KeyError(f"Config section [{section}] not found.")
    return {k: _auto_parse(v) for k, v in config[section].items()} # 输入的字符串内容转换为 Python 对象，如string类型的list，返回的直接是 list of tuples

def get_config_value(config: configparser.ConfigParser, section: str, key: str, fallback: Any = None) -> Any:
    """
    读取单个 key 值，支持 fallback 默认值
    
    适用于只需要 1 个字段，且希望设置默认值的场景
    """
    try:
        value = config[section][key]
        return _auto_parse(value)
    except KeyError:
        return fallback

def _auto_parse(value: str) -> Any:
    """转换Python 对象：支持 str → int / float / list / dict"""
    try:
        return literal_eval(value)
    except Exception:
        return value.strip()