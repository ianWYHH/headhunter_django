import logging
import json
import re
import openai
import pandas
import docx
from django.conf import settings
from .models import ApiKey
from .utils import decrypt_key


def call_ai_model(text: str, provider_key: str):
    """
    一个通用的AI模型调用函数。
    它会根据provider_key查找模型配置，并从数据库获取API Key。
    """
    # 1. 从settings.py获取模型的静态配置
    model_config = settings.AI_MODELS.get(provider_key)
    if not model_config:
        return {"error": "配置错误", "message": f"模型 '{provider_key}' 的配置未在settings.py中找到。"}

    # 2. 从配置中提取所需信息
    provider_for_db_lookup = model_config.get('provider')
    base_url = model_config.get('base_url')
    model_name = model_config.get('model_name')

    if not all([provider_for_db_lookup, base_url, model_name]):
        return {"error": "配置不完整", "message": f"模型 '{provider_key}' 在settings.py中的配置不完整。"}

    # 3. 使用 'provider' 字段从数据库获取加密的API Key
    try:
        api_key_obj = ApiKey.objects.get(provider=provider_for_db_lookup)
        api_key = decrypt_key(api_key_obj.api_key_encrypted)
    except ApiKey.DoesNotExist:
        return {"error": "密钥缺失",
                "message": f"未在数据库中找到服务商 '{provider_for_db_lookup.upper()}' 的API密钥，请先在“API密钥管理”页面添加。"}

    if not api_key:
        return {"error": "密钥无效", "message": "从数据库解密后的API密钥为空。"}

    # 4. 使用获取到的信息调用AI模型
    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)

        prompt = f"""
        你是一个专业的HR助手，负责将非结构化的职位描述(JD)文本精确地解析为结构化的JSON对象。
        请严格按照以下字段和类型定义来解析下面的职位描述文本。
        JSON输出格式:
        - "company_name": string | 公司名称。
        - "title": string | 职位名称。
        - "department": string | 所属部门。
        - "salary_range": string | 薪资范围。
        - "level_set": string[] | 职级要求。
        - "locations": string[] | 工作地点。
        - "skills": string[] | 核心技能要求。
        - "job_description": string | 完整的“职位描述”部分文本。
        - "job_requirement": string | 完整的“职位要求”部分文本。
        - "notes": string | 其他补充信息。
        约束:
        1. 如果某个字段找不到对应信息，请使用空字符串 "" 或空数组 []。
        2. 返回结果必须是一个能被`json.loads()`直接解析的、纯净的JSON对象。
        3. 不要在JSON对象前后包含任何解释性文字、说明或Markdown的```json标记。
        待解析的职位描述文本:
        ---
        {text}
        """
        messages = [{'role': 'system',
                     'content': '你是一个专门解析职位描述的助手，总是返回一个纯净的、不带任何额外解释的JSON对象。'},
                    {'role': 'user', 'content': prompt}]

        completion_params = {'model': model_name, 'messages': messages, 'temperature': 0.1}

        completion = client.chat.completions.create(**completion_params)
        content = completion.choices[0].message.content

        if "```json" in content:
            match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if match: content = match.group(1).strip()

        return json.loads(content)

    except openai.AuthenticationError:
        return {"error": "认证失败",
                "message": f"服务商 '{provider_for_db_lookup.upper()}' 的API密钥无效、过期或权限不足。请检查并更新密钥。"}
    except openai.RateLimitError:
        return {"error": "请求超限",
                "message": f"您对 '{provider_for_db_lookup.upper()}' 的请求频率过高或已超出当月额度。"}
    except openai.NotFoundError:
        return {"error": "模型未找到", "message": f"所选模型 '{model_name}' 不存在或当前服务商不支持。"}
    except openai.APITimeoutError:
        return {"error": "请求超时",
                "message": f"连接 '{provider_for_db_lookup.upper()}' 的API接口超时，请检查网络或稍后重试。"}
    except json.JSONDecodeError:
        return {"error": "格式错误", "message": f"AI模型返回了非JSON格式的内容，无法解析。"}
    except Exception as e:
        logging.error(f"调用 {provider_for_db_lookup} API时发生未知错误: {e}")
        return {"error": "未知错误", "message": f"调用API时发生未知错误: {e}"}


def get_texts_from_file(file):
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
