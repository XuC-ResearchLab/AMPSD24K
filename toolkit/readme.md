1、各py文件及函数功能说明 
[API]
url = https://api.chatanywhere.tech #  API地址
authorization_key = sk-fGwWk84dlV3GCQLOOu921oKwjxE65M2qRB4rPF3ruNQcQgVa # API密钥
model = gpt-4o # 使用的模型
max_tokens = 128 # 生成的内容长度
temperature = 0 # 保证生成的内容是确定的

2、main函数中需要替换的部分，演示
"""
字段：

- **id：**题目编号
- **zh_text** (string): 数学题题干的中文描述。
- **en_text** (string): 数学题题干的英文描述。
- **equation** (string): 解题方程。
- **ans** (string): 最终答案。
- **segmented_text** (string): 题干分词。
- **QuantityRelation**数量关系
- **reasoning_type** (string): 解题推理类型，共有四种类型：
	- **type_1**: 不依赖数学公式直接解。
	- **type_2**: 直接使用数学公式或仅需单步转换即可套用数学公式进行求解。
	- **type_3**: 需要用数学公式且需要进行多步转换。
	- **type_4**: 题干为纯数字的题目。
- **source** (string): 数据最初来源（APE、ASP、BNU、EEP、Math23K）。
- **problem_category**（list）:题目类型。
- **knowledge_tags**（list）：知识点标签

数据处理操作入口：
    统一字段，包括字段名、添加缺省字段，该操作在从各数据源加载数据过程完成
    合并 + 去重（根据zh_text字段进行），concat(dataframe_list, ignore_index=True).drop_duplicates("zh_text")两个函数前后执行
    题目筛选：去掉纯数字题，选取题干字符在30-60之间,方式：正则表达式，
    题目类型打标分类 + 翻译 + 数量关系提取，采用gpt-api prompt方式
    分词，工具jieba
    给题目编号
    以标准json文件返回
    
操作在各函数中的分布：
1、
    统一字段，包括字段名、添加缺省字段，该操作在从各数据源加载数据过程完成
    合并 + 去重（根据zh_text字段进行），concat(dataframe_list, ignore_index=True).drop_duplicates("zh_text")两个函数前后执行
    题目筛选：去掉纯数字题，选取题干字符在30-60之间,方式：正则表达式
2、
    读取api配置
    题目类型打标分类 + 翻译 + 数量关系提取，采用gpt-api prompt方式（这一步最为耗时和钱）
3、
    分词，分词工具jieba
    编号
4、
    以标注格式输出json文件
"""