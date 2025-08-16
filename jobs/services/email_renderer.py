import re
from typing import Dict, Any, Optional
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from jobs.models import Candidate, Contact, Job


class EmailRenderer:
    """邮件内容渲染器，用于处理模板变量替换"""
    
    # 支持的变量模式
    VARIABLE_PATTERN = r'\{\{([^}]+)\}\}'
    
    @classmethod
    def render_template(cls, template_content: str, context: Dict[str, Any]) -> str:
        """
        渲染邮件模板内容
        
        Args:
            template_content: 模板内容（支持HTML）
            context: 上下文变量字典
            
        Returns:
            渲染后的内容
        """
        if not template_content:
            return ""
        
        # 查找所有变量占位符
        def replace_variable(match):
            variable_name = match.group(1).strip()
            value = cls._get_variable_value(variable_name, context)
            return str(value) if value is not None else ""
        
        # 执行变量替换
        rendered_content = re.sub(cls.VARIABLE_PATTERN, replace_variable, template_content)
        
        return rendered_content
    
    @classmethod
    def _get_variable_value(cls, variable_name: str, context: Dict[str, Any]) -> Optional[str]:
        """
        获取变量值
        
        Args:
            variable_name: 变量名（支持点号访问）
            context: 上下文字典
            
        Returns:
            变量值
        """
        # 处理点号访问（如 candidate.name）
        parts = variable_name.split('.')
        current = context
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
            
            if current is None:
                return None
        
        # 处理特殊类型的值
        if callable(current):
            current = current()
        
        return str(current) if current is not None else ""
    
    @classmethod
    def create_candidate_context(cls, candidate: Candidate, user: User = None, job: Job = None) -> Dict[str, Any]:
        """
        为候选人创建上下文变量
        
        Args:
            candidate: 候选人对象
            user: 当前用户（可选）
            job: 相关职位（可选）
            
        Returns:
            上下文字典
        """
        context = {
            'candidate': {
                'name': candidate.name,
                'salutation': cls._get_salutation(candidate),
                'emails': candidate.emails,
                'primary_email': candidate.emails[0] if candidate.emails else '',
                'location': candidate.location or '',
                'education_level': candidate.get_education_level_display(),
                'gender': candidate.get_gender_display(),
                'predicted_position': candidate.predicted_position or '',
                'keywords': ', '.join(candidate.keywords) if candidate.keywords else '',
                'homepage': candidate.homepage or '',
                'github_profile': candidate.github_profile or '',
                'linkedin_profile': candidate.linkedin_profile or '',
            },
            'user': {
                'name': user.get_full_name() if user else '',
                'username': user.username if user else '',
                'signature': cls._get_user_signature(user),
            } if user else {},
            'job': {
                'title': job.title if job else '',
                'company_name': job.company.name if job else '',
                'salary_range': job.salary_range if job else '',
                'locations': ', '.join(job.locations) if job and job.locations else '',
                'department': job.department if job else '',
            } if job else {},
        }
        
        return context
    
    @classmethod
    def create_contact_context(cls, contact: Contact, user: User = None, job: Job = None) -> Dict[str, Any]:
        """
        为联系人创建上下文变量
        
        Args:
            contact: 联系人对象
            user: 当前用户（可选）
            job: 相关职位（可选）
            
        Returns:
            上下文字典
        """
        context = {
            'contact': {
                'name': contact.name,
                'salutation': cls._get_contact_salutation(contact),
                'email': contact.email,
                'primary_email': contact.email,
                'phone': contact.phone or '',
                'position': contact.position or '',
                'company': contact.company or '',
                'department': contact.department or '',
                'gender': contact.get_gender_display(),
                'notes': contact.notes or '',
            },
            # 为了保持兼容性，也提供candidate命名空间，指向联系人数据
            'candidate': {
                'name': contact.name,
                'salutation': cls._get_contact_salutation(contact),
                'emails': [contact.email],
                'primary_email': contact.email,
                'location': '',  # 联系人没有位置字段
                'education_level': '',  # 联系人没有学历字段
                'gender': contact.get_gender_display(),
                'predicted_position': contact.position or '',
                'keywords': '',  # 联系人没有关键词字段
                'homepage': '',  # 联系人没有主页字段
                'github_profile': '',  # 联系人没有GitHub字段
                'linkedin_profile': '',  # 联系人没有LinkedIn字段
            },
            'user': {
                'name': user.get_full_name() if user else '',
                'username': user.username if user else '',
                'signature': cls._get_user_signature(user),
            } if user else {},
            'job': {
                'title': job.title if job else '',
                'company_name': job.company.name if job else '',
                'salary_range': job.salary_range if job else '',
                'locations': ', '.join(job.locations) if job and job.locations else '',
                'department': job.department if job else '',
            } if job else {},
        }
        
        return context
    
    @classmethod
    def _get_salutation(cls, candidate: Candidate) -> str:
        """获取候选人的称呼"""
        if candidate.gender == '男':
            return f"{candidate.name}先生"
        elif candidate.gender == '女':
            return f"{candidate.name}女士"
        else:
            return candidate.name
    
    @classmethod
    def _get_contact_salutation(cls, contact: Contact) -> str:
        """获取联系人的称呼"""
        if contact.gender == Contact.Gender.MALE:
            return f"{contact.name}先生"
        elif contact.gender == Contact.Gender.FEMALE:
            return f"{contact.name}女士"
        else:
            return contact.name
    
    @classmethod
    def _get_user_signature(cls, user) -> str:
        """安全地获取用户签名"""
        if not user:
            return ''
        
        try:
            default_account = user.email_accounts.filter(is_default=True).first()
            return default_account.signature if default_account else ''
        except Exception:
            return ''
    
    @classmethod
    def render_batch_emails(cls, template_content: str, template_subject: str, 
                          recipients: list = None, candidates: list = None, user: User = None, job: Job = None) -> list:
        """
        批量渲染邮件内容
        
        Args:
            template_content: 模板内容
            template_subject: 模板主题
            recipients: 收件人列表（候选人或联系人混合）
            candidates: 候选人列表（为了向后兼容）
            user: 当前用户
            job: 相关职位（可选）
            
        Returns:
            渲染结果列表，每个元素包含 recipient, subject, content
        """
        results = []
        
        # 确定收件人列表（优先使用recipients参数）
        recipient_list = recipients if recipients is not None else (candidates or [])
        
        for recipient in recipient_list:
            # 根据收件人类型创建上下文
            if isinstance(recipient, Contact):
                context = cls.create_contact_context(recipient, user, job)
                recipient_type = 'contact'
            else:
                # 默认当作候选人处理（向后兼容）
                context = cls.create_candidate_context(recipient, user, job)
                recipient_type = 'candidate'
            
            # 渲染主题和内容
            subject = cls.render_template(template_subject, context)
            content = cls.render_template(template_content, context)
            
            results.append({
                'recipient': recipient,
                'recipient_type': recipient_type,
                'subject': subject,
                'content': content,
                'context': context,
                # 为了向后兼容，保留candidate字段
                'candidate': recipient
            })
        
        return results
    
    @classmethod
    def validate_template(cls, template_content: str) -> Dict[str, Any]:
        """
        验证模板中的变量
        
        Args:
            template_content: 模板内容
            
        Returns:
            验证结果，包含使用的变量列表和错误信息
        """
        variables = set()
        errors = []
        
        # 提取所有变量
        matches = re.findall(cls.VARIABLE_PATTERN, template_content)
        for match in matches:
            variable_name = match.strip()
            variables.add(variable_name)
        
        # 检查变量是否有效
        valid_variables = {
            # 候选人变量
            'candidate.name', 'candidate.salutation', 'candidate.emails', 'candidate.primary_email',
            'candidate.location', 'candidate.education_level', 'candidate.gender',
            'candidate.predicted_position', 'candidate.keywords', 'candidate.homepage',
            'candidate.github_profile', 'candidate.linkedin_profile',
            # 联系人变量
            'contact.name', 'contact.salutation', 'contact.email', 'contact.primary_email',
            'contact.phone', 'contact.position', 'contact.company', 'contact.department',
            'contact.gender', 'contact.notes',
            # 用户变量
            'user.name', 'user.username', 'user.signature',
            # 职位变量
            'job.title', 'job.company_name', 'job.salary_range', 'job.locations', 'job.department'
        }
        
        for var in variables:
            if var not in valid_variables:
                errors.append(f"未知变量: {var}")
        
        return {
            'variables': list(variables),
            'errors': errors,
            'is_valid': len(errors) == 0
        } 