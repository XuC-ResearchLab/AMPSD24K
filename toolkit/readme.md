**1. Module Architecture of AutoMATH-Dataset:**

Core Processing Modules:<br>
(1) DataPreprocess.py: Ingests raw datasets with heterogeneous formats and aligns them to a unified schema. It applies filtering strategies based on length, numeric-only inputs, and malformed fields. This ensures input standardization, improves data quality, and prepares clean inputs for downstream processing.<br>
(2) ApiPromptAsync.py: An asynchronous GPT-4o annotator supporting multi-task annotation, including reasoning type classification, translation, quantity relation extraction, problem type labeling, and knowledge tagging. Enables high-throughput annotation, supports parallelism, and ensures scalability for large-scale datasets.<br>
(3) ApiPromptSync.py: Synchronous (serial) variant primarily used for debugging, prototyping, or small-batch annotation tasks. Provides deterministic behavior, facilitates debugging, and allows for quick iteration during pipeline development.<br>
(4) DataPostprocess.py: Conducts symbolic validation (via SymPy), equation normalization, and ID reindexing. Ensures mathematical correctness, enforces semantic consistency, and prepares data for benchmarking or model training.<br>
(5) main.py: Acts as the master controller orchestrating the full pipeline using a centralized configuration. Supports modular integration, enables automated execution, and ensures reproducibility.<br>
<br>
Configuration and Control Modules<br>
(1) pipeline_config.ini: Declarative configuration file that defines operational parameters such as file paths, model settings, API keys, filtering rules, and output formats. Facilitates smart pipeline control, enhances maintainability and reproducibility, and supports collaborative development.<br>
(2) config_utils.py: Loads and parses the centralized configuration from pipeline_config.ini, supporting section-wise access and automatic type conversion. Promotes separation of configuration and logic, improves reusability, and supports flexible reparameterization.<br>
(3) log_utils.py: Provides a unified logging interface supporting both console and file outputs, with configurable verbosity. Enhances debuggability, ensures transparent error tracking, and enables consistent monitoring throughout the pipeline.<br>
<br>

**2. Dataset:**

This toolkit AutoMATH-Dataset generated over 170,000 annotated problems, and for this study, a representative and balanced 24,000 benchmark was sampled using a 2:4:4 ratio across reasoning types for first-phase evaluation.
