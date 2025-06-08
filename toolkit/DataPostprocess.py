import pandas as pd
import sympy as sp
import re
import logging
import json
from typing import List, Tuple
import jieba
from collections import defaultdict

class DataPostprocessor:
    def __init__(self):
        # 正则表达式：处理百分号
        self.percent_pattern = r'(\d+(\.\d+)?)%'
    
    def format_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        logging.info("[DataPostprocessor.format_dataframe] 开始格式化数学表达式")
        df = df.copy()
        formatted_records = []

        for item in df.to_dict(orient='records'):
            raw_eq = item.get('equation', '')
            ans = item.get('ans', '').strip()

            # 1. 方程补全：加 x=
            if not raw_eq.startswith("x="):
                # 如果方程不是以"x="开头，则进行补全
                logging.info(f"补全方程")
                item["equation"] = f"x={raw_eq}"
                
                # 处理方程时，确保它以"x="开头 用于后续统一取等式右边的表达式
                raw_eq = f"x={raw_eq}" 
                
            # 2. 百分号、括号、幂号标准化
            formatted_eq = re.sub(self.percent_pattern, r'(\1/100)', raw_eq) # 将百分号转换为小数
            formatted_eq = formatted_eq.replace('[', '(').replace(']', ')').replace('^', '**') # 替换括号和幂号

            # 3. 表达式求值
            try:
                # expr_str = formatted_eq.split('=', 1)[1] # 取等号右侧的表达式
                # expr_val = str(sp.N(sp.sympify(expr_str)))  # sympy 计算右侧的表达式的值
                expr_str = formatted_eq.split('=', 1)[1].strip()
                expr = sp.sympify(expr_str)
                val = float(sp.N(expr))
                expr_val = format(val, ".6g")  # 控制精度为简洁数值
            except Exception as e:
                logging.warning(f"表达式解析失败: {formatted_eq} → {e}")
                continue

            # 4. 判断是否 ans 是表达式本身
            # 例如：
                # "equation": "x=720",
                # "ans": "720"
                
                # "equation": "x=210-(195+12)/3",
                # "ans": "210-(195+12)/3"

            # 如果 ans 为空 或者 ans 不等于计算结果 覆盖原 ans
            if not ans:
                logging.info(f"填入计算结果: {expr_str} → {expr_val}")
                item["ans"] = expr_val
            elif ans != expr_val:
                logging.info(f"ans ≠ 实际值，覆盖 ans: {ans} → {expr_val}")
                item["ans"] = expr_val
            # 如果 ans 和计算结果一致 则不做修改
            else:
                logging.info(f"表达式和 ans 一致: {expr_str} == {ans}")
            
            formatted_records.append(item)

        logging.info(f"[DataPostprocessor.format_dataframe] 处理完成：{len(formatted_records)} 条记录")
        return pd.DataFrame(formatted_records)


    def tokenize_std_export(self, df: pd.DataFrame, source_list: List[Tuple[str, str]], data_output: str) -> None:
        logging.info("[DataPostprocessor.tokenize_std_export] 开始分词与编号处理")

        if df.empty:
            logging.warning("[DataPostprocessor.tokenize_std_export] 输入数据为空，跳过处理")
            return

        if "zh_text" not in df.columns:
            logging.error("[DataPostprocessor.tokenize_std_export] DataFrame 中缺少 'zh_text' 字段，无法进行分词。")

        df = df.copy()

        # 1、分词：
        df["segmented_text"] = df["zh_text"].apply(lambda x: " ".join(jieba.cut(x, cut_all=False)))
        
        # 2、编号：range(1, len(df) + 1) 从 1 开始编号 并替换原 id 列
        df["id"] = range(1, len(df) + 1)

        sources = [source for _, source in source_list]

        result_json = {
            "head": {
                "name": "benchmark_data",
                "version": "1.0",
                "size": len(df),
                "source": ", ".join(sources),
                "description": "This is a benchmark dataset for math question.",
                "original_language": "Chinese"
            },
            "body": df.to_dict(orient='records')
        }
        
        try:
            with open(data_output, 'w', encoding='utf-8') as f:
                json.dump(result_json, f, ensure_ascii=False, indent=4)
            logging.info(f"[DataPostprocessor.tokenize_std_export] 成功写入文件: {data_output}")
        except Exception as e:
            logging.error(f"[DataPostprocessor.tokenize_std_export] 写入文件失败: {e}")

def data_postprocessing(df: pd.DataFrame, source_list: List[Tuple[str, str]], data_output: str) -> None:
    """
    格式化数学表达式并进行分词与编号处理，并以标准格式写入 JSON 文件

    参数：
        df: 包含 'zh_text' 和 'equation' 字段的 DataFrame
        source_list: [(filename, source)] 元组列表
        data_output: JSON 输出文件路径
    """
    logging.info("[DataPostprocessor] 开始处理数据")

    formatter = DataPostprocessor()
    df_formatter = formatter.format_dataframe(df)

    # 进行分词与编号处理 格式化输出到 JSON 文件
    formatter.tokenize_std_export(df_formatter, source_list, data_output)