from django.contrib.auth.models import User
from ..models import ActionLog

def create_log(user: User, action_description: str, related_object=None):
    """
    创建一个操作日志的统一服务函数。

    :param user: 执行操作的 User 实例
    :param action_description: 操作的文字描述
    :param related_object: (可选) 操作关联的Django模型实例
    """
    related_str = ""
    if related_object:
        # 尝试获取对象的名称或标题，如果失败则使用默认的字符串表示
        name = getattr(related_object, 'name', getattr(related_object, 'title', str(related_object)))
        related_str = f"{related_object.__class__.__name__}: {name}"

    ActionLog.objects.create(
        user=user,
        action_description=action_description,
        related_object_str=related_str
    )
