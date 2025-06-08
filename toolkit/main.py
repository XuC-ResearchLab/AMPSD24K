from config_utils import load_config, get_config_value, get_section_dict
from log_utils import setup_logging
import logging

from DataPreprocess import data_preprocessing
from ApiPromptSync import api_prompt_sync
from ApiPromptAsync import api_prompt_async
from DataPostprocess import data_postprocessing

def main():
    # 1、读取配置文件（相对路径）
    config = load_config("./ToolCodes/pipeline_config.ini")
    
    # 从配置中读取日志参数
    logging_cfg = get_section_dict(config, 'Logging')

    # 初始化日志系统
    log_path = setup_logging(
        logging_cfg["log_dir"], 
        logging_cfg["log_name"], 
        logging_cfg["max_mb"], 
        logging_cfg["backup_count"], 
        logging_cfg["console"]
    )
    
    logging.info("[main] 日志系统初始化完成，日志文件路径: %s", log_path)
    
    # 从配置中读取数据路径参数    
    datapath_cfg = get_section_dict(config, 'DATAPATH')
    sourceData_folder = datapath_cfg["source_folder"]
    sourceData_list = datapath_cfg["source_list"]
    
    logging.info(f"[main] 准备读取源数据，文件夹: {sourceData_folder}，文件列表: {sourceData_list}")

    # 2、数据预处理
    # 2.1、读取数据文件，返回 DataFrame
    filter_df = data_preprocessing(config, sourceData_list, sourceData_folder)
    logging.info(f"[main] 数据预处理完成，样本数量: {len(filter_df)}")
    
    # 3、API Pormopt 处理
    # 是否启用异步处理，同步sync: 1  异步async: 2, 默认值为: 1
    ASYNC_OR_SYNC = get_config_value(config, 'Processing_Mode', 'async_or_sync', fallback = 1)

    if ASYNC_OR_SYNC == 1:   # 同步处理
        logging.info("[main] 启动同步处理模式")
        label_translate_quantityRelation_df = api_prompt_sync(filter_df, config)
    elif ASYNC_OR_SYNC == 2:  # 异步处理
        logging.info("[main] 启动异步处理模式")
        label_translate_quantityRelation_df = api_prompt_async(filter_df, config)
    else:
        logging.error(f"[main] 无效的模式参数: {ASYNC_OR_SYNC}，请选择 'sync' 或 'async'")
        # raise ValueError(f"[main] 无效的模式参数: {ASYNC_OR_SYNC}，请选择 'sync' 或 'async'") # 不在控制台（stderr）输出错误信息

    # 4、分词 编号 标准化输出
    data_output = datapath_cfg["data_output"]
    logging.info(f"[main] 开始输出结果到: {data_output}")
    data_postprocessing(label_translate_quantityRelation_df, sourceData_list, data_output)
    logging.info("[main] 所有流程执行完毕！")
    
if __name__ == "__main__":
    """
    确保代码只在“直接运行该脚本”时才会被执行，而在被其他模块 import 时不会执行。
    __name__ 是 Python 的一个内置变量。当脚本被直接运行时，__name__ 的值是 "__main__";被其他文件通过 import 引入时，__name__ 的值就是该模块的名字
    """
    main()