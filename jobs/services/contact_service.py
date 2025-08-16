"""
联系人管理服务
"""
import logging
from typing import List, Dict, Optional, Any
from django.db import transaction, models
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone

from ..models import Contact, ContactGroup, ContactOperationLog, Company

logger = logging.getLogger(__name__)


class ContactOperationLogger:
    """联系人操作日志记录器"""
    
    @staticmethod
    def log_operation(
        operation_type: str,
        operator: User,
        contact: Contact = None,
        contact_group: ContactGroup = None,
        description: str = "",
        old_values: Dict = None,
        new_values: Dict = None,
        request=None
    ):
        """记录联系人操作日志"""
        try:
            # 获取请求相关信息
            ip_address = None
            user_agent = "系统操作"  # 默认值
            
            if request:
                ip_address = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '未知浏览器')[:500]
            
            ContactOperationLog.objects.create(
                operation_type=operation_type,
                operator=operator,
                contact=contact,
                contact_group=contact_group,
                operation_description=description,
                old_values=old_values or {},
                new_values=new_values or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(f"记录操作日志: {operator.username} {operation_type} {contact or contact_group}")
            
        except Exception as e:
            logger.error(f"记录操作日志失败: {e}")
    
    @staticmethod
    def get_model_changes(old_instance, new_instance):
        """获取模型变更信息"""
        old_values = {}
        new_values = {}
        
        if old_instance:
            for field in old_instance._meta.fields:
                if not field.name.endswith('_at'):  # 排除时间戳字段
                    old_values[field.name] = str(getattr(old_instance, field.name))
        
        if new_instance:
            for field in new_instance._meta.fields:
                if not field.name.endswith('_at'):  # 排除时间戳字段
                    new_values[field.name] = str(getattr(new_instance, field.name))
        
        return old_values, new_values


class ContactService:
    """联系人服务类"""
    
    @staticmethod
    def search_contacts(
        search_query: str = "",
        company: str = "",
        position: str = "",
        department: str = "",
        contact_group: ContactGroup = None,
        is_active: Optional[bool] = None
    ) -> models.QuerySet:
        """
        搜索联系人
        
        Args:
            search_query: 搜索关键词（姓名、邮箱、电话、公司名称）
            company: 公司名称关键词
            position: 职位关键词
            department: 部门关键词
            contact_group: 联系人分组
            is_active: 是否有效
            
        Returns:
            联系人查询集
        """
        queryset = Contact.objects.prefetch_related('contact_groups')
        
        # 关键词搜索
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(company__icontains=search_query)
            )
        
        # 公司筛选
        if company:
            queryset = queryset.filter(company__icontains=company)
        
        # 职位筛选
        if position:
            queryset = queryset.filter(position__icontains=position)
        
        # 部门筛选
        if department:
            queryset = queryset.filter(department__icontains=department)
        
        # 分组筛选
        if contact_group:
            queryset = queryset.filter(contact_groups=contact_group)
        
        # 状态筛选
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        return queryset.distinct().order_by('company', 'name')
    
    @staticmethod
    @transaction.atomic
    def create_contact(contact_data: Dict, operator: User, request=None) -> Contact:
        """
        创建联系人
        
        Args:
            contact_data: 联系人数据
            operator: 操作者
            request: HTTP请求对象
            
        Returns:
            创建的联系人实例
        """
        # 准备联系人数据
        contact_data = contact_data.copy()  # 创建副本，避免修改原数据
        
        contact_data['created_by'] = operator
        contact_data['updated_by'] = operator
        
        contact = Contact.objects.create(**contact_data)
        
        # 记录操作日志
        ContactOperationLogger.log_operation(
            operation_type=ContactOperationLog.OperationType.CREATE,
            operator=operator,
            contact=contact,
            description=f"创建联系人: {contact.name} ({contact.company})",
            new_values={'name': contact.name, 'email': contact.email, 'company': contact.company},
            request=request
        )
        
        logger.info(f"创建联系人成功: {contact.name} ({contact.company})")
        return contact
    
    @staticmethod
    @transaction.atomic
    def update_contact(contact: Contact, update_data: Dict, operator: User, request=None) -> Contact:
        """
        更新联系人
        
        Args:
            contact: 联系人实例
            update_data: 更新数据
            operator: 操作者
            request: HTTP请求对象
            
        Returns:
            更新后的联系人实例
        """
        # 记录变更前的值
        old_values, _ = ContactOperationLogger.get_model_changes(contact, None)
        
        # 准备更新数据
        update_data = update_data.copy()  # 创建副本，避免修改原数据
        
        # 更新联系人
        update_data['updated_by'] = operator
        for key, value in update_data.items():
            setattr(contact, key, value)
        
        contact.save()
        
        # 记录变更后的值
        _, new_values = ContactOperationLogger.get_model_changes(None, contact)
        
        # 记录操作日志
        ContactOperationLogger.log_operation(
            operation_type=ContactOperationLog.OperationType.UPDATE,
            operator=operator,
            contact=contact,
            description=f"更新联系人: {contact.name} ({contact.company})",
            old_values=old_values,
            new_values=new_values,
            request=request
        )
        
        logger.info(f"更新联系人成功: {contact.name} ({contact.company})")
        return contact
    
    @staticmethod
    @transaction.atomic
    def delete_contact(contact: Contact, operator: User, request=None):
        """
        删除联系人（软删除）
        
        Args:
            contact: 联系人实例
            operator: 操作者
            request: HTTP请求对象
        """
        old_values, _ = ContactOperationLogger.get_model_changes(contact, None)
        
        contact_name = contact.name
        company_name = contact.company
        
        # 软删除
        contact.is_active = False
        contact.updated_by = operator
        contact.save()
        
        # 记录操作日志
        ContactOperationLogger.log_operation(
            operation_type=ContactOperationLog.OperationType.DELETE,
            operator=operator,
            contact=contact,
            description=f"删除联系人: {contact_name} ({company_name})",
            old_values=old_values,
            request=request
        )
        
        logger.info(f"删除联系人成功: {contact_name} ({company_name})")
    
    @staticmethod
    def get_contacts_by_groups(contact_groups: List[ContactGroup]) -> List[Contact]:
        """
        根据分组获取联系人列表
        
        Args:
            contact_groups: 联系人分组列表
            
        Returns:
            联系人列表
        """
        if not contact_groups:
            return []
        
        contacts = Contact.objects.filter(
            contact_groups__in=contact_groups,
            is_active=True
        ).distinct()
        
        return list(contacts)
    
    @staticmethod
    def get_contact_statistics() -> Dict[str, Any]:
        """获取联系人统计信息"""
        total_contacts = Contact.objects.filter(is_active=True).count()
        total_companies = Contact.objects.filter(is_active=True).values('company').distinct().count()
        total_groups = ContactGroup.objects.count()
        
        # 按公司统计
        company_stats = Contact.objects.filter(is_active=True).values(
            'company'
        ).annotate(
            contact_count=models.Count('id')
        ).order_by('-contact_count')[:10]
        
        # 按分组统计
        group_stats = ContactGroup.objects.annotate(
            contact_count=models.Count('contacts', filter=models.Q(contacts__is_active=True))
        ).order_by('-contact_count')[:10]
        
        return {
            'total_contacts': total_contacts,
            'total_companies': total_companies,
            'total_groups': total_groups,
            'top_companies': list(company_stats),
            'top_groups': list(group_stats),
        }


class ContactGroupService:
    """联系人分组服务类"""
    
    @staticmethod
    @transaction.atomic
    def create_group(group_data: Dict, operator: User, request=None) -> ContactGroup:
        """创建联系人分组"""
        group_data['user'] = operator
        
        group = ContactGroup.objects.create(**group_data)
        
        # 记录操作日志
        ContactOperationLogger.log_operation(
            operation_type=ContactOperationLog.OperationType.CREATE,
            operator=operator,
            contact_group=group,
            description=f"创建联系人分组: {group.name}",
            new_values={'name': group.name, 'description': group.description},
            request=request
        )
        
        logger.info(f"创建联系人分组成功: {group.name}")
        return group
    
    @staticmethod
    @transaction.atomic
    def update_group(group: ContactGroup, update_data: Dict, operator: User, request=None) -> ContactGroup:
        """更新联系人分组"""
        old_values, _ = ContactOperationLogger.get_model_changes(group, None)
        
        update_data['updated_by'] = operator
        for key, value in update_data.items():
            setattr(group, key, value)
        
        group.save()
        
        _, new_values = ContactOperationLogger.get_model_changes(None, group)
        
        # 记录操作日志
        ContactOperationLogger.log_operation(
            operation_type=ContactOperationLog.OperationType.UPDATE,
            operator=operator,
            contact_group=group,
            description=f"更新联系人分组: {group.name}",
            old_values=old_values,
            new_values=new_values,
            request=request
        )
        
        logger.info(f"更新联系人分组成功: {group.name}")
        return group
    
    @staticmethod
    @transaction.atomic
    def add_contacts_to_group(group: ContactGroup, contacts: List[Contact], operator: User, request=None):
        """向分组添加联系人"""
        added_contacts = []
        
        for contact in contacts:
            if not group.contacts.filter(id=contact.id).exists():
                group.contacts.add(contact)
                added_contacts.append(contact)
        
        if added_contacts:
            contact_names = [c.name for c in added_contacts]
            
            # 记录操作日志
            ContactOperationLogger.log_operation(
                operation_type=ContactOperationLog.OperationType.GROUP_ADD,
                operator=operator,
                contact_group=group,
                description=f"向分组 {group.name} 添加联系人: {', '.join(contact_names)}",
                new_values={'added_contacts': contact_names},
                request=request
            )
            
            logger.info(f"向分组 {group.name} 添加了 {len(added_contacts)} 个联系人")
    
    @staticmethod
    @transaction.atomic
    def remove_contacts_from_group(group: ContactGroup, contacts: List[Contact], operator: User, request=None):
        """从分组移除联系人"""
        removed_contacts = []
        
        for contact in contacts:
            if group.contacts.filter(id=contact.id).exists():
                group.contacts.remove(contact)
                removed_contacts.append(contact)
        
        if removed_contacts:
            contact_names = [c.name for c in removed_contacts]
            
            # 记录操作日志
            ContactOperationLogger.log_operation(
                operation_type=ContactOperationLog.OperationType.GROUP_REMOVE,
                operator=operator,
                contact_group=group,
                description=f"从分组 {group.name} 移除联系人: {', '.join(contact_names)}",
                old_values={'removed_contacts': contact_names},
                request=request
            )
            
            logger.info(f"从分组 {group.name} 移除了 {len(removed_contacts)} 个联系人")