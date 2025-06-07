
import json

def analyze_log(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.startswith("{")]

    total = len(lines)
    success = [l for l in lines if l["status"] == "success"]
    fallback = [l for l in lines if l.get("fallback_used")]
    slow = [l for l in lines if l.get("elapsed_time", 0) > 5.0]

    print(f"📊 总请求数: {total}")
    print(f"✅ 成功数: {len(success)} ({len(success)/total:.2%})")
    print(f"⚠️ 使用 fallback 数: {len(fallback)} ({len(fallback)/total:.2%})")
    print(f"🐢 慢请求（>5s）数: {len(slow)} ({len(slow)/total:.2%})")

    avg_time = sum(l["elapsed_time"] for l in success) / len(success) if success else 0
    print(f"⏱ 平均响应时间: {avg_time:.2f} 秒")

# 示例调用：
# analyze_log("logs/async_api_log.jsonl")
