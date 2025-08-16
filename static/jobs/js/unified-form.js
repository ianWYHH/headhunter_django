/**
 * 统一表单交互和验证脚本
 * 提供一致的表单用户体验
 */

document.addEventListener('DOMContentLoaded', function() {
    // 表单验证和增强
    initFormValidation();
    initFormInteraction();
    initFormSubmission();
});

/**
 * 初始化表单验证
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate="true"], .needs-validation');
    
    forms.forEach(function(form) {
        // 实时验证
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(function(input) {
            input.addEventListener('blur', function() {
                validateField(this);
            });
            
            input.addEventListener('input', function() {
                clearFieldError(this);
            });
        });
        
        // 表单提交验证
        form.addEventListener('submit', function(event) {
            if (!validateForm(this)) {
                event.preventDefault();
                event.stopPropagation();
            }
            this.classList.add('was-validated');
        });
    });
}

/**
 * 验证单个字段
 */
function validateField(field) {
    const value = field.value.trim();
    const isRequired = field.hasAttribute('required') || field.classList.contains('required');
    const fieldType = field.type || field.tagName.toLowerCase();
    
    // 清除之前的错误状态
    clearFieldError(field);
    
    // 必填验证
    if (isRequired && !value) {
        showFieldError(field, '此字段为必填项');
        return false;
    }
    
    // 类型验证
    if (value) {
        switch (fieldType) {
            case 'email':
                if (!isValidEmail(value)) {
                    showFieldError(field, '请输入有效的邮箱地址');
                    return false;
                }
                break;
            case 'tel':
                if (!isValidPhone(value)) {
                    showFieldError(field, '请输入有效的电话号码');
                    return false;
                }
                break;
            case 'url':
                if (!isValidUrl(value)) {
                    showFieldError(field, '请输入有效的网址');
                    return false;
                }
                break;
        }
    }
    
    // 自定义验证规则
    const customValidation = field.getAttribute('data-validation');
    if (customValidation && value) {
        const result = validateCustomRule(value, customValidation);
        if (!result.valid) {
            showFieldError(field, result.message);
            return false;
        }
    }
    
    // 验证通过
    showFieldSuccess(field);
    return true;
}

/**
 * 验证整个表单
 */
function validateForm(form) {
    const fields = form.querySelectorAll('input, select, textarea');
    let isValid = true;
    
    fields.forEach(function(field) {
        if (!validateField(field)) {
            isValid = false;
        }
    });
    
    return isValid;
}

/**
 * 显示字段错误
 */
function showFieldError(field, message) {
    field.classList.add('is-invalid');
    field.classList.remove('is-valid');
    
    let errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        field.parentNode.appendChild(errorDiv);
    }
    
    errorDiv.innerHTML = '<i class="fas fa-exclamation-triangle"></i> ' + message;
}

/**
 * 显示字段成功状态
 */
function showFieldSuccess(field) {
    if (field.value.trim()) {
        field.classList.add('is-valid');
        field.classList.remove('is-invalid');
    }
}

/**
 * 清除字段错误状态
 */
function clearFieldError(field) {
    field.classList.remove('is-invalid', 'is-valid');
    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

/**
 * 初始化表单交互
 */
function initFormInteraction() {
    // 自动聚焦第一个输入框
    const firstInput = document.querySelector('form input:not([type="hidden"]):not([readonly])');
    if (firstInput) {
        firstInput.focus();
    }
    
    // 字数统计
    const textareas = document.querySelectorAll('textarea[data-max-length]');
    textareas.forEach(function(textarea) {
        const maxLength = parseInt(textarea.getAttribute('data-max-length'));
        const counterDiv = document.createElement('div');
        counterDiv.className = 'form-text text-end';
        textarea.parentNode.appendChild(counterDiv);
        
        function updateCounter() {
            const remaining = maxLength - textarea.value.length;
            counterDiv.textContent = `剩余 ${remaining} 字符`;
            counterDiv.className = remaining < 10 ? 'form-text text-end text-warning' : 'form-text text-end';
        }
        
        textarea.addEventListener('input', updateCounter);
        updateCounter();
    });
    
    // 密码显示切换
    const passwordToggles = document.querySelectorAll('[data-toggle="password"]');
    passwordToggles.forEach(function(toggle) {
        toggle.addEventListener('click', function() {
            const target = document.querySelector(this.getAttribute('data-target'));
            if (target) {
                const type = target.getAttribute('type') === 'password' ? 'text' : 'password';
                target.setAttribute('type', type);
                
                const icon = this.querySelector('i');
                if (icon) {
                    icon.className = type === 'password' ? 'fas fa-eye' : 'fas fa-eye-slash';
                }
            }
        });
    });
}

/**
 * 初始化表单提交处理
 */
function initFormSubmission() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            const submitBtn = this.querySelector('button[type="submit"], input[type="submit"]');
            
            if (submitBtn && !submitBtn.disabled) {
                // 显示加载状态
                const originalText = submitBtn.innerHTML;
                const loadingText = submitBtn.getAttribute('data-loading-text') || '提交中...';
                
                submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${loadingText}`;
                submitBtn.disabled = true;
                
                // 如果是AJAX表单，不需要恢复按钮状态
                if (!this.hasAttribute('hx-post') && !this.hasAttribute('hx-put')) {
                    // 3秒后恢复按钮状态（防止网络问题）
                    setTimeout(function() {
                        submitBtn.innerHTML = originalText;
                        submitBtn.disabled = false;
                    }, 3000);
                }
            }
        });
    });
}

/**
 * 验证函数
 */
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function isValidPhone(phone) {
    const re = /^[\d\s\-\+\(\)]+$/;
    return re.test(phone) && phone.length >= 7;
}

function isValidUrl(url) {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
}

function validateCustomRule(value, rule) {
    switch (rule) {
        case 'chinese-name':
            const chineseNameRe = /^[\u4e00-\u9fa5]{2,10}$/;
            return {
                valid: chineseNameRe.test(value),
                message: '请输入2-10个中文字符的姓名'
            };
        case 'company-name':
            return {
                valid: value.length >= 2 && value.length <= 50,
                message: '公司名称长度应在2-50字符之间'
            };
        case 'position-title':
            return {
                valid: value.length >= 2 && value.length <= 30,
                message: '职位名称长度应在2-30字符之间'
            };
        default:
            return { valid: true };
    }
}

/**
 * 公共工具函数
 */
window.FormUtils = {
    validateField: validateField,
    validateForm: validateForm,
    showFieldError: showFieldError,
    showFieldSuccess: showFieldSuccess,
    clearFieldError: clearFieldError,
    
    // 重置表单
    resetForm: function(form) {
        form.reset();
        form.classList.remove('was-validated');
        const fields = form.querySelectorAll('.is-invalid, .is-valid');
        fields.forEach(function(field) {
            field.classList.remove('is-invalid', 'is-valid');
        });
        const errorDivs = form.querySelectorAll('.invalid-feedback');
        errorDivs.forEach(function(div) {
            div.remove();
        });
    },
    
    // 设置字段值
    setFieldValue: function(fieldName, value) {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            field.value = value;
            validateField(field);
        }
    },
    
    // 禁用表单
    disableForm: function(form) {
        const elements = form.querySelectorAll('input, select, textarea, button');
        elements.forEach(function(element) {
            element.disabled = true;
        });
    },
    
    // 启用表单
    enableForm: function(form) {
        const elements = form.querySelectorAll('input, select, textarea, button');
        elements.forEach(function(element) {
            element.disabled = false;
        });
    }
};