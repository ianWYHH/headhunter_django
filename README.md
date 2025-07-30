# 智能猎头招聘管理系统

一个基于Django的智能猎头招聘管理系统，集成了AI辅助功能，帮助猎头顾问高效管理职位、候选人和邮件沟通流程。

## 功能特性

### 核心功能
- **职位管理**: 职位信息的增删改查，支持AI智能解析职位描述
- **候选人管理**: 候选人信息管理，支持分组和AI解析简历
- **智能匹配**: 基于关键词的职位-候选人匹配算法
- **邮件系统**: 多邮箱账户管理，邮件模板，AI智能生成邮件内容
- **AI辅助**: 支持多种AI模型，智能解析和内容生成

### 技术特性
- 多AI模型支持（通义千问、Kimi、豆包、混元等）
- 数据加密存储（API密钥等敏感信息）
- 实时交互（HTMX）
- 邮件发送队列和状态跟踪
- 操作日志记录

## 安装和配置

### 1. 环境要求
- Python 3.8+
- MySQL 5.7+
- 现代浏览器（支持HTMX）

### 2. 安装依赖
```bash
pip install -r requirements.txt
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

### 2. 职位管理
- 手动添加职位信息
- 或使用AI解析功能批量导入职位描述
- 支持文件上传（TXT、XLSX、DOCX）

### 3. 候选人管理
- 手动添加候选人信息
- 或使用AI解析功能批量导入简历
- 支持候选人分组管理

### 4. 智能匹配
- 系统自动基于关键词匹配职位和候选人
- 支持手动调整匹配结果

### 5. 邮件沟通
- 使用AI生成个性化邮件内容
- 支持邮件模板管理
- 批量发送邮件给候选人分组

## 支持的AI模型

- **通义千问**: Plus、Turbo、Max
- **Kimi**: 32K、128K上下文
- **豆包**: Pro 32K、Pro 128K
- **腾讯混元**: Pro
- **深度求索**: Chat、Coder
- **MiniMax**: abab6.5
- **Together AI**: Mixtral-8x22B、Llama3.1-70B

## 项目结构

```
headhunter_django/
├── headhunter_django/     # Django项目配置
├── jobs/                  # 主应用
│   ├── models.py         # 数据模型
│   ├── views.py          # 视图函数
│   ├── forms.py          # 表单
│   ├── services/         # 业务逻辑服务
│   │   ├── ai_service.py      # AI服务
│   │   ├── parsing_service.py # 解析服务
│   │   ├── matching_service.py # 匹配服务
│   │   ├── mailing_service.py  # 邮件服务
│   │   └── logging_service.py  # 日志服务
│   └── templates/        # 模板文件
├── requirements.txt      # 依赖包
├── manage.py            # Django管理脚本
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

### 日志查看
- 应用日志在Django管理后台的"操作日志"页面
- 邮件发送记录在"邮件发送记录"页面

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

## 许可证

本项目采用MIT许可证。

## 贡献

欢迎提交Issue和Pull Request来改进项目。 