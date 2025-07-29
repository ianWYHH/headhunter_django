import logging
import json
import re
import openai
import pandas
import docx
from django.conf import settings
from ..models import ApiKey
from ..utils import decrypt_key

# 定义标准化的关键词列表
STANDARDIZED_KEYWORDS = [
    "计算机视觉", "自然语言处理", "大模型预训练", "推理", "后训练",
    "音频处理", "强化学习", "推荐系统", "图神经网络", "多模态",
    "Computer Vision", "Natural Language Processing", "LLM Pre-training",
    "Inference", "Post-training", "Audio Processing", "Reinforcement Learning",
    "Recommendation Systems", "Graph Neural Networks", "Multimodality"
]

def _call_ai_model(prompt: str, provider_key: str):
    """一个通用的、私有的AI模型调用函数。"""
    model_config = settings.AI_MODELS.get(provider_key)
    if not model_config:
        return {"error": "配置错误", "message": f"模型 '{provider_key}' 的配置未在settings.py中找到。"}

    provider_for_db_lookup = model_config.get('provider')
    base_url = model_config.get('base_url')
    model_name = model_config.get('model_name')

    if not all([provider_for_db_lookup, base_url, model_name]):
        return {"error": "配置不完整", "message": f"模型 '{provider_key}' 在settings.py中的配置不完整。"}

    try:
        api_key_obj = ApiKey.objects.get(provider=provider_for_db_lookup)
        api_key = decrypt_key(api_key_obj.api_key_encrypted)
    except ApiKey.DoesNotExist:
        return {"error": "密钥缺失", "message": f"未在数据库中找到服务商 '{provider_for_db_lookup.upper()}' 的API密钥，请先在“API密钥管理”页面添加。"}

    if not api_key:
        return {"error": "密钥无效", "message": "从数据库解密后的API密钥为空。"}

    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)
        messages = [{'role': 'system', 'content': '你是一个专业的HR助手，总是返回一个纯净的、不带任何额外解释的JSON对象或数组。'},
                      {'role': 'user', 'content': prompt}]
        completion_params = {'model': model_name, 'messages': messages, 'temperature': 0.1, 'response_format': {"type": "json_object"}}
        completion = client.chat.completions.create(**completion_params)
        content = completion.choices[0].message.content
        # AI有时会返回一个包含 "jobs" 键的根对象，我们需要从中提取数组
        data = json.loads(content)
        if isinstance(data, dict) and "jobs" in data and isinstance(data["jobs"], list):
            return data["jobs"]
        return data
    except openai.AuthenticationError:
        return {"error": "认证失败", "message": f"服务商 '{provider_for_db_lookup.upper()}' 的API密钥无效、过期或权限不足。请检查并更新密钥。"}
    except openai.RateLimitError:
        return {"error": "请求超限", "message": f"您对 '{provider_for_db_lookup.upper()}' 的请求频率过高或已超出当月额度。"}
    except openai.NotFoundError:
         return {"error": "模型未找到", "message": f"所选模型 '{model_name}' 不存在或当前服务商不支持。"}
    except openai.APITimeoutError:
        return {"error": "请求超时", "message": f"连接 '{provider_for_db_lookup.upper()}' 的API接口超时，请检查网络或稍后重试。"}
    except json.JSONDecodeError:
        return {"error": "格式错误", "message": f"AI模型返回了非JSON格式的内容，无法解析。"}
    except Exception as e:
        logging.error(f"调用 {provider_for_db_lookup} API时发生未知错误: {e}")
        return {"error": "未知错误", "message": f"调用API时发生未知错误: {e}"}

def parse_multiple_job_descriptions(text: str, provider_key: str):
    """(已重构) 解析可能包含多个职位的文本块"""
    keyword_list_str = ", ".join(STANDARDIZED_KEYWORDS)
    prompt = f"""
    你是一个专业的HR助手，负责将非结构化的职位描述(JD)文本精确地解析为结构化的JSON对象数组。
    文本块中可能包含一个或多个独立的职位描述。请你识别出所有的职位，并为每一个职位生成一个JSON对象。

    **关键词提取约束**: 对于每个职位的 "keywords" 字段，你必须只从下面的列表中提取与JD内容匹配的关键词。忽略所有编程语言、工具或框架。
    **允许的关键词列表**: {keyword_list_str}

    **最终输出格式**:
    你必须返回一个根键为 "jobs" 的JSON对象，其值是一个JSON数组 `[]`。数组中的每个元素都是一个符合以下结构的JSON对象:
    {{
        "company_name": string,
        "title": string,
        "department": string,
        "salary_range": string,
        "level_set": string[],
        "locations": string[],
        "keywords": string[] (必须来自上面的允许列表),
        "job_description": string,
        "job_requirement": string,
        "notes": string
    }}

    **规则**:
    1. 仔细分析整个文本，识别出所有独立的职位描述。
    2. 如果文本中只有一个职位，你的输出也必须是一个包含单个对象的JSON数组。
    3. 如果某个字段找不到信息，请使用空字符串 "" 或空数组 []。
    4. 返回结果必须是一个能被`json.loads()`直接解析的、纯净的JSON对象。

    **待解析的JD文本**:
    ---
    {text}
    """
    return _call_ai_model(prompt, provider_key)

def parse_candidate_resume(text: str, provider_key: str):
    """解析候选人简历"""
    keyword_list_str = ", ".join(STANDARDIZED_KEYWORDS)
    prompt = f"""
    你是一个专业的HR助手，负责将候选人简历文本精确地解析为结构化的JSON对象。
    **关键词提取约束**: 对于 "keywords" 字段，你必须只从下面的列表中提取与简历内容匹配的关键词。忽略所有编程语言、工具或框架。
    **允许的关键词列表**: {keyword_list_str}
    **JSON输出格式**:
    - "name": string
    - "emails": string[]
    - "homepage": string
    - "github_profile": string
    - "linkedin_profile": string
    - "external_id": integer | (可选) 候选人在其他系统中的数字ID
    - "keywords": string[] (必须来自上面的允许列表)
    **规则**:
    1. 如果某个字段找不到信息，请使用空字符串 ""、空数组 [] 或 null。
    2. 返回结果必须是一个能被`json.loads()`直接解析的、纯净的JSON对象。
    **待解析的简历文本**:
    ---
    {text}
    """
    return _call_ai_model(prompt, provider_key)

def get_texts_from_file(file):
    """从上传的文件中提取文本列表 (支持TXT, XLSX, DOCX)"""
    try:
        if file.name.endswith('.txt'):
            content = file.read().decode("utf-8")
            return [j.strip() for j in re.split(r'\n\s*\n|\n---\n', content) if j.strip()]
        elif file.name.endswith('.xlsx'):
            df = pandas.read_excel(file, engine='openpyxl').fillna('')
            return [", ".join(f"{c}: {v}" for c, v in row.items() if str(v).strip()) for _, row in df.iterrows()]
        elif file.name.endswith('.docx'):
            doc = docx.Document(file)
            return ["\n".join([p.text for p in doc.paragraphs])]
        return []
    except Exception as e:
        logging.error(f"解析文件 {file.name} 时出错: {e}")
        return []
