import os
import logging
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logging(log_dir: str, log_name: str, max_mb: int, backup_count: int, console: bool) -> str:
    """
    初始化日志系统，支持控制台输出和文件自动轮转。
    :param log_dir: 日志输出目录
    :param log_name: 主日志文件名（不带扩展名）
    :param max_mb: 单个日志文件最大体积（50 MB）
    :param backup_count: 最多保留的轮转日志数量
    :param console: 是否同时输出到控制台
    :return: 主日志文件完整路径
    """
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{log_name}.jsonl")

    handlers = [
        RotatingFileHandler(log_path, maxBytes=max_mb * 1024 * 1024, backupCount=backup_count, encoding='utf-8')
    ]
    if console:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",  # 保持结构化 JSON 输出格式
        handlers=handlers
    )

    logging.info(json.dumps({
        "event": "log_init",
        "log_path": log_path, # "log_path" 属于环境/运行配置
        "timestamp": datetime.now().isoformat()
    }))
    
    return log_path

def log_api_event(request_id, status, elapsed, fallback, prompt_preview="", error=None):
    """
    记录结构化 API 日志事件。
    :param request_id: 请求编号
    :param status: 'success' / 'bad_response' / 'exception'
    :param elapsed: 耗时（秒）
    :param fallback: 是否使用 fallback
    :param zh_preview: 中文题目摘要
    :param error: 可选错误信息
    """
    log_obj = {
        "event": "api_call",
        "request_id": request_id,
        "status": status,
        "elapsed_time": elapsed,
        "fallback_used": fallback,
        "timestamp": datetime.now().isoformat()
    }
    
    # Only include zh_preview if fallback is used
    if fallback and prompt_preview:
        log_obj["prompt_preview"] = prompt_preview
            
    if error:
        log_obj["error"] = error

    if status == "success":
        logging.info(json.dumps(log_obj))
    elif status == "bad_response":
        logging.warning(json.dumps(log_obj))
    else:
        logging.error(json.dumps(log_obj))