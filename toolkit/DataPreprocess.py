import os
import json
import pandas as pd
import re
import configparser
from config_utils import get_section_dict
import logging

class DataPreprocessor:
    # 通过统一接口读取配置文件中预定义的标准字段和字段别名
    def __init__(self, config: configparser.ConfigParser):
        field_cfg = get_section_dict(config, 'Predefined_Standard_Fields')
        self.target_fields = field_cfg['target_fields']
        self.field_aliases = field_cfg['field_aliases']

    # 统一字段名并按顺序补齐数据源json文件中不存在的字段
    def standardize_and_align_fields(self, df: pd.DataFrame, source_value: str = None) -> pd.DataFrame:
        rename_map = {col: self.field_aliases[col] for col in df.columns if col in self.field_aliases}
        df = df.rename(columns=rename_map)

        # 读取数据文件时便赋值 source 字段
        df['source'] = source_value
        
        # 补齐其他缺失字段
        for field in self.target_fields:
            if field not in df.columns:
                df[field] = pd.NA

        # 返回df之前进行reindex 重置dataframe的索引
        return df.reindex(columns=self.target_fields)

    # 题目筛选
    def filter_math_questions(self, df: pd.DataFrame) -> pd.DataFrame:
        # 匹配仅包含数字、空格、运算符、括号（纯数学表达式）
        pure_math_pattern = re.compile(r'^[\d\s\-+*/().]+[\d\s\-+*/().]*[^\u4e00-\u9fa5]*$')
        
        # 过滤：保留字符长度在 30~80 且 不是纯数字题的题目
        df = df[
            df['zh_text'].apply(lambda x: isinstance(x, str) and 30 <= len(x) <= 80 and not pure_math_pattern.fullmatch(x))
        ]
        
        # 重置dataframe的索引
        return df.reset_index(drop=True)

    # 读取每个文件及其指定的 source 值（支持结构 A（带 head 和 body）和结构 B（不带 head，直接是 list））
    def load_files_with_sources(self, file_source_list: list, folder_path: str) -> pd.DataFrame:
        logging.info("[dataPreprocess.load_files_with_sources] 开始加载数据文件...")
        all_dfs = []

        for filename, source_value in file_source_list:
            full_path = os.path.join(folder_path, filename)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, dict) and 'body' in data:
                    df = pd.DataFrame(data['body'])   # 格式 A
                elif isinstance(data, list):
                    df = pd.DataFrame(data)          # 格式 B
                else:
                    logging.error(f"[dataPreprocess.load_files_with_sources] 未识别的数据结构：{filename} → {e}")
                    continue

                df = self.standardize_and_align_fields(df, source_value)
                
                logging.info(f"[dataPreprocess.load_files_with_sources] 成功读取文件: {filename}，记录数: {len(df)}")
                
                all_dfs.append(df)

            except Exception as e:
                logging.error(f"[dataPreprocess.load_files_with_sources] 文件读取失败：{filename} → {e}")

        if all_dfs:
            combined_df = pd.concat(all_dfs, ignore_index=True).drop_duplicates("zh_text")
        else:
            combined_df = pd.DataFrame(columns=self.target_fields).drop_duplicates("zh_text")

        logging.info(f"[dataPreprocess.load_files_with_sources] 数据合并完成，总样本数: {len(combined_df)}")
        
        return self.filter_math_questions(combined_df)

def data_preprocessing(config: configparser.ConfigParser, file_source_list: list, folder_path: str) -> pd.DataFrame:
    preprocessor = DataPreprocessor(config)
    return preprocessor.load_files_with_sources(file_source_list, folder_path)