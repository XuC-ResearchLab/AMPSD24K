import aiohttp
import asyncio
import pandas as pd
import configparser
from config_utils import get_section_dict, get_config_value
import re
import json
from log_utils import log_api_event
import logging
import time

class ApiPromptAsyncProcessor:
    # 通过统一接口读取配置文件
    def __init__(self, config: configparser.ConfigParser):
        self.call_count = 0 # 新增：初始化请求计数器
        
        api_cfg = get_section_dict(config, 'API')
        
        self.authorization_key = api_cfg['authorization_key']
        self.url_async = api_cfg['url_async']
        self.model = api_cfg.get('model')
        self.max_tokens = api_cfg.get('max_tokens', 300)
        self.temperature = api_cfg.get('temperature', 0)
        
        # 读取Prompt_Labels配置
        prompt_cfg = get_section_dict(config, 'Prompt_Labels')
        self.problem_categories = prompt_cfg['problem_categories']
        self.knowledge_tags = prompt_cfg['knowledge_tags']

        # 创建信号量限制并发请求数量
        max_concurrent = get_config_value(config, 'Processing_Mode', 'max_concurrent_requests')
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def api_call(self, prompt, session, fallback=None, ERROR_INFO="[错误]"):
        self.call_count += 1  # 请求计数器加一
        request_id = self.call_count
        
        # 截取最后30个字符作为请求返回失败时的预览
        # 先清理换行符，再统一处理摘要
        cleaned_preview = re.sub(r'[\r\n]+', ' ', prompt_preview).strip()
        prompt_preview = cleaned_preview[-30:] if len(cleaned_preview) > 30 else cleaned_preview

        start_time = time.time()
        
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        headers = {
            "Authorization": f"Bearer {self.authorization_key}",
            "Content-Type": "application/json"
        }
        async with self.semaphore:
            try:
                async with session.post(self.url_async, json=body, headers=headers) as resp:
                    res = await resp.json()
                    elapsed = round(time.time() - start_time, 3)
                    
                    if "choices" in res:
                        # 成功返回时不传prompt_preview，失败时prompt_preview用于追踪
                        log_api_event(request_id, "success", elapsed, False)
                        return res["choices"][0]["message"]["content"].strip()
                    
                    # 结构错误但没有触发异常
                    # 记录 res 的尾部信息作为 preview
                    # res 是 dict，先将它转成 JSON 字符串
                    bad_res_str = json.dumps(res, ensure_ascii=False)
                    prompt_preview = bad_res_str[-30:] if len(bad_res_str) > 30 else bad_res_str
                    log_api_event(request_id, "bad_response", elapsed, True, prompt_preview)
            except Exception as e:
                elapsed = round(time.time() - start_time, 3)
                log_api_event(request_id, "exception", elapsed, True, prompt_preview, error=str(e))
            
            # 无论是结构问题或异常，最终都 fallback
            return fallback

    # 清理api-response字符串中多余的转义符和换行，并转换为实际 Python 对象
    @staticmethod
    def clean_api_field(value: str, field_type: str = "list"):
        """
        通用字段清洗函数：
        - field_type='dict': 解析quantity_relation为 dict（处理非标准 JSON 格式）
        - field_type='list': 解析problem_category、knowledge_tag为 list（标准 JSON 字符串或单字符串）

        示例：
        "quantity\_relation": "数量关系: {"猴妈妈要把35枝铅笔和42本日记本平均分给孩子们": "铅笔总数 = 35，日记本总数 = 42", "铅笔缺1枝": "每个孩子分得的铅笔数量 = 铅笔总数 / 孩子数量 - 1", "日记本多2本": "每个孩子分得的日记本数量 = 日记本总数 / 孩子数量 + 2", "最多有几只小猴?": "孩子数量 = X"}"
        "problem\_category": "{["分配与平均类"]}",
        "knowledge\_tag": "{[\"除法\", \"余数处理\", \"实际应用题\"]}"

        经clean_api_field处理后：
        "quantity_relation": {
                "猴妈妈要把35枝铅笔平均分给孩子们": "总铅笔数 = 35，平均每只小猴分得铅笔 = 总铅笔数 / 小猴数量",
                "铅笔缺1枝": "最后剩余铅笔 = -1",
                "猴妈妈要把42本日记本平均分给孩子们": "总日记本数 = 42，平均每只小猴分得日记本 = 总日记本数 / 小猴数量",
                "日记本多2本": "最后剩余日记本 = 2",
                "最多有几只小猴?": "小猴数量 = X"
            },
        "problem_category": [
            "平均分配类",
            "最大公约数类"
        ],
        "knowledge_tag": [
            "除法",
            "余数处理",
            "平均数"
        ] 
        """
        if not isinstance(value, str):
            return value

        # 清理通用格式
        value = value.replace('\\', '').replace('\n', ' ').replace('\r', ' ').strip()

        # 修复中文全角引号（“”）→ 英文引号（""）
        value = value.replace('“', '"').replace('”', '"')

        # 如果开头有“**输出**：”或类似注释，清除掉
        value = re.sub(r'^\**输出\**[:：]?', '', value, flags=re.IGNORECASE).strip()

        # ===== 1. 对应字典型字段 =====
        if field_type == "dict":
            try:
                # 若不是以 { 开头，尝试包裹成 JSON 格式
                if not value.startswith("{"):
                    value = "{" + value + "}"

                # 修复 JSON 尾部多余逗号或句点
                value = re.sub(r',\s*}', '}', value)
                value = re.sub(r'\.\s*}$', '}', value)

                return json.loads(value)
            
            except Exception as e:
                logging.warning(f"[clean_api_field] 解析 dict 失败: {e}\n原始内容: {value}")
                return value

        # ===== 2. 对应列表型字段 =====
        elif field_type == "list":
            try:
                return json.loads(value)
            except Exception:
                # 若不是 JSON 格式字符串，就包为列表返回
                return [value.strip()]

        # ===== 3. 其他情况：原样返回 =====
        else:
            return value

    async def reasoning_type(self, zh_text, session):
        prompt = f"""
        你是一位精通数学文字题的专家，请根据题目的解答推理复杂程度对数学文字题进行分类。分类标准如下：
        type_1(简单计算)：没有隐含关系，只需简单加减乘除计算即可解题。
        type_2(单步公式)：可以直接使用数学公式，或者只需进行一步简单转换即可解决。
        type_3(多步公式)：需要使用数学公式，并且必须经过多步转换才能解决。
        数学题内容: "{zh_text}"
        分类选项: [type_1, type_2, type_3]
        请尽量只选择最接近的一个分类，并直接输出分类标签。
        """
        return await self.api_call(prompt, session, fallback="type_error", ERROR_INFO="[分类错误]")

    async def translate_text(self, zh_text, session):
        prompt = f"""
        你是一个擅长将中文翻译成英文的专家，而不是解答问题，请将以下中文翻译成英文:\n{zh_text}
        """
        return await self.api_call(prompt, session, fallback=None, ERROR_INFO="[翻译错误]")

    async def extract_relation(self, zh_text, session):
        prompt = f"""
        你作为一个数量关系抽取器，从题目中提取实体之间的数量关系，而不是解答问题。
        请确保提取的关系清晰、准确且格式一致，只需直接输出题目文本对应的数量关系即可。
        
        示例：
        题目：一个果园的李树棵数是桃树的 7/8，桃树棵数是梨树的 5/6。已知李树有1680棵，梨树有多少棵？
        输出："李树棵数是桃树的 7/8":"李树 = 桃树 * 7/8","桃树棵数是梨树的 5/6":"桃树 = 梨树 * 6/5","李树有 1680 棵":"李树 = 1680","梨树有多少棵?":"梨树 = X"
        题目：用棱长为3 cm正方形塑料拼插积木在广场中心搭建起一面长6 m，高2.7 m，厚6 cm的奥运中心墙，算一下这个墙用了多少积木？
        输出："棱长为3 cm正方形塑料拼插积木": "正方体棱长 = 3 cm，积木体积 = 棱长 * 棱长", "长6 m": "墙的长度 = 6 m = 600 cm", "高2.7 m": "墙的高度 = 2.7 m = 270 cm", "厚6 cm": "墙的厚度 = 6 cm", "这个墙用了多少积木": "墙的体积 = 长度 * 高度 * 厚度，积木数量 = 墙的体积 / 每个积木的体积"
        
        题目：{zh_text}
        """
        return await self.api_call(prompt, session, fallback=None, ERROR_INFO="[关系抽取错误]")

    async def problem_category(self, zh_text, session):
        prompt = f"""
        你是一位资深小学数学专家，擅长对题目进行结构化分类。请根据题干列出该题目所属的类型（可多选）。
        请尽量从以下问题分类中选择最接近的一个或多个，并直接输出分类选项：{self.problem_categories}
        
        示例：
        题目：小明和小红从家出发，分别以每小时 4 千米和 3 千米的速度迎面而行，2 小时后相遇。他们家之间相距多少千米？
        输出：["行程类"]

        题目: {zh_text}
        """
        return await self.api_call(prompt, session, fallback=None, ERROR_INFO="[题型分类错误]")

    async def knowledge_tag(self, zh_text, session):
        prompt = f"""
        你是一位小学数学教师，擅长分析题目所涉及的数学知识点。请根据题干列出其中涵盖的数学知识点（可多选）。
        请尽量从以下知识点标签中选择最接近的一个或多个，并直接输出知识点标签：{self.knowledge_tags}
        
        示例：
        题目：妈妈买了 3 条裙子，每条裙子 48 元，一共花了多少钱？
        输出：["乘法", "人民币计算"]
        
        题目：{zh_text}       
        """
        return await self.api_call(prompt, session, fallback=None, ERROR_INFO="[知识点打标错误]")

    async def process_dataframe_async(self, df: pd.DataFrame) -> pd.DataFrame:
        logging.info("[ApiPromptAsync.process_dataframe_async] 启动异步批量处理流程")

        df = df.copy()
        async with aiohttp.ClientSession() as session:
            reasoning_tasks = [self.reasoning_type(q, session) for q in df["zh_text"]]
            translate_tasks = [self.translate_text(q, session) for q in df["zh_text"]]
            extract_tasks = [self.extract_relation(q, session) for q in df["zh_text"]]
            category_tasks = [self.problem_category(q, session) for q in df["zh_text"]]
            tag_tasks = [self.knowledge_tag(q, session) for q in df["zh_text"]]

            # 异步执行所有任务
            reasoning_res, en_res, relation_res, category_res, tag_res = await asyncio.gather(
                asyncio.gather(*reasoning_tasks),
                asyncio.gather(*translate_tasks),
                asyncio.gather(*extract_tasks),
                asyncio.gather(*category_tasks),
                asyncio.gather(*tag_tasks),
            )
            
            # 应用清洗函数
            df["reasoning_type"] = reasoning_res
            df["en_text"] = en_res
            df["quantity_relation"] = [self.clean_api_field(r, "dict") for r in relation_res]
            df["problem_category"] = [self.clean_api_field(c, "list") for c in category_res]
            df["knowledge_tag"] = [self.clean_api_field(t, "list") for t in tag_res]
        
        logging.info("[ApiPromptAsync.process_dataframe_async] 所有字段api_call处理完成")

        return df

# def api_prompt_async(df: pd.DataFrame, config: configparser.ConfigParser) -> pd.DataFrame:
#     processor = ApiPromptAsyncProcessor(config)
#     return asyncio.run(processor.process_dataframe_async(df))

import nest_asyncio
nest_asyncio.apply()  # 必须在 get_event_loop 之前执行
    
def api_prompt_async(df: pd.DataFrame, config: configparser.ConfigParser) -> pd.DataFrame:
    processor = ApiPromptAsyncProcessor(config)
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(processor.process_dataframe_async(df))	