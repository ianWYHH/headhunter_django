# 🚀 智能猎头招聘管理系统 (HeadHunter Django)

一个基于Django的现代化智能猎头招聘管理平台，集成AI辅助功能，为猎头顾问提供职位管理、候选人管理、智能匹配、邮件营销和客户关系管理的一站式解决方案。

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![Django Version](https://img.shields.io/badge/django-4.2%2B-green.svg)](https://djangoproject.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 功能特性

### 核心功能
- **职位管理**: 职位信息的增删改查，支持AI智能解析职位描述
- **候选人管理**: 候选人信息管理，支持分组和AI解析简历，AI预测职位标签
- **联系人管理**: 公司联系人信息管理，分组管理，邮件发送
- **智能匹配**: 基于关键词的职位-候选人匹配算法
- **邮件系统**: 多邮箱账户管理，邮件模板，AI智能生成邮件内容
- **定时任务**: 支持定时发送邮件到候选人分组和联系人分组
- **多邮箱管理**: 智能轮换发送邮箱，避免单邮箱发送限制
- **IMAP收件**: 自动接收候选人回信，关联到候选人档案
- **AI辅助**: 支持多种AI模型，智能解析和内容生成
- **SMTP状态检查**: 实时检测邮箱服务器连接状态，确保邮件发送可靠性
- **AI容错机制**: 智能故障转移，确保AI服务的高可用性
- **批处理功能**: 支持大批量数据的AI处理，具备容错和重试机制

### 技术特性
- **AI架构优化**: 基于适配器模式的AI管理系统，支持热插拔和故障转移
- **多AI模型支持**: 通义千问、Kimi、豆包、混元、深度求索、MiniMax、Together AI等
- **智能容错机制**: AI服务故障自动切换，重试策略和错误分类
- **批处理引擎**: 高效处理大批量数据，支持断点续传和错误恢复
- **数据加密存储**: API密钥等敏感信息采用Fernet加密
- **实时交互**: 基于HTMX的无刷新页面交互
- **邮件服务**: 完整的邮件发送队列、状态跟踪和SMTP健康检查
- **定时任务调度**: APScheduler后台调度系统
- **多邮箱智能管理**: 智能分配、限额管理和故障转移
- **IMAP自动收件**: 邮件关联和回复管理
- **全面日志记录**: 操作、邮件、AI调用等完整审计日志

## 安装和配置

### 1. 环境要求
- Python 3.8+
- MySQL 5.7+
- 现代浏览器（支持HTMX）

### 2. 安装依赖
```bash
pip install -r requirements.txt
# 新功能所需的额外依赖
pip install apscheduler pytz
```

### 3. 环境配置
1. 复制环境变量示例文件：
```bash
cp env_example.txt .env
```

2. 生成加密密钥：
```bash
python generate_key.py
```

3. 编辑 `.env` 文件，配置以下变量：
   - `DJANGO_SECRET_KEY`: Django密钥
   - `DB_*`: 数据库配置
   - `ENCRYPTION_KEY`: 加密密钥（从generate_key.py获取）
   - `EMAIL_*`: 邮件配置

### 4. 数据库设置
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. 创建超级用户
```bash
python manage.py createsuperuser
```

### 6. 运行开发服务器
```bash
python manage.py runserver
```

## 使用指南

### 1. 初始设置
1. 访问 `http://localhost:8000/register/` 注册账户
2. 在"API密钥管理"页面添加AI服务商的API密钥
3. 在"邮箱账户管理"页面配置发件邮箱
4. 在"多邮箱管理"页面配置多个发送邮箱（可选）

### 2. 职位管理
- 手动添加职位信息
- 或使用AI解析功能批量导入职位描述
- 支持文件上传（TXT、XLSX、DOCX）

### 3. 候选人管理
- 手动添加候选人信息
- 或使用AI解析功能批量导入简历，AI自动预测候选人适合的职位
- 支持候选人分组管理
- 系统自动提取并显示AI预测的职位标签

### 4. 联系人管理
- 管理公司联系人信息（姓名、邮箱、电话、职位、公司等）
- 创建联系人分组，支持批量管理
- 向联系人或联系人分组发送邮件
- 支持按姓名、邮箱、电话、公司搜索联系人

### 5. 智能匹配
- 系统自动基于关键词匹配职位和候选人
- 支持手动调整匹配结果

### 6. 邮件沟通
- 使用AI生成个性化邮件内容
- 支持邮件模板管理
- 批量发送邮件给候选人分组或联系人分组
- 多邮箱智能轮换发送，避免单邮箱发送限制
- SMTP连接状态实时监控和健康检查

### 7. 定时任务
- 创建定时邮件发送任务
- 支持向候选人分组或联系人分组定时发送邮件
- 可配置多个发送时间和邮件模板
- 支持使用多邮箱轮换发送

### 8. IMAP收件
- 配置IMAP账户自动接收候选人回信
- 系统自动将回信关联到相应的候选人档案
- 支持多个企业邮箱（如腾讯企业邮箱）

## 支持的AI模型

- **通义千问**: Plus、Turbo、Max
- **Kimi**: 32K、128K上下文
- **豆包**: Pro 32K、Pro 128K
- **腾讯混元**: Pro
- **深度求索**: Chat V2、Coder V2
- **MiniMax**: abab6.5、abab6.5s
- **ChatGLM**: GLM-4、GLM-4-Flash
- **Together AI**: Mixtral-8x22B、Llama3.1-70B、Llama3.2等
- **更多模型**: 支持任何OpenAI兼容的API接口

## 项目结构

```
headhunter_django/
├── headhunter_django/     # Django项目配置
├── jobs/                  # 主应用
│   ├── models.py         # 数据模型
│   ├── views.py          # 视图函数
│   ├── forms.py          # 表单
│   ├── admin.py          # Django Admin配置
│   ├── apps.py           # 应用配置（邮件调度器启动）
│   ├── urls.py           # URL路由
│   ├── services/         # 业务逻辑服务
│   │   ├── ai_manager.py          # AI管理器（新架构核心）
│   │   ├── ai_service.py          # AI服务
│   │   ├── ai_service_v2.py       # AI服务V2
│   │   ├── parsing_service.py     # 解析服务
│   │   ├── parsing_service_v2.py  # 解析服务V2
│   │   ├── batch_processing.py    # 批处理引擎
│   │   ├── smtp_status_checker.py # SMTP状态检查器
│   │   ├── matching_service.py    # 匹配服务
│   │   ├── mailing_service.py     # 邮件服务
│   │   ├── logging_service.py     # 日志服务
│   │   ├── mail_scheduler.py      # 定时邮件调度
│   │   ├── email_renderer.py      # 邮件模板渲染
│   │   ├── multi_email_service.py # 多邮箱服务
│   │   ├── imap_service.py        # IMAP收件服务
│   │   ├── contact_service.py     # 联系人服务
│   │   ├── ai_adapters/           # AI适配器
│   │   │   ├── base.py           # 基础适配器
│   │   │   ├── adapter_factory.py # 适配器工厂
│   │   │   ├── qwen_adapter.py   # 通义千问适配器
│   │   │   ├── kimi_adapter.py   # Kimi适配器
│   │   │   ├── doubao_adapter.py # 豆包适配器
│   │   │   └── ...               # 其他AI模型适配器
│   │   ├── ai_config/            # AI配置管理
│   │   │   ├── config_manager.py # 配置管理器
│   │   │   └── model_registry.py # 模型注册器
│   │   └── ai_fallback/          # AI容错机制
│   │       ├── fallback_manager.py # 容错管理器
│   │       ├── retry_strategy.py   # 重试策略
│   │       └── error_classifier.py # 错误分类器
│   ├── management/       # Django管理命令
│   │   └── commands/
│   │       └── fetch_emails.py  # IMAP收件命令
│   └── templates/        # 模板文件
├── requirements.txt      # 依赖包
├── manage.py            # Django管理脚本
├── generate_key.py      # 加密密钥生成工具
├── env_example.txt      # 环境变量示例
├── create_test_data.py  # 测试数据生成脚本
└── README.md           # 项目说明
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库配置和连接信息
   - 确保MySQL服务正在运行

2. **AI模型调用失败**
   - 检查API密钥是否正确配置
   - 确认API密钥有足够的额度
   - 检查网络连接

3. **邮件发送失败**
   - 检查邮箱账户配置
   - 确认SMTP设置正确
   - 检查防火墙设置

4. **加密错误**
   - 确保ENCRYPTION_KEY已正确设置
   - 重新生成加密密钥

5. **定时任务失败**
   - 检查APScheduler是否正确安装
   - 确认Django应用已启动邮件调度器
   - 查看调度器日志排查问题

6. **多邮箱轮换失败**
   - 检查邮箱账户配置是否正确
   - 确认邮箱发送限额设置
   - 查看邮箱统计数据

7. **IMAP收件失败**
   - 检查IMAP服务器配置
   - 确认邮箱IMAP权限已开启
   - 查看IMAP连接日志

8. **SMTP连接失败**
   - 使用SMTP状态检查器诊断连接问题
   - 检查服务器地址、端口和加密设置
   - 验证用户名和密码正确性

9. **AI服务故障**
   - 系统自动启用容错机制，尝试其他可用模型
   - 查看AI调用日志了解失败原因
   - 检查API密钥和额度状态

### 日志查看
- 应用日志在Django管理后台的"操作日志"页面
- 邮件发送记录在"邮件发送记录"页面
- 定时任务日志在"定时邮件任务"页面
- 联系人操作日志在"联系人操作记录"页面
- IMAP收件记录在"收到的邮件"页面

## 开发说明

### 添加新的AI模型
1. 在 `settings.py` 的 `AI_MODELS` 中添加配置
2. 确保模型支持OpenAI兼容的API格式

### 自定义邮件模板
1. 在"邮件设置"页面创建模板
2. 使用占位符：`{{candidate.name}}`、`{{job.title}}` 等

### 扩展匹配算法
- 修改 `matching_service.py` 中的匹配逻辑
- 可以添加更多匹配维度

### 添加新的定时任务
1. 扩展 `ScheduledEmailTask` 模型
2. 修改 `mail_scheduler.py` 中的调度逻辑
3. 在表单中添加新的任务配置选项

### 自定义邮箱轮换策略
- 修改 `multi_email_service.py` 中的分配算法
- 可以根据邮箱性能、发送成功率等因素优化

### 扩展联系人管理
- 在 `Contact` 模型中添加新字段
- 修改 `contact_service.py` 中的业务逻辑
- 更新相关表单和模板

## 许可证

本项目采用MIT许可证。

## 贡献

欢迎提交Issue和Pull Request来改进项目。 