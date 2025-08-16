from django.contrib.auth.models import User
from ..models import Job, Candidate

# 研究方向关键词列表 - 用于高层匹配
RESEARCH_DIRECTION_KEYWORDS = {
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
}


def find_matching_jobs(candidate: Candidate):
    """
    为指定候选人查找匹配的职位 (基于研究方向匹配)。
    匹配规则: 候选人和职位的研究方向关键词有任意一个重合即可。
    只考虑高层研究方向，忽略具体的技术技能和工具。
    
    :param candidate: Candidate 实例
    :return: 一个包含匹配职位信息的字典列表
    """
    if not candidate.keywords:
        return []

    matching_jobs = []
    
    # 提取候选人的研究方向关键词
    candidate_research_keywords = set()
    for keyword in candidate.keywords:
        if keyword in RESEARCH_DIRECTION_KEYWORDS:
            candidate_research_keywords.add(keyword)
    
    # 如果候选人没有研究方向关键词，返回空列表
    if not candidate_research_keywords:
        return []

    # 从所有活跃职位中进行匹配 (数据共享)
    active_jobs = Job.objects.filter(
        status__in=[Job.JobStatus.IN_PROGRESS, Job.JobStatus.PENDING]
    ).select_related('company')

    for job in active_jobs:
        if not job.keywords:
            continue

        # 提取职位的研究方向关键词
        job_research_keywords = set()
        for keyword in job.keywords:
            if keyword in RESEARCH_DIRECTION_KEYWORDS:
                job_research_keywords.add(keyword)
        
        # 如果职位没有研究方向关键词，跳过
        if not job_research_keywords:
            continue

        # 计算研究方向关键词的交集
        matched_research_keywords = candidate_research_keywords.intersection(job_research_keywords)

        if matched_research_keywords:
            matching_jobs.append({
                'job_id': job.id,
                'title': job.title,
                'company_name': job.company.name,
                'locations': job.locations,
                'level_set': job.level_set,
                'matched_keywords': list(matched_research_keywords),
                'match_count': len(matched_research_keywords),
                'candidate_research_areas': list(candidate_research_keywords),
                'job_research_areas': list(job_research_keywords)
            })

    # 按匹配关键词数量降序排序
    matching_jobs.sort(key=lambda x: x['match_count'], reverse=True)
    
    return matching_jobs


def get_research_direction_keywords():
    """
    获取所有研究方向关键词列表。
    
    :return: 研究方向关键词集合
    """
    return RESEARCH_DIRECTION_KEYWORDS.copy()


def filter_research_keywords(keywords_list):
    """
    从关键词列表中筛选出研究方向关键词。
    
    :param keywords_list: 关键词列表
    :return: 研究方向关键词列表
    """
    if not keywords_list:
        return []
    
    research_keywords = []
    for keyword in keywords_list:
        if keyword in RESEARCH_DIRECTION_KEYWORDS:
            research_keywords.append(keyword)
    
    return research_keywords


def calculate_research_match_score(candidate_keywords, job_keywords):
    """
    计算候选人和职位在研究方向上的匹配分数。
    
    :param candidate_keywords: 候选人关键词列表
    :param job_keywords: 职位关键词列表
    :return: 匹配分数字典，包含匹配数量、候选人研究方向数、职位研究方向数
    """
    candidate_research = set(filter_research_keywords(candidate_keywords))
    job_research = set(filter_research_keywords(job_keywords))
    
    if not candidate_research or not job_research:
        return {
            'match_count': 0,
            'match_ratio': 0.0,
            'candidate_research_count': len(candidate_research),
            'job_research_count': len(job_research),
            'matched_keywords': []
        }
    
    matched_keywords = candidate_research.intersection(job_research)
    match_count = len(matched_keywords)
    
    # 计算匹配比例 (匹配数量 / 候选人研究方向数量)
    match_ratio = match_count / len(candidate_research) if candidate_research else 0.0
    
    return {
        'match_count': match_count,
        'match_ratio': match_ratio,
        'candidate_research_count': len(candidate_research),
        'job_research_count': len(job_research),
        'matched_keywords': list(matched_keywords)
    }
