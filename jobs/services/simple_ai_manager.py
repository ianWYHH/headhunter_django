"""
简化的AI管理器
去掉复杂的回退机制，只保留基本的模型选择和解析功能
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from django.contrib.auth.models import User
from django.conf import settings
from jobs.models import ApiKey
from jobs.utils import decrypt_key

# 确保清除任何可能影响OpenAI客户端的环境变量
if 'OPENAI_PROXY' in os.environ:
    del os.environ['OPENAI_PROXY']
if 'HTTP_PROXY' in os.environ:
    del os.environ['HTTP_PROXY']
if 'HTTPS_PROXY' in os.environ:
    del os.environ['HTTPS_PROXY']

import openai

logger = logging.getLogger(__name__)

# 研究方向关键词列表（与parsing_service.py保持一致）
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


class SimpleAIManager:
    """
    简化的AI管理器 - 直接调用指定模型，无复杂回退机制
    """
    
    def __init__(self):
        """初始化简单AI管理器"""
        self._adapters_cache = {}
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有可用的AI模型
        
        Returns:
            Dict: 模型配置字典
        """
        try:
            return getattr(settings, 'AI_MODELS', {})
        except Exception as e:
            logger.error(f"获取可用模型失败: {e}")
            return {}
    
    def get_model_info(self, model_key: str) -> Dict[str, Any]:
        """
        获取指定模型的详细信息
        
        Args:
            model_key: 模型键值
            
        Returns:
            Dict: 模型信息
        """
        models = self.get_available_models()
        return models.get(model_key, {})
    
    def parse_with_model(self, user: User, model_key: str, content: str, 
                        parse_type: str = 'candidate') -> Dict[str, Any]:
        """
        使用指定模型解析内容
        
        Args:
            user: 用户对象
            model_key: 模型键值 (如 'qwen_plus')
            content: 要解析的内容
            parse_type: 解析类型 ('candidate' 或 'job')
            
        Returns:
            Dict: 解析结果
        """
        try:
            # 获取模型信息
            model_info = self.get_model_info(model_key)
            if not model_info:
                return {
                    'success': False,
                    'error': f'未找到模型: {model_key}',
                    'data': None
                }
            
            # 记录开始解析
            logger.info(f"开始使用模型 {model_key} 解析 {parse_type}")
            
            # 直接调用基础API（不使用适配器）
            result = self._call_basic_api(model_key, content, parse_type, user)
            
            if result.get('success'):
                logger.info(f"模型 {model_key} 解析成功")
                return {
                    'success': True,
                    'data': result.get('data'),
                    'model_used': model_key,
                    'model_name': model_info.get('display_name', model_key)
                }
            else:
                logger.warning(f"模型 {model_key} 解析失败: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error', '解析失败'),
                    'data': None
                }
                
        except Exception as e:
            logger.error(f"解析过程出错: {e}")
            return {
                'success': False,
                'error': f'解析过程出错: {str(e)}',
                'data': None
            }
    
    def _call_basic_api(self, model_key: str, content: str, parse_type: str, user: User) -> Dict[str, Any]:
        """直接调用基础AI API"""
        try:
            # 获取模型配置
            model_info = self.get_model_info(model_key)
            if not model_info:
                return {'success': False, 'error': f'模型配置不存在: {model_key}'}
            
            provider = model_info.get('provider')
            base_url = model_info.get('base_url')
            model_name = model_info.get('model_name')
            
            if not all([provider, base_url, model_name]):
                return {'success': False, 'error': f'模型配置不完整: {model_key}'}
            
            # 获取API密钥
            try:
                api_key_obj = ApiKey.objects.get(user=user, provider=provider)
                api_key = decrypt_key(api_key_obj.api_key_encrypted)
            except ApiKey.DoesNotExist:
                return {
                    'success': False, 
                    'error': f'未找到 {provider.upper()} 的API密钥，请先添加'
                }
            
            if not api_key:
                return {'success': False, 'error': 'API密钥解密失败'}
            
            # 构建prompt
            prompt = self._build_parse_prompt(content, parse_type)
            
            # 调用OpenAI兼容的API - 使用最简单的方式
            messages = [
                {'role': 'system', 'content': '你是一个专业的HR助手，总是返回纯净的JSON格式数据。必须严格按照用户要求的JSON结构返回，不要添加任何解释文字或markdown格式。'},
                {'role': 'user', 'content': prompt}
            ]
            
            # 使用requests直接调用API，避免OpenAI库的兼容性问题
            import requests
            import json
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': model_name,
                'messages': messages,
                'temperature': 0.1,
                'stream': False
            }
            
            # 直接HTTP调用，避免库兼容性问题
            try:
                response = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                response_text = result['choices'][0]['message']['content']
            except requests.exceptions.RequestException as req_error:
                logger.error(f"HTTP请求失败: {req_error}")
                return {'success': False, 'error': f'API请求失败: {str(req_error)}'}
            except Exception as api_error:
                logger.error(f"API调用异常: {api_error}")
                return {'success': False, 'error': f'API调用异常: {str(api_error)}'}
            
            # 解析JSON响应
            try:
                # 记录原始响应内容用于调试
                logger.info(f"=== AI管理器调试信息 ===")
                logger.info(f"AI响应状态码: {response.status_code}")
                logger.info(f"AI完整原始响应: {response_text}")
                logger.info(f"响应长度: {len(response_text)}")
                
                # 尝试直接解析JSON
                try:
                    data = json.loads(response_text)
                    logger.info(f"JSON解析成功，数据类型: {type(data)}")
                    logger.info(f"解析后数据: {data}")
                    return {'success': True, 'data': data}
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}")
                    # 如果直接解析失败，尝试提取JSON部分
                    import re
                    # 查找JSON块
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        logger.info(f"提取到JSON块: {json_str}")
                        try:
                            data = json.loads(json_str)
                            logger.info(f"提取的JSON解析成功: {data}")
                            return {'success': True, 'data': data}
                        except json.JSONDecodeError as e2:
                            logger.error(f"提取的JSON解析也失败: {e2}")
                            pass
                    
                    # 如果仍然失败，记录详细错误信息
                    logger.error(f"所有JSON解析方法都失败，原始内容: {response_text}")
                    return {'success': False, 'error': f'返回内容不是有效JSON: {response_text[:200]}...'}
            except Exception as json_error:
                logger.error(f"JSON处理异常: {json_error}")
                return {'success': False, 'error': f'JSON处理失败: {str(json_error)}'}
                
        except Exception as e:
            logger.error(f"基础API调用失败: {e}")
            return {'success': False, 'error': f'API调用失败: {str(e)}'}
    
    def _build_parse_prompt(self, content: str, parse_type: str) -> str:
        """构建解析提示"""
        if parse_type == 'candidate':
            keyword_list_str = '", "'.join(RESEARCH_DIRECTION_KEYWORDS)
            return f"""你是一个专业的HR助手，负责将候选人简历文本精确地解析为结构化的JSON对象。
    
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
    你必须返回一个根键为 "candidates" 的JSON对象，其值是一个JSON数组 []。数组中的每个对象包含以下字段：
    {{
        "candidates": [
            {{
                "name": string,
                "emails": string[],
                "homepage": string,
                "github_profile": string,
                "linkedin_profile": string,
                "external_id": integer | (可选) 候选人的外部系统标识符，从"No. 123456"、"员工编号: 12345"、"ID: 98765"等格式中提取纯数字,
                "birthday": string | (可选) 出生年月日，格式为 "YYYY-MM-DD" 或 "YYYY-MM" 或 "YYYY",
                "gender": string | (可选) 性别，只能是 "男"、"女"、"其他"、"未知" 中的一个,
                "location": string | (可选) 所在地，如 "北京"、"上海"、"深圳" 等,
                "education_level": string | (可选) 最高学历，只能是 "高中"、"大专"、"本科"、"硕士"、"博士"、"其他"、"未知" 中的一个,
                "predicted_position": string | (可选) AI根据简历内容判断该候选人目前从事或适合的职位名称，如 "AI算法工程师"、"机器学习工程师"、"深度学习研究员" 等,
                "keywords": string[] (只能从研究方向关键词列表中选择，格式必须是JSON数组)
            }}
        ]
    }}
    
    **规则**:
    1. 如果某个字段找不到信息，请使用空字符串 ""、空数组 [] 或 null。
    2. birthday字段如果只能确定年份，使用 "YYYY" 格式；如果能确定年月，使用 "YYYY-MM" 格式；如果能确定具体日期，使用 "YYYY-MM-DD" 格式。
    3. gender字段必须严格匹配给定的选项。
    4. education_level字段必须严格匹配给定的选项。
    5. predicted_position字段应该基于候选人的技能、工作经历、项目经验等综合判断，给出最合适的职位名称。
    6. keywords字段必须严格按照上述要求执行，只选择列表中存在的关键词。
    7. external_id字段应该从简历中提取任何数字标识符，包括但不限于：
       - "员工编号: 12345" → 12345
       - "工号: E001" → 1  
       - "用户ID: 98765" → 98765
       - "No. 111110" → 111110
       - "编号: A123456" → 123456
       - "ID: 789012" → 789012
       只提取数字部分，忽略字母前缀。
    8. 返回结果必须是一个能被`json.loads()`直接解析的、纯净的JSON对象。
    
    **待解析的简历文本**:
    ---
    {content}
    """
        
        elif parse_type == 'job':
            keyword_list_str = '", "'.join(RESEARCH_DIRECTION_KEYWORDS)
            return f"""你是一个专业的HR助手，负责将非结构化的职位描述(JD)文本精确地解析为结构化的JSON对象。
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
    你必须返回一个根键为 "jobs" 的JSON对象，其值是一个包含职位对象的JSON数组。每个职位对象必须包含以下字段：
    {{
        "jobs": [
            {{
                "title": string,
                "company_name": string,
                "location": string[],
                "salary_range": string,
                "department": string,
                "job_description": string,
                "job_requirement": string,
                "keywords": string[]
            }}
        ]
    }}
    
    **重要提醒**：请严格按照上述格式输出，不要在jobs数组的元素内再嵌套jobs字段！
    
    **字段说明**:
    - title: 从文本中提取职位标题
    - company_name: 提取公司名称
    - location: 提取工作地点，必须是数组格式，如["上海", "北京", "杭州"]
    - salary_range: 提取薪资信息
    - department: 提取部门信息
    - job_description: 提取岗位职责部分的内容
    - job_requirement: 提取任职要求部分的内容
    - keywords: 从研究方向关键词列表中匹配相关技术关键词
    
    **规则**:
    1. 如果某个字段找不到信息，请使用空字符串 ""、空数组 [] 或 null。
    2. location字段必须是JSON数组，即使只有一个地点也要用数组格式。
    3. keywords字段必须严格按照上述要求执行，只选择列表中存在的关键词。
    4. 返回结果必须是一个能被`json.loads()`直接解析的、纯净的JSON对象。
    5. 确保所有字段名称完全匹配上述格式。
    
    **待解析的职位描述文本**:
    ---
    {content}
    """
        
        else:
            return f"请分析以下内容：\n\n{content}"


# 创建全局实例
simple_ai_manager = SimpleAIManager()