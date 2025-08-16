"""
Parsing Service V2

Enhanced parsing service using the new adapter architecture.
This provides backward compatibility while leveraging the new AI adapter system.
"""

import logging
import json
import re
import pandas as pd
import docx
from typing import Dict, Any
from django.contrib.auth.models import User

from .simple_ai_manager import SimpleAIManager

# 创建简化AI管理器实例
simple_ai_manager = SimpleAIManager()

logger = logging.getLogger(__name__)

# 定义研究方向关键词列表 (严格限制提取范围)
RESEARCH_DIRECTION_KEYWORDS = [
    "大模型", "LLM", "ChatGPT", "GPT", "Claude", "Gemini",
    "Transformer", "预训练", "对齐", "指令微调", "SFT", "RLHF", "RLAIF",
    "后训练", "Post-training", "Instruct-tuning", "Alignment",
    "微调", "参数高效微调", "PEFT", "LoRA", "Prompt Tuning", "Adapter", "Prefix Tuning",
    "Prompt Engineering", "Chain-of-Thought", "CoT", "Toolformer", "MoE",
    "多模态", "Multimodal", "图文", "语音多模态", "音视频理解", "VLM", "视觉语言模型",
    "图文匹配", "图文生成", "VQA", "图像字幕", "CLIP", "BLIP", "Video-Language", "文生图", "图生文",
    "自然语言处理", "NLP", "问答系统", "信息抽取", "文本生成", "语言建模", "意图识别", "命名实体识别", "对话系统", "情感分析", "文本分类", "摘要生成",
    "语音合成", "Speech Synthesis", "TTS", "语音识别", "ASR", "语音增强", "声学建模", "语音转写", "多说话人分离", "语音转换", "语音对话",
    "计算机视觉", "CV", "图像识别", "目标检测", "图像分割", "实例分割", "人体姿态估计", "OCR", "人脸识别", "图像生成", "Diffusion", "图像增强", "视频理解", "视频生成", "三维重建",
    "代码生成", "Code Generation", "Program Synthesis", "代码补全", "代码搜索", "程序理解", "自动修复", "代码翻译", "代码分析", "静态分析",
    "图神经网络", "GNN", "图表示学习", "Graph Learning", "图神经网络推理", "Knowledge Graph", "知识图谱", "KG", "关系抽取",
    "推荐系统", "Recommendation", "大规模推荐", "召回排序", "用户建模", "兴趣预测", "CTR预测", "搜索引擎", "信息检索", "Embedding Matching",
    "强化学习", "Reinforcement Learning", "Actor-Critic", "PPO", "DQN", "A3C", "MCTS", "智能体", "Agent", "任务规划", "控制策略",
    "大模型安全", "模型鲁棒性", "模型攻击", "对抗样本", "模型防御", "可解释性", "公平性", "隐私保护", "模型审计", "内容安全", "毒性检测",
    "模型压缩", "量化", "剪枝", "蒸馏", "边缘部署", "模型加速", "模型裁剪", "ONNX", "TensorRT", "服务器推理优化", "轻量模型",
    "大模型训练", "分布式训练", "并行训练", "数据并行", "模型并行", "张量并行", "流水并行", "异构计算", "A100", "H100", "Colossal-AI", "DeepSpeed", "Megatron", "FlashAttention",
    "推理服务", "推理引擎", "MII", "vLLM", "模型托管", "模型服务化", "A/B测试", "高可用", "弹性扩展", "容器化部署", "Kubernetes", "MLops", "AutoML", "Model Monitoring",
    "数据清洗", "数据增强", "数据合成", "Synthetic Data", "数据治理", "Data Pipeline", "训练集构建", "Web数据爬取", "Corpus构建", "Benchmark",
    "因果推理", "Causal Inference", "因果表示", "元学习", "Meta Learning", "自监督学习", "少样本学习", "多任务学习", "迁移学习",
    "AIGC", "数字人", "虚拟人", "Agent", "AI助手", "自动驾驶", "机器人", "人机交互", "XR", "AI for Science"
]


def _call_ai_model(prompt: str, provider_key: str, user: User) -> Dict[str, Any]:
    """
    通用的AI模型调用函数 - 使用新的适配器架构。
    
    这个函数保持与原始版本相同的接口，但内部使用新的AIManager。
    
    Args:
        prompt: 发送给模型的提示
        provider_key: 模型标识符
        user: 用户对象
        
    Returns:
        包含响应或错误信息的字典
    """
    # Use fallback-enabled calling for robust batch processing
    result = simple_ai_manager.parse_with_model(user, provider_key, prompt, 'job')
    
    # Enhanced result processing for parsing
    if result.get('success'):
        data = result.get('data', {})
        if isinstance(data, dict) and "jobs" in data and isinstance(data["jobs"], list):
            return data  # Return in expected format
        elif isinstance(data, dict) and "candidates" in data and isinstance(data["candidates"], list):
            return data  # Return candidate parsing format
        else:
            return data  # Return as-is for other formats
    else:
        # Return detailed error information for better debugging
        return {
            'error': result.get('error', 'unknown'),
            'message': result.get('message', 'AI解析失败'),
            'models_tried': result.get('models_tried', 0),
            'fallback_used': result.get('fallback_used', False),
            'human_log': result.get('human_readable_log', [])
        }


def parse_job_from_text(text: str, provider_key: str, user: User) -> Dict[str, Any]:
    """
    从文本中解析职位信息。
    
    Args:
        text: 包含职位信息的文本
        provider_key: AI模型标识符
        user: 用户对象
        
    Returns:
        解析结果字典
    """
    keyword_list_str = '", "'.join(RESEARCH_DIRECTION_KEYWORDS)
    
    prompt = f"""
你是一个专业的HR助手，负责将非结构化的职位描述(JD)文本精确地解析为结构化的JSON对象数组。
文本块中可能包含一个或多个独立的职位描述。请你识别出所有的职位，并为每一个职位生成一个JSON对象。

**【关键词提取字段要求】**：

1. "keywords" 字段的输出格式必须是 **JSON 字符串数组**，如：
```json
["大模型", "自然语言处理", "推荐系统"]
```

2. 所有关键词只能从下列"研究方向关键词列表"中选择：
["{keyword_list_str}"]

3. 如果解析内容中未发现任何关键词，返回空数组 []，不要返回字符串、"无" 或 null。

4. 严禁输出解释性语句、句子或段落，例如：
   - "该职位要求推荐系统" ❌
   - "关键词为：推荐系统、大模型" ❌  
   - "无关键词" ❌
   - "null" ❌
   - "推荐系统，大模型" ❌（这是字符串，不是数组）

5. 模型必须严格控制输出，不能发散或补充额外的词汇。

**最终输出格式**:
你必须返回一个根键为 "jobs" 的JSON对象，其值是一个JSON数组 `[]`。数组中的每个元素都是一个符合以下结构的JSON对象:
{{
    "company_name": string,
    "title": string,
    "department": string,
    "salary_range": string,
    "level_set": string[],
    "locations": string[],
    "keywords": string[] (只能从研究方向关键词列表中选择，格式必须是JSON数组),
    "job_description": string,
    "job_requirement": string,
    "notes": string
}}

**规则**:
1. 仔细分析整个文本，识别出所有独立的职位描述。
2. 如果文本中只有一个职位，你的输出也必须是一个包含单个对象的JSON数组。
3. 如果某个字段找不到信息，请使用空字符串 "" 或空数组 []。
4. keywords字段必须严格按照上述要求执行，只选择列表中存在的关键词。
5. 返回结果必须是一个能被`json.loads()`直接解析的、纯净的JSON对象。

**待解析的JD文本**:
---
{text}
---
"""
    
    return _call_ai_model(prompt, provider_key, user)


def parse_candidate_resume(text: str, provider_key: str, user: User) -> Dict[str, Any]:
    """
    从简历文本中解析候选人信息。
    
    Args:
        text: 候选人简历文本
        provider_key: AI模型标识符
        user: 用户对象
        
    Returns:
        解析结果字典
    """
    keyword_list_str = '", "'.join(RESEARCH_DIRECTION_KEYWORDS)
    prompt = f"""
    你是一个专业的HR助手，负责将候选人简历文本精确地解析为结构化的JSON对象。
    
    **【关键词提取字段要求】**：
    
    1. "keywords" 字段的输出格式必须是 **JSON 字符串数组**，如：
    ```json
    ["大模型", "自然语言处理", "推荐系统"]
    ```
    
    2. 所有关键词只能从下列"研究方向关键词列表"中选择：
    ["{keyword_list_str}"]
    
    3. 如果解析内容中未发现任何关键词，返回空数组 []，不要返回字符串、"无" 或 null。
    
    4. 严禁输出解释性语句、句子或段落，例如：
       - "该候选人擅长推荐系统" ❌
       - "关键词为：推荐系统、大模型" ❌
       - "无关键词" ❌
       - "null" ❌
       - "推荐系统，大模型" ❌（这是字符串，不是数组）
    
    5. 模型必须严格控制输出，不能发散或补充额外的词汇。

    **最终输出格式**:
    你必须返回一个根键为 "candidates" 的JSON对象，其值是一个JSON数组 `[]`。
    {{
        "name": string,
        "emails": string[],
        "homepage": string,
        "github_profile": string,
        "linkedin_profile": string,
        "external_id": integer | (可选) 候选人在其他系统中的数字ID,
        "birthday": string | (可选) 出生年月日，格式为 "YYYY-MM-DD" 或 "YYYY-MM" 或 "YYYY",
        "gender": string | (可选) 性别，只能是 "男"、"女"、"其他"、"未知" 中的一个,
        "location": string | (可选) 所在地，如 "北京"、"上海"、"深圳" 等,
        "education_level": string | (可选) 最高学历，只能是 "高中"、"大专"、"本科"、"硕士"、"博士"、"其他"、"未知" 中的一个,
        "predicted_position": string | (可选) AI根据简历内容判断该候选人目前从事或适合的职位名称，如 "AI算法工程师"、"机器学习工程师"、"深度学习研究员" 等,
        "keywords": string[] (只能从研究方向关键词列表中选择，格式必须是JSON数组)
    }}
    
    **规则**:
    1. 如果某个字段找不到信息，请使用空字符串 ""、空数组 [] 或 null。
    2. birthday字段如果只能确定年份，使用 "YYYY" 格式；如果能确定年月，使用 "YYYY-MM" 格式；如果能确定具体日期，使用 "YYYY-MM-DD" 格式。
    3. gender字段必须严格匹配给定的选项。
    4. education_level字段必须严格匹配给定的选项。
    5. predicted_position字段应该基于候选人的技能、工作经历、项目经验等综合判断，给出最合适的职位名称。
    6. keywords字段必须严格按照上述要求执行，只选择列表中存在的关键词。
    7. 返回结果必须是一个能被`json.loads()`直接解析的、纯净的JSON对象。
    
    **待解析的简历文本**:
    ---
    {text}
    """
    return _call_ai_model(prompt, provider_key, user)


def parse_multiple_job_descriptions(text: str, provider_key: str, user: User) -> Dict[str, Any]:
    """
    解析可能包含多个职位的文本块。
    
    Args:
        text: 包含一个或多个职位描述的文本
        provider_key: AI模型标识符
        user: 用户对象
        
    Returns:
        解析结果字典
    """
    return parse_job_from_text(text, provider_key, user)


def parse_from_file_upload(file, provider_key: str, user: User) -> Dict[str, Any]:
    """
    从上传的文件中解析职位信息。
    
    Args:
        file: 上传的文件对象
        provider_key: AI模型标识符
        user: 用户对象
        
    Returns:
        解析结果字典
    """
    try:
        # Extract text content from file
        texts = get_texts_from_file(file)
        if not texts:
            return {
                'error': 'file_parsing_failed',
                'message': f'无法从文件 {file.name} 中提取文本内容'
            }
        
        # Combine all text content
        full_text = '\n\n'.join(texts)
        
        # Parse the combined text
        return parse_job_from_text(full_text, provider_key, user)
        
    except Exception as e:
        logger.error(f"Error parsing file {file.name}: {e}")
        return {
            'error': 'file_processing_error',
            'message': f'处理文件时发生错误: {str(e)}'
        }


def parse_candidate_from_file_upload(file, provider_key: str, user: User) -> Dict[str, Any]:
    """
    从上传的文件中解析候选人简历信息。
    
    Args:
        file: 上传的简历文件对象
        provider_key: AI模型标识符
        user: 用户对象
        
    Returns:
        解析结果字典
    """
    try:
        # Extract text content from file
        texts = get_texts_from_file(file)
        if not texts:
            return {
                'error': 'file_parsing_failed',
                'message': f'无法从文件 {file.name} 中提取文本内容'
            }
        
        # Combine all text content
        full_text = '\n\n'.join(texts)
        
        # Parse the combined text as candidate resume
        return parse_candidate_resume(full_text, provider_key, user)
        
    except Exception as e:
        logger.error(f"Error parsing candidate file {file.name}: {e}")
        return {
            'error': 'file_processing_error',
            'message': f'处理简历文件时发生错误: {str(e)}'
        }


def parse_job_description_with_ai(text: str, provider_key: str, user: User) -> Dict[str, Any]:
    """
    使用AI解析职位描述 - 这个函数提供向后兼容性。
    
    Args:
        text: 职位描述文本
        provider_key: AI模型标识符
        user: 用户对象
        
    Returns:
        解析结果字典
    """
    return parse_job_from_text(text, provider_key, user)


def get_texts_from_file(file):
    """
    从上传的文件中提取文本列表 (支持TXT, XLSX, DOCX)
    
    Args:
        file: 上传的文件对象
        
    Returns:
        文本内容列表
    """
    try:
        if file.name.endswith('.txt'):
            content = file.read().decode("utf-8")
            return [j.strip() for j in re.split(r'\n\s*\n|\n---\n', content) if j.strip()]
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file, engine='openpyxl').fillna('')
            return [", ".join(f"{c}: {v}" for c, v in row.items() if str(v).strip()) for _, row in df.iterrows()]
        elif file.name.endswith('.docx'):
            doc = docx.Document(file)
            return ["\n".join([p.text for p in doc.paragraphs])]
        return []
    except Exception as e:
        logger.error(f"解析文件 {file.name} 时出错: {e}")
        return []