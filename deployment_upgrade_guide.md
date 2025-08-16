# Django项目升级部署指南

## 📋 升级概述
本次升级主要包含：
- 🚀 异步批量邮件发送功能
- 🛠️ AI解析功能优化
- 🎨 界面改进和错误修复
- 📧 邮件发送稳定性提升

---

## 🗂️ 需要更新的文件清单

### 🔧 后端核心文件
```
jobs/services/multi_email_service.py        ⭐ 重要：新增异步批量发送
jobs/services/mailing_service.py           ⭐ 重要：邮件处理优化
jobs/views.py                               ⭐ 重要：新增API端点
jobs/urls.py                                ⭐ 重要：新增路由
jobs/forms.py                               📝 表单优化
jobs/services/simple_parsing_service.py     🤖 AI解析改进
jobs/services/template_service.py           📧 模板服务优化
jobs/services/ai_service_v2.py             🤖 AI服务修复
```

### 🎨 前端模板文件
```
jobs/templates/jobs/unified_email_send.html              ⭐ 重要：统一邮件发送页面
jobs/templates/jobs/template_form.html                   📝 模板表单修复
jobs/templates/jobs/base.html                           🔧 基础模板改进
jobs/templates/jobs/partials/text_preview_and_parse_form.html  🔧 解析表单
jobs/templates/jobs/partials/job_content_preview.html    🔧 职位预览
jobs/templates/jobs/partials/candidate_content_preview.html   🔧 候选人预览
```

### ⚙️ 配置文件
```
.env                                        ⭐ 重要：邮件SSL配置修改
```

---

## 🚀 堡塔面板部署步骤

### 第一步：备份现有文件
1. 在堡塔面板进入 **文件管理**
2. 进入项目目录：`/www/wwwroot/your_project_name/`
3. **创建备份**：
   - 右键项目文件夹 → 压缩 → 命名为 `backup_before_upgrade_$(date +%Y%m%d_%H%M).tar.gz`

### 第二步：上传新文件
1. **方式一：FTP上传**
   - 使用FTP工具将修改的文件上传到对应目录
   
2. **方式二：堡塔文件管理**
   - 在堡塔面板中逐个上传修改的文件
   - 注意保持目录结构不变

### 第三步：修改配置文件
1. 编辑 `.env` 文件：
   ```bash
   # 在堡塔面板文件管理中找到 .env 文件，点击编辑
   # 修改以下行：
   EMAIL_USE_SSL=False
   
   # 确保其他邮件配置正确：
   EMAIL_HOST=your_smtp_host
   EMAIL_PORT=587
   EMAIL_HOST_USER=your_email
   EMAIL_HOST_PASSWORD=your_password
   EMAIL_USE_TLS=True
   ```

### 第四步：检查依赖包（如需要）
1. 进入 **终端** 或 **SSH**
2. 激活虚拟环境：
   ```bash
   cd /www/wwwroot/your_project_name/
   source venv/bin/activate
   ```
3. 检查依赖：
   ```bash
   pip install -r requirements.txt
   ```

### 第五步：数据库迁移（如需要）
```bash
# 在虚拟环境中执行
python manage.py makemigrations
python manage.py migrate
```

### 第六步：收集静态文件
```bash
python manage.py collectstatic --noinput
```

### 第七步：重启服务
1. 在堡塔面板中找到 **Python项目管理**
2. 找到您的Django项目
3. 点击 **重启** 按钮

### 第八步：重启Nginx（可选）
1. 在堡塔面板中进入 **软件商店**
2. 找到 **Nginx**
3. 点击 **重启**

---

## ✅ 升级验证清单

### 🔍 功能验证
- [ ] **登录系统** - 确保可以正常登录
- [ ] **邮件发送测试**：
  - [ ] 发送1-2封邮件（同步模式）
  - [ ] 发送6封以上邮件（异步模式）
  - [ ] 检查邮件任务状态
- [ ] **AI解析功能**：
  - [ ] 职位解析
  - [ ] 候选人解析
  - [ ] AI邮件生成
- [ ] **模板功能**：
  - [ ] 创建邮件模板
  - [ ] 模板变量显示正确
- [ ] **分组功能**：
  - [ ] 候选人分组选择
  - [ ] 联系人分组选择

### 📊 性能验证
- [ ] **页面加载速度** - 应在3秒内加载完成
- [ ] **大批量邮件** - 超过5封邮件应立即响应（异步模式）
- [ ] **邮件发送日志** - 检查是否有错误日志

### 🔐 安全验证
- [ ] **SSL配置** - 邮件发送不应出现SSL冲突错误
- [ ] **权限检查** - 非管理员用户权限正确
- [ ] **数据隔离** - 用户只能看到自己的数据

---

## 🚨 常见问题解决

### 问题1：邮件发送失败
**症状**：发送邮件时提示"TLS/SSL冲突"
**解决**：
```bash
# 检查.env文件中的配置
EMAIL_USE_SSL=False
EMAIL_USE_TLS=True
```

### 问题2：静态文件404
**解决**：
```bash
python manage.py collectstatic --noinput
# 然后重启Nginx
```

### 问题3：模板变量不显示
**症状**：邮件模板中看不到变量说明
**解决**：清除浏览器缓存，检查模板文件是否正确上传

### 问题4：AI功能报错
**解决**：检查AI服务配置和网络连接

---

## 📞 回滚方案

如果升级后出现严重问题，可以快速回滚：

1. **停止Django服务**
2. **恢复备份文件**：
   ```bash
   cd /www/wwwroot/your_project_name/
   # 解压之前的备份
   tar -xzf backup_before_upgrade_*.tar.gz
   ```
3. **重启服务**

---

## 📈 升级后的新功能

### 🚀 异步批量邮件发送
- **小批量**（≤5封）：立即发送，实时反馈
- **大批量**（>5封）：异步处理，避免超时
- **状态跟踪**：可通过API查询发送进度

### 🎯 智能邮件功能
- **智能称呼**：自动生成"先生/女士"称呼
- **模板优化**：AI生成的邮件模板更准确
- **错误处理**：更robust的错误处理机制

### 🎨 界面改进
- **去重优化**：移除重复的模板变量说明
- **交互优化**：更好的用户反馈和进度显示

---

## 📋 部署检查清单

升级完成后，请逐项检查：

- [ ] 所有文件已正确上传
- [ ] .env配置已更新
- [ ] 数据库迁移已执行
- [ ] 静态文件已收集
- [ ] Django服务已重启
- [ ] Nginx已重启（如需要）
- [ ] 功能验证已通过
- [ ] 性能验证已通过
- [ ] 备份文件已保存

**升级完成时间**：约30-60分钟
**影响范围**：邮件发送、AI功能、用户界面
**风险等级**：中等（有备份和回滚方案）

---

💡 **提示**：建议在业务低峰期进行升级，确保有充足时间进行验证测试。