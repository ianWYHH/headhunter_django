# 堡塔面板Django项目正确配置指南

## 🎯 问题分析
- **命令行启动**: `source venv/bin/activate && python manage.py runserver` → AI解析正常 ✅
- **堡塔面板启动**: 配置界面启动 → AI解析失败 ❌

**根本原因**: 堡塔面板启动时虚拟环境、工作目录或环境变量配置不正确

---

## 🛠️ 堡塔面板正确配置

### 配置项1: 项目路径
```
项目路径: /www/wwwroot/your_project_name/
```

### 配置项2: 启动文件  
```
启动文件: manage.py
```

### 配置项3: 框架
```
框架: Django
```

### 配置项4: Python解释器路径 ⭐ 重要
```
Python路径: /www/wwwroot/your_project_name/venv/bin/python
```
**注意**: 必须使用虚拟环境中的Python，不要使用系统Python

### 配置项5: 启动参数
```
参数: runserver 0.0.0.0:8000
```

### 配置项6: 工作目录 ⭐ 重要
```
工作目录: /www/wwwroot/your_project_name/
```

### 配置项7: 环境变量 (如果需要)
```
DJANGO_SETTINGS_MODULE=headhunter_django.settings
```

---

## 🔧 具体操作步骤

### 步骤1: 检查虚拟环境
在服务器上确认虚拟环境路径：
```bash
ls -la /www/wwwroot/your_project_name/venv/bin/python
```

### 步骤2: 在堡塔面板中配置
1. 进入 **堡塔面板** → **网站** → **Python项目**
2. 找到您的Django项目，点击 **设置**
3. 按照上述配置项逐项设置

### 步骤3: 特别注意Python路径
确保Python路径设置为：
```
/www/wwwroot/your_project_name/venv/bin/python
```
**不是**：
- `/usr/bin/python3`
- `/usr/local/bin/python`
- 系统默认Python路径

### 步骤4: 验证配置
重启项目后，在堡塔面板的**日志**中查看启动信息，应该看到类似：
```
Starting development server at http://0.0.0.0:8000/
```

---

## 🚀 测试验证

### 方法1: 检查Python路径
在Django项目中添加临时视图来验证：
```python
# 在views.py中临时添加
def debug_env(request):
    import sys
    return JsonResponse({
        'python_path': sys.executable,
        'python_version': sys.version,
        'working_directory': os.getcwd(),
        'virtual_env': os.environ.get('VIRTUAL_ENV', 'Not set')
    })
```

### 方法2: 检查包路径
```python
def debug_packages(request):
    try:
        import openai
        import django
        return JsonResponse({
            'django_path': django.__file__,
            'openai_path': openai.__file__,
        })
    except ImportError as e:
        return JsonResponse({'error': str(e)})
```

---

## 🔍 常见问题排查

### 问题1: Python路径错误
**症状**: 项目能启动但AI功能异常
**解决**: 确保使用虚拟环境中的Python

### 问题2: 工作目录错误  
**症状**: 找不到模板或静态文件
**解决**: 设置正确的工作目录为项目根目录

### 问题3: 包依赖缺失
**症状**: 模块导入错误
**解决**: 
```bash
# 在虚拟环境中重新安装依赖
cd /www/wwwroot/your_project_name/
source venv/bin/activate
pip install -r requirements.txt
```

### 问题4: 权限问题
**症状**: 无法访问文件或网络
**解决**:
```bash
# 设置正确的文件权限
chown -R www:www /www/wwwroot/your_project_name/
chmod -R 755 /www/wwwroot/your_project_name/
```

---

## 🎯 核心要点

1. **必须使用虚拟环境中的Python** (`venv/bin/python`)
2. **工作目录必须是项目根目录**
3. **启动参数使用相对路径** (`manage.py`)
4. **确保依赖包完整安装**

---

## 📋 配置检查清单

配置完成后，请逐项检查：

- [ ] Python路径指向虚拟环境 (`/path/to/venv/bin/python`)
- [ ] 工作目录设置为项目根目录
- [ ] 启动文件设置为 `manage.py`
- [ ] 启动参数设置为 `runserver 0.0.0.0:8000`
- [ ] 项目能够正常启动
- [ ] Web界面可以正常访问
- [ ] AI解析功能正常工作
- [ ] 静态文件正常加载

---

## 🚨 如果仍有问题

1. **查看堡塔面板日志**：
   - 进入项目设置 → 日志
   - 查看启动和运行时错误

2. **对比环境差异**：
   ```bash
   # 命令行环境
   source venv/bin/activate
   python -c "import sys; print('Python:', sys.executable)"
   python -c "import os; print('CWD:', os.getcwd())"
   
   # 然后与堡塔面板启动的环境对比
   ```

3. **重新创建虚拟环境**（最后选项）：
   ```bash
   cd /www/wwwroot/your_project_name/
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

按照以上配置，AI解析功能应该能在堡塔面板启动的环境中正常工作！