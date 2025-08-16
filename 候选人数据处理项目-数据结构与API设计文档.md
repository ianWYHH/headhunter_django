# 📋 数据结构与API设计文档 - 候选人数据处理项目

## 🏗️ **项目架构建议**

```
crawler_project/                    # 爬虫数据处理项目
├── 📁 crawler/                     # 爬虫模块
│   ├── spiders/                    # 爬虫脚本
│   ├── items.py                    # 数据项定义
│   ├── pipelines.py                # 数据处理管道
│   └── settings.py                 # 爬虫配置
├── 📁 processor/                   # 数据处理模块
│   ├── normalizer.py               # 数据标准化
│   ├── validator.py                # 数据验证
│   └── formatter.py                # 数据格式化
├── 📁 api/                         # API接口模块
│   ├── models.py                   # 数据模型
│   ├── views.py                    # API视图
│   └── serializers.py              # 数据序列化
├── 📁 output/                      # 输出模块
│   ├── json_exporter.py            # JSON导出
│   ├── sql_generator.py            # SQL生成
│   └── api_sender.py               # API发送
└── 📄 requirements.txt             # 项目依赖
```

---

## 🗄️ **目标系统数据结构**

### 1️⃣ **候选人核心数据结构**

#### 📊 **数据库表结构**

```sql
-- ===============================================
-- 候选人信息表 (jobs_candidate)
-- ===============================================
CREATE TABLE `jobs_candidate` (
  -- 基础字段
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(100) NOT NULL COMMENT '候选人姓名',
  `email` varchar(254) DEFAULT NULL COMMENT '邮箱地址',
  `phone` varchar(20) DEFAULT NULL COMMENT '手机号码',
  
  -- 职业信息
  `current_position` varchar(200) DEFAULT NULL COMMENT '当前职位',
  `current_company` varchar(200) DEFAULT NULL COMMENT '当前公司',
  `experience_years` int(11) DEFAULT NULL COMMENT '工作年限(整数)',
  `education` varchar(200) DEFAULT NULL COMMENT '最高学历',
  
  -- 技能和能力
  `skills` longtext DEFAULT NULL COMMENT '技能标签(JSON数组格式)',
  `predicted_job_tags` longtext DEFAULT NULL COMMENT 'AI预测适合职位标签(JSON数组)',
  
  -- 简历相关
  `resume_file` varchar(100) DEFAULT NULL COMMENT '简历文件路径',
  `resume_content` longtext DEFAULT NULL COMMENT '简历文本内容',
  `ai_parsed_data` longtext DEFAULT NULL COMMENT 'AI解析的结构化数据(JSON)',
  
  -- 求职意向
  `salary_expectation` varchar(100) DEFAULT NULL COMMENT '期望薪资',
  `location_preference` varchar(200) DEFAULT NULL COMMENT '期望工作地点',
  `availability` varchar(50) DEFAULT NULL COMMENT '可入职时间',
  
  -- 管理字段
  `notes` longtext DEFAULT NULL COMMENT '备注信息',
  `status` varchar(20) DEFAULT 'active' COMMENT '状态(active/inactive/hired/blacklist)',
  `source` varchar(100) DEFAULT NULL COMMENT '数据来源渠道',
  `user_id` bigint(20) NOT NULL COMMENT '所属用户ID',
  
  -- 时间戳
  `created_at` datetime(6) NOT NULL COMMENT '创建时间',
  `updated_at` datetime(6) NOT NULL COMMENT '更新时间',
  
  -- 索引
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_email_user` (`email`, `user_id`),
  KEY `idx_phone` (`phone`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='候选人信息表';

-- ===============================================
-- 候选人分组表 (jobs_candidategroup)
-- ===============================================
CREATE TABLE `jobs_candidategroup` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '分组ID',
  `name` varchar(100) NOT NULL COMMENT '分组名称',
  `description` longtext DEFAULT NULL COMMENT '分组描述',
  `color` varchar(20) DEFAULT '#007bff' COMMENT '分组颜色代码',
  `tags` longtext DEFAULT NULL COMMENT '分组标签(JSON数组)',
  `user_id` bigint(20) NOT NULL COMMENT '所属用户ID',
  `created_at` datetime(6) NOT NULL COMMENT '创建时间',
  `updated_at` datetime(6) NOT NULL COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_name_user` (`name`, `user_id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='候选人分组表';

-- ===============================================
-- 候选人分组关联表 (jobs_candidate_groups)
-- ===============================================
CREATE TABLE `jobs_candidate_groups` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `candidate_id` bigint(20) NOT NULL COMMENT '候选人ID',
  `candidategroup_id` bigint(20) NOT NULL COMMENT '分组ID',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_candidate_group` (`candidate_id`, `candidategroup_id`),
  KEY `idx_candidate_id` (`candidate_id`),
  KEY `idx_group_id` (`candidategroup_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='候选人分组关联表';
```

### 2️⃣ **JSON数据格式规范**

#### 🏷️ **技能标签格式 (skills)**
```json
{
  "programming_languages": ["Python", "Java", "JavaScript", "Go"],
  "frameworks": ["Django", "Spring Boot", "React", "Vue.js"],
  "databases": ["MySQL", "Redis", "MongoDB", "PostgreSQL"],
  "tools": ["Git", "Docker", "Kubernetes", "Jenkins"],
  "soft_skills": ["团队协作", "项目管理", "沟通能力"],
  "certifications": ["AWS认证", "PMP认证"],
  "languages": [
    {"language": "中文", "level": "母语"},
    {"language": "英语", "level": "熟练"}
  ]
}
```

#### 🎯 **AI预测职位标签格式 (predicted_job_tags)**
```json
{
  "primary_roles": [
    {"role": "后端开发工程师", "confidence": 0.95},
    {"role": "全栈开发工程师", "confidence": 0.85}
  ],
  "secondary_roles": [
    {"role": "技术经理", "confidence": 0.70},
    {"role": "架构师", "confidence": 0.65}
  ],
  "industries": ["互联网", "金融科技", "电商"],
  "seniority_level": "中级", // 初级/中级/高级/专家
  "job_categories": ["技术", "研发", "后端"]
}
```

#### 🤖 **AI解析数据格式 (ai_parsed_data)**
```json
{
  "extraction_info": {
    "model_used": "qwen-plus",
    "confidence": 0.92,
    "extraction_time": "2024-01-15T10:30:00Z",
    "source_type": "resume_pdf"
  },
  "personal_info": {
    "full_name": "张三",
    "gender": "男",
    "age": 28,
    "birth_year": 1995,
    "marital_status": "未婚"
  },
  "contact_info": {
    "emails": ["zhangsan@example.com"],
    "phones": ["13800138000"],
    "location": "北京市朝阳区",
    "address": "具体地址信息"
  },
  "education": [
    {
      "school": "清华大学",
      "degree": "本科",
      "major": "计算机科学与技术",
      "start_date": "2013-09",
      "end_date": "2017-07",
      "gpa": "3.8/4.0"
    }
  ],
  "work_experience": [
    {
      "company": "字节跳动",
      "position": "高级后端开发工程师",
      "start_date": "2020-03",
      "end_date": "2024-01",
      "duration": "3年10个月",
      "responsibilities": [
        "负责推荐系统后端开发",
        "优化系统性能，提升QPS 50%",
        "带领3人小团队完成项目"
      ],
      "technologies": ["Python", "Django", "MySQL", "Redis"]
    }
  ],
  "projects": [
    {
      "name": "用户推荐系统",
      "role": "核心开发",
      "duration": "6个月",
      "description": "构建千万级用户推荐系统",
      "technologies": ["Python", "TensorFlow", "Redis"],
      "achievements": ["提升点击率15%", "日处理请求1亿次"]
    }
  ],
  "skills_analysis": {
    "technical_skills": {
      "programming": ["Python", "Java", "JavaScript"],
      "frameworks": ["Django", "Spring"],
      "databases": ["MySQL", "Redis"],
      "proficiency_level": "高级"
    },
    "years_experience": {
      "total": 6,
      "python": 5,
      "backend": 6,
      "team_lead": 2
    }
  },
  "salary_info": {
    "current_salary": "年薪40万",
    "expected_salary": "年薪50-60万",
    "currency": "CNY"
  }
}
```

---

## 📝 **数据处理项目代码结构**

### 1️⃣ **数据项定义 (items.py)**

```python
import scrapy
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class CandidateItem:
    """候选人数据项"""
    
    # 基础信息
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    
    # 职业信息  
    current_position: Optional[str] = None
    current_company: Optional[str] = None
    experience_years: Optional[int] = None
    education: Optional[str] = None
    
    # 技能和标签
    skills: List[str] = None
    predicted_job_tags: List[str] = None
    
    # 简历相关
    resume_file: Optional[str] = None
    resume_content: Optional[str] = None
    ai_parsed_data: Optional[Dict[str, Any]] = None
    
    # 求职意向
    salary_expectation: Optional[str] = None
    location_preference: Optional[str] = None
    availability: Optional[str] = None
    
    # 管理字段
    notes: Optional[str] = None
    status: str = 'active'
    source: Optional[str] = None
    
    # 时间戳
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 原始数据
    raw_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'current_position': self.current_position,
            'current_company': self.current_company,
            'experience_years': self.experience_years,
            'education': self.education,
            'skills': self.format_skills(),
            'predicted_job_tags': self.format_job_tags(),
            'resume_file': self.resume_file,
            'resume_content': self.resume_content,
            'ai_parsed_data': self.format_ai_data(),
            'salary_expectation': self.salary_expectation,
            'location_preference': self.location_preference,
            'availability': self.availability,
            'notes': self.notes,
            'status': self.status,
            'source': self.source,
            'created_at': self.created_at or datetime.now(),
            'updated_at': datetime.now()
        }
    
    def format_skills(self) -> str:
        """格式化技能为JSON字符串"""
        if not self.skills:
            return '[]'
        import json
        return json.dumps(self.skills, ensure_ascii=False)
    
    def format_job_tags(self) -> str:
        """格式化职位标签为JSON字符串"""
        if not self.predicted_job_tags:
            return '[]'
        import json
        return json.dumps(self.predicted_job_tags, ensure_ascii=False)
    
    def format_ai_data(self) -> str:
        """格式化AI数据为JSON字符串"""
        if not self.ai_parsed_data:
            return '{}'
        import json
        return json.dumps(self.ai_parsed_data, ensure_ascii=False)
```

### 2️⃣ **数据处理管道 (pipelines.py)**

```python
import json
import mysql.connector
from datetime import datetime
import logging
from typing import Dict, Any

class DataValidationPipeline:
    """数据验证管道"""
    
    def process_item(self, item: CandidateItem, spider):
        """验证数据项"""
        
        # 必填字段验证
        if not item.name or not item.name.strip():
            raise ValueError("候选人姓名不能为空")
        
        # 邮箱格式验证
        if item.email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, item.email):
                spider.logger.warning(f"邮箱格式不正确: {item.email}")
                item.email = None
        
        # 手机号格式验证
        if item.phone:
            phone_clean = re.sub(r'[^\d]', '', item.phone)
            if len(phone_clean) == 11 and phone_clean.startswith('1'):
                item.phone = phone_clean
            else:
                spider.logger.warning(f"手机号格式不正确: {item.phone}")
                item.phone = None
        
        # 工作年限验证
        if item.experience_years is not None:
            if not isinstance(item.experience_years, int) or item.experience_years < 0 or item.experience_years > 50:
                spider.logger.warning(f"工作年限不合理: {item.experience_years}")
                item.experience_years = None
        
        return item

class DataNormalizationPipeline:
    """数据标准化管道"""
    
    def process_item(self, item: CandidateItem, spider):
        """标准化数据"""
        
        # 姓名标准化
        if item.name:
            item.name = item.name.strip()
        
        # 公司名称标准化
        if item.current_company:
            # 移除常见的公司后缀变体
            company_suffixes = ['有限公司', '股份有限公司', '科技有限公司', 'Ltd.', 'Inc.', 'Corp.']
            for suffix in company_suffixes:
                if item.current_company.endswith(suffix):
                    item.current_company = item.current_company[:-len(suffix)].strip()
                    break
        
        # 职位名称标准化
        if item.current_position:
            # 标准化常见职位名称
            position_mapping = {
                '软件开发工程师': '软件工程师',
                '程序员': '软件工程师', 
                'Java开发': 'Java工程师',
                'Python开发': 'Python工程师',
                '前端开发': '前端工程师',
                '后端开发': '后端工程师',
            }
            
            item.current_position = position_mapping.get(
                item.current_position, 
                item.current_position
            )
        
        # 技能标准化
        if item.skills:
            normalized_skills = []
            skill_mapping = {
                'javascript': 'JavaScript',
                'python': 'Python',
                'java': 'Java',
                'mysql': 'MySQL',
                'redis': 'Redis',
            }
            
            for skill in item.skills:
                skill_lower = skill.lower().strip()
                normalized_skill = skill_mapping.get(skill_lower, skill.strip())
                if normalized_skill and normalized_skill not in normalized_skills:
                    normalized_skills.append(normalized_skill)
            
            item.skills = normalized_skills
        
        return item

class DatabaseExportPipeline:
    """数据库导出管道"""
    
    def __init__(self, mysql_settings):
        self.mysql_settings = mysql_settings
        self.connection = None
        
    @classmethod
    def from_crawler(cls, crawler):
        mysql_settings = crawler.settings.getdict("MYSQL_SETTINGS")
        return cls(mysql_settings)
    
    def open_spider(self, spider):
        """爬虫启动时连接数据库"""
        self.connection = mysql.connector.connect(**self.mysql_settings)
        spider.logger.info("数据库连接已建立")
    
    def close_spider(self, spider):
        """爬虫结束时关闭数据库连接"""
        if self.connection:
            self.connection.close()
            spider.logger.info("数据库连接已关闭")
    
    def process_item(self, item: CandidateItem, spider):
        """处理数据项并插入数据库"""
        try:
            cursor = self.connection.cursor()
            
            # 检查是否已存在
            if item.email:
                cursor.execute(
                    "SELECT id FROM jobs_candidate WHERE email = %s",
                    (item.email,)
                )
                if cursor.fetchone():
                    spider.logger.info(f"跳过重复邮箱: {item.email}")
                    return item
            
            # 插入候选人数据
            insert_sql = """
                INSERT INTO jobs_candidate (
                    name, email, phone, current_position, current_company,
                    experience_years, education, skills, resume_file, resume_content,
                    ai_parsed_data, predicted_job_tags, salary_expectation,
                    location_preference, availability, notes, status, source,
                    user_id, created_at, updated_at
                ) VALUES (
                    %(name)s, %(email)s, %(phone)s, %(current_position)s, %(current_company)s,
                    %(experience_years)s, %(education)s, %(skills)s, %(resume_file)s, %(resume_content)s,
                    %(ai_parsed_data)s, %(predicted_job_tags)s, %(salary_expectation)s,
                    %(location_preference)s, %(availability)s, %(notes)s, %(status)s, %(source)s,
                    %(user_id)s, %(created_at)s, %(updated_at)s
                )
            """
            
            data = item.to_dict()
            data['user_id'] = 1  # 默认用户ID，可根据需要调整
            
            cursor.execute(insert_sql, data)
            self.connection.commit()
            
            spider.logger.info(f"成功插入候选人: {item.name}")
            
        except Exception as e:
            spider.logger.error(f"插入数据失败: {e}")
            self.connection.rollback()
        
        finally:
            cursor.close()
        
        return item

class JSONExportPipeline:
    """JSON文件导出管道"""
    
    def __init__(self):
        self.file = None
        self.items = []
    
    def open_spider(self, spider):
        """打开输出文件"""
        filename = f"candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.file = open(filename, 'w', encoding='utf-8')
        spider.logger.info(f"JSON导出文件: {filename}")
    
    def close_spider(self, spider):
        """关闭文件并写入数据"""
        if self.file:
            json.dump(self.items, self.file, ensure_ascii=False, indent=2)
            self.file.close()
            spider.logger.info(f"JSON导出完成，共 {len(self.items)} 条记录")
    
    def process_item(self, item: CandidateItem, spider):
        """收集数据项"""
        self.items.append(item.to_dict())
        return item
```

### 3️⃣ **数据格式化器 (formatter.py)**

```python
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

class CandidateDataFormatter:
    """候选人数据格式化器"""
    
    @staticmethod
    def extract_experience_years(experience_text: str) -> Optional[int]:
        """从文本中提取工作年限"""
        if not experience_text:
            return None
        
        # 匹配各种年限表达方式
        patterns = [
            r'(\d+)\s*年',
            r'(\d+)\s*年工作经验',
            r'工作\s*(\d+)\s*年',
            r'(\d+)\s*years?',
            r'experience:\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, experience_text, re.IGNORECASE)
            if match:
                years = int(match.group(1))
                return years if 0 <= years <= 50 else None
        
        return None
    
    @staticmethod
    def parse_skills(skills_text: str) -> List[str]:
        """解析技能文本为技能列表"""
        if not skills_text:
            return []
        
        # 常见分隔符
        separators = [',', '，', ';', '；', '|', '/', '、', '\n', '\t']
        
        # 分割技能
        skills = [skills_text]
        for sep in separators:
            new_skills = []
            for skill in skills:
                new_skills.extend(skill.split(sep))
            skills = new_skills
        
        # 清理和标准化
        cleaned_skills = []
        for skill in skills:
            skill = skill.strip()
            if skill and len(skill) > 1:
                cleaned_skills.append(skill)
        
        return list(set(cleaned_skills))  # 去重
    
    @staticmethod
    def format_salary(salary_text: str) -> Optional[str]:
        """格式化薪资信息"""
        if not salary_text:
            return None
        
        # 标准化薪资格式
        salary = salary_text.strip()
        
        # 常见薪资格式映射
        salary_patterns = [
            (r'(\d+)[kK][-~](\d+)[kK]', r'\1K-\2K'),
            (r'(\d+)万[-~](\d+)万', r'\1万-\2万'),
            (r'年薪(\d+)万', r'年薪\1万'),
            (r'月薪(\d+)[kK]', r'月薪\1K'),
        ]
        
        for pattern, replacement in salary_patterns:
            salary = re.sub(pattern, replacement, salary, flags=re.IGNORECASE)
        
        return salary
    
    @staticmethod
    def generate_ai_parsed_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成AI解析数据格式"""
        
        ai_data = {
            "extraction_info": {
                "model_used": "crawler_extraction",
                "confidence": 0.8,
                "extraction_time": datetime.now().isoformat(),
                "source_type": "web_crawling"
            },
            "raw_source": {
                "url": raw_data.get('source_url'),
                "platform": raw_data.get('platform'),
                "crawl_time": datetime.now().isoformat()
            }
        }
        
        # 添加个人信息
        if any(key in raw_data for key in ['name', 'email', 'phone']):
            ai_data["personal_info"] = {
                "full_name": raw_data.get('name'),
                "contact_info": {
                    "emails": [raw_data['email']] if raw_data.get('email') else [],
                    "phones": [raw_data['phone']] if raw_data.get('phone') else []
                }
            }
        
        # 添加工作经验
        if raw_data.get('current_company') or raw_data.get('current_position'):
            ai_data["work_experience"] = [{
                "company": raw_data.get('current_company'),
                "position": raw_data.get('current_position'),
                "is_current": True
            }]
        
        # 添加技能分析
        if raw_data.get('skills'):
            ai_data["skills_analysis"] = {
                "technical_skills": raw_data['skills'],
                "extraction_method": "text_parsing"
            }
        
        return ai_data

class DataExporter:
    """数据导出器"""
    
    @staticmethod
    def export_to_sql(candidates: List[CandidateItem], filename: str) -> None:
        """导出为SQL插入语句"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("-- 候选人数据导入SQL\n")
            f.write("-- 生成时间: {}\n\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            f.write("SET NAMES utf8mb4;\n")
            f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")
            
            for candidate in candidates:
                data = candidate.to_dict()
                
                # 生成INSERT语句
                f.write("INSERT INTO jobs_candidate (\n")
                f.write("    name, email, phone, current_position, current_company,\n")
                f.write("    experience_years, education, skills, resume_content,\n")
                f.write("    ai_parsed_data, predicted_job_tags, salary_expectation,\n")
                f.write("    location_preference, availability, notes, status, source,\n")
                f.write("    user_id, created_at, updated_at\n")
                f.write(") VALUES (\n")
                
                # 格式化值
                values = []
                for key in ['name', 'email', 'phone', 'current_position', 'current_company']:
                    val = data.get(key)
                    values.append(f"'{val}'" if val else 'NULL')
                
                values.append(str(data.get('experience_years')) if data.get('experience_years') else 'NULL')
                
                for key in ['education', 'skills', 'resume_content', 'ai_parsed_data', 
                           'predicted_job_tags', 'salary_expectation', 'location_preference',
                           'availability', 'notes', 'status', 'source']:
                    val = data.get(key)
                    if val:
                        # 转义单引号
                        escaped_val = str(val).replace("'", "\\'")
                        values.append(f"'{escaped_val}'")
                    else:
                        values.append('NULL')
                
                values.append('1')  # user_id
                values.append(f"'{data['created_at'].strftime('%Y-%m-%d %H:%M:%S')}'")
                values.append(f"'{data['updated_at'].strftime('%Y-%m-%d %H:%M:%S')}'")
                
                f.write("    " + ",\n    ".join(values) + "\n")
                f.write(");\n\n")
            
            f.write("SET FOREIGN_KEY_CHECKS = 1;\n")
    
    @staticmethod
    def export_to_api_format(candidates: List[CandidateItem]) -> List[Dict[str, Any]]:
        """导出为API接口格式"""
        
        api_data = []
        for candidate in candidates:
            data = candidate.to_dict()
            
            # API格式转换
            api_item = {
                "candidate_info": {
                    "basic": {
                        "name": data['name'],
                        "email": data['email'],
                        "phone": data['phone']
                    },
                    "career": {
                        "current_position": data['current_position'],
                        "current_company": data['current_company'],
                        "experience_years": data['experience_years'],
                        "education": data['education']
                    },
                    "skills": json.loads(data['skills']) if data['skills'] else [],
                    "preferences": {
                        "salary_expectation": data['salary_expectation'],
                        "location_preference": data['location_preference'],
                        "availability": data['availability']
                    }
                },
                "metadata": {
                    "source": data['source'],
                    "status": data['status'],
                    "notes": data['notes'],
                    "created_at": data['created_at'].isoformat(),
                    "updated_at": data['updated_at'].isoformat()
                },
                "ai_data": json.loads(data['ai_parsed_data']) if data['ai_parsed_data'] else {}
            }
            
            api_data.append(api_item)
        
        return api_data
```

---

## 🔌 **API接口设计**

### 1️⃣ **RESTful API端点**

```python
# api/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import CandidateData
from .serializers import CandidateSerializer

class CandidateDataViewSet(viewsets.ModelViewSet):
    """候选人数据API视图集"""
    
    queryset = CandidateData.objects.all()
    serializer_class = CandidateSerializer
    
    @action(detail=False, methods=['post'])
    def batch_import(self, request):
        """批量导入候选人数据"""
        data = request.data.get('candidates', [])
        
        results = {
            'total': len(data),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for item in data:
            try:
                serializer = self.get_serializer(data=item)
                if serializer.is_valid():
                    serializer.save()
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'data': item,
                        'errors': serializer.errors
                    })
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'data': item,
                    'error': str(e)
                })
        
        return Response(results, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def export_format(self, request):
        """获取数据导出格式说明"""
        format_info = {
            'required_fields': ['name'],
            'optional_fields': [
                'email', 'phone', 'current_position', 'current_company',
                'experience_years', 'education', 'skills', 'salary_expectation',
                'location_preference', 'availability', 'notes', 'source'
            ],
            'data_formats': {
                'skills': 'JSON数组或逗号分隔字符串',
                'experience_years': '整数',
                'salary_expectation': '字符串描述',
                'email': '有效邮箱格式',
                'phone': '11位手机号'
            },
            'example': {
                'name': '张三',
                'email': 'zhangsan@example.com',
                'phone': '13800138000',
                'current_position': 'Python工程师',
                'current_company': '字节跳动',
                'experience_years': 5,
                'skills': ['Python', 'Django', 'MySQL'],
                'salary_expectation': '年薪50-60万',
                'location_preference': '北京',
                'availability': '随时到岗',
                'source': '网络爬虫'
            }
        }
        
        return Response(format_info)
```

### 2️⃣ **数据序列化器**

```python
# api/serializers.py
from rest_framework import serializers
from .models import CandidateData
import json

class CandidateSerializer(serializers.ModelSerializer):
    """候选人数据序列化器"""
    
    skills_list = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="技能列表"
    )
    
    class Meta:
        model = CandidateData
        fields = '__all__'
        extra_kwargs = {
            'name': {'required': True, 'help_text': '候选人姓名'},
            'email': {'required': False, 'help_text': '邮箱地址'},
            'phone': {'required': False, 'help_text': '手机号码'},
            'skills': {'read_only': True},
        }
    
    def validate_email(self, value):
        """验证邮箱格式"""
        if value:
            import re
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, value):
                raise serializers.ValidationError("邮箱格式不正确")
        return value
    
    def validate_phone(self, value):
        """验证手机号格式"""
        if value:
            import re
            phone_clean = re.sub(r'[^\d]', '', value)
            if not (len(phone_clean) == 11 and phone_clean.startswith('1')):
                raise serializers.ValidationError("手机号格式不正确")
            return phone_clean
        return value
    
    def validate_experience_years(self, value):
        """验证工作年限"""
        if value is not None:
            if not isinstance(value, int) or value < 0 or value > 50:
                raise serializers.ValidationError("工作年限必须是0-50之间的整数")
        return value
    
    def create(self, validated_data):
        """创建候选人记录"""
        skills_list = validated_data.pop('skills_list', [])
        
        # 处理技能列表
        if skills_list:
            validated_data['skills'] = json.dumps(skills_list, ensure_ascii=False)
        
        return super().create(validated_data)
    
    def to_representation(self, instance):
        """自定义输出格式"""
        data = super().to_representation(instance)
        
        # 解析技能JSON
        if data.get('skills'):
            try:
                data['skills_list'] = json.loads(data['skills'])
            except json.JSONDecodeError:
                data['skills_list'] = []
        
        # 解析AI数据
        if data.get('ai_parsed_data'):
            try:
                data['ai_parsed_data'] = json.loads(data['ai_parsed_data'])
            except json.JSONDecodeError:
                data['ai_parsed_data'] = {}
        
        return data
```

---

## 📚 **使用文档**

### 1️⃣ **快速开始**

```bash
# 1. 创建项目
mkdir candidate_crawler
cd candidate_crawler

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install scrapy django djangorestframework mysql-connector-python

# 4. 创建Django项目
django-admin startproject api_server
cd api_server
python manage.py startapp candidates

# 5. 创建Scrapy项目
cd ..
scrapy startproject crawler
```

### 2️⃣ **配置示例**

```python
# settings.py (Scrapy)
ITEM_PIPELINES = {
    'crawler.pipelines.DataValidationPipeline': 100,
    'crawler.pipelines.DataNormalizationPipeline': 200,
    'crawler.pipelines.JSONExportPipeline': 300,
    'crawler.pipelines.DatabaseExportPipeline': 400,
}

MYSQL_SETTINGS = {
    'host': 'localhost',
    'port': 3306,
    'user': 'headhunter_user',
    'password': 'your_password',
    'database': 'headhunter_db',
    'charset': 'utf8mb4'
}

# Django settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'headhunter_db',
        'USER': 'headhunter_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50
}
```

### 3️⃣ **API调用示例**

```python
import requests
import json

# 批量导入候选人数据
candidates_data = [
    {
        "name": "张三",
        "email": "zhangsan@example.com",
        "phone": "13800138000",
        "current_position": "Python工程师",
        "current_company": "字节跳动",
        "experience_years": 5,
        "skills_list": ["Python", "Django", "MySQL", "Redis"],
        "salary_expectation": "年薪50-60万",
        "location_preference": "北京",
        "source": "网络爬虫"
    }
]

response = requests.post(
    'http://localhost:8000/api/candidates/batch_import/',
    json={'candidates': candidates_data},
    headers={'Content-Type': 'application/json'}
)

print(response.json())
```

---

## 🚀 **项目推荐工具和框架**

### 📦 **依赖包推荐**

```txt
# requirements.txt
# 爬虫框架
scrapy==2.11.0
scrapy-splash==0.8.0

# Web框架  
django==4.2.7
djangorestframework==3.14.0

# 数据库
mysql-connector-python==8.2.0
PyMySQL==1.1.0

# 数据处理
pandas==2.1.3
numpy==1.24.3

# 文本处理
jieba==0.42.1
python-docx==1.1.0
PyPDF2==3.0.1

# 工具库
requests==2.31.0
lxml==4.9.3
beautifulsoup4==4.12.2
fake-useragent==1.4.0

# 异步支持
aiohttp==3.9.1
asyncio==3.4.3

# 日志和监控
loguru==0.7.2
```

---

## 📊 **字段映射对照表**

| 目标字段 | 数据类型 | 说明 | 示例 |
|---------|---------|------|------|
| `name` | varchar(100) | 候选人姓名，必填 | "张三" |
| `email` | varchar(254) | 邮箱地址，用于去重 | "zhangsan@example.com" |
| `phone` | varchar(20) | 手机号码，11位数字 | "13800138000" |
| `current_position` | varchar(200) | 当前职位 | "高级Python工程师" |
| `current_company` | varchar(200) | 当前公司 | "字节跳动" |
| `experience_years` | int(11) | 工作年限，整数 | 5 |
| `education` | varchar(200) | 最高学历 | "本科" |
| `skills` | longtext | 技能标签，JSON数组格式 | '["Python", "Django"]' |
| `predicted_job_tags` | longtext | AI预测职位标签，JSON | '["后端工程师", "全栈工程师"]' |
| `resume_content` | longtext | 简历文本内容 | "个人简历内容..." |
| `ai_parsed_data` | longtext | AI解析结构化数据，JSON | '{"personal_info": {...}}' |
| `salary_expectation` | varchar(100) | 期望薪资 | "年薪50-60万" |
| `location_preference` | varchar(200) | 期望工作地点 | "北京" |
| `availability` | varchar(50) | 可入职时间 | "随时到岗" |
| `notes` | longtext | 备注信息 | "从XX网站爬取" |
| `status` | varchar(20) | 状态 | "active" |
| `source` | varchar(100) | 数据来源渠道 | "网络爬虫" |
| `user_id` | bigint(20) | 所属用户ID | 1 |
| `created_at` | datetime(6) | 创建时间 | "2024-01-15 10:30:00" |
| `updated_at` | datetime(6) | 更新时间 | "2024-01-15 10:30:00" |

---

## 🎯 **项目实施建议**

### 1️⃣ **开发阶段规划**

1. **阶段1: 基础框架搭建**
   - 创建Scrapy和Django项目
   - 配置数据库连接
   - 实现基础数据模型

2. **阶段2: 爬虫开发**
   - 编写目标网站爬虫
   - 实现数据提取逻辑
   - 添加数据验证和清洗

3. **阶段3: API接口开发**
   - 实现RESTful API
   - 添加批量导入功能
   - 完善数据序列化

4. **阶段4: 数据处理优化**
   - 优化数据格式化逻辑
   - 添加错误处理机制
   - 实现数据导出功能

### 2️⃣ **技术选型建议**

- **爬虫框架**: Scrapy (功能完善，扩展性好)
- **Web框架**: Django + DRF (快速开发，API友好)
- **数据库**: MySQL (与目标系统兼容)
- **数据处理**: Pandas (数据分析和清洗)
- **任务队列**: Celery (可选，处理大批量数据)

### 3️⃣ **部署建议**

- **开发环境**: 使用虚拟环境隔离依赖
- **测试环境**: 小批量数据测试
- **生产环境**: Docker容器化部署
- **监控**: 添加日志和性能监控

这个文档提供了完整的数据结构、代码框架和实施指南，可以作为爬虫项目开发的技术参考文档！ 🚀