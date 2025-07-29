from django.contrib import admin
from django.urls import path, include
from jobs import views as job_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # 1. 用户认证URL
    # 我们将登录、登出、注册页面放在网站的根路径下
    path('login/', job_views.login_view, name='login'),
    path('logout/', job_views.logout_view, name='logout'),
    path('register/', job_views.register_view, name='register'),

    # 2. 主应用URL
    # 所有核心功能（职位、候选人管理等）都包含在 jobs 应用中
    path('', include('jobs.urls')),
]
