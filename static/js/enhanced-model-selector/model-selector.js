
// 增强的AI模型选择器
class EnhancedModelSelector {
    constructor(containerId, models) {
        this.container = document.getElementById(containerId);
        this.models = models;
        this.selectedModel = null;
        this.isOpen = false;
        
        this.init();
    }
    
    init() {
        this.render();
        this.bindEvents();
        
        // 设置默认选择 (qwen-plus 优先)
        const defaultModel = this.models.find(m => m.key === 'qwen_plus') || this.models[0];
        if (defaultModel) {
            this.selectModel(defaultModel);
        }
    }
    
    render() {
        this.container.innerHTML = `
            <div class="ai-model-selector">
                <div class="current-model-display" id="current-model">
                    <span>请选择AI模型</span>
                </div>
                <div class="model-dropdown" id="model-dropdown">
                    <div class="model-search">
                        <input type="text" placeholder="搜索模型..." id="model-search">
                    </div>
                    <div class="model-list" id="model-list">
                        ${this.renderModelList()}
                    </div>
                </div>
                <input type="hidden" name="model_provider" id="model_provider">
            </div>
        `;
    }
    
    renderModelList(filter = '') {
        const filteredModels = this.models.filter(model => 
            model.name.toLowerCase().includes(filter.toLowerCase()) ||
            model.description.toLowerCase().includes(filter.toLowerCase())
        );
        
        return filteredModels.map(model => `
            <div class="ai-model-option" data-model-key="${model.key}">
                <div class="model-name">${model.name}</div>
                <div class="model-description">${model.description}</div>
                ${this.renderFeatures(model.features || {})}
            </div>
        `).join('');
    }
    
    renderFeatures(features) {
        if (!features || Object.keys(features).length === 0) {
            return '';
        }
        
        const tags = [];
        
        if (features.context_length) {
            tags.push(`<span class="feature-tag context">上下文: ${features.context_length}</span>`);
        }
        
        if (features.free_tokens) {
            tags.push(`<span class="feature-tag tokens">${features.free_tokens}</span>`);
        }
        
        if (features.suitable_for) {
            tags.push(`<span class="feature-tag scenario">适用: ${features.suitable_for}</span>`);
        }
        
        return tags.length > 0 ? `<div class="model-features">${tags.join('')}</div>` : '';
    }
    
    bindEvents() {
        const currentModel = document.getElementById('current-model');
        const dropdown = document.getElementById('model-dropdown');
        const search = document.getElementById('model-search');
        const modelList = document.getElementById('model-list');
        
        // 点击当前模型显示/隐藏下拉框
        currentModel.addEventListener('click', () => {
            this.toggleDropdown();
        });
        
        // 搜索功能
        search.addEventListener('input', (e) => {
            const filter = e.target.value;
            modelList.innerHTML = this.renderModelList(filter);
            this.bindModelOptions();
        });
        
        // 点击外部关闭下拉框
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.closeDropdown();
            }
        });
        
        this.bindModelOptions();
    }
    
    bindModelOptions() {
        const options = document.querySelectorAll('.ai-model-option');
        options.forEach(option => {
            option.addEventListener('click', () => {
                const modelKey = option.dataset.modelKey;
                const model = this.models.find(m => m.key === modelKey);
                if (model) {
                    this.selectModel(model);
                }
            });
        });
    }
    
    selectModel(model) {
        this.selectedModel = model;
        
        // 更新显示
        const currentModel = document.getElementById('current-model');
        currentModel.innerHTML = `
            <div>
                <div class="model-name">${model.name}</div>
                <div class="model-description" style="font-size: 0.85em; color: #666;">
                    ${model.description}
                </div>
            </div>
        `;
        
        // 更新隐藏输入
        const input = document.getElementById('model_provider');
        input.value = model.key;
        
        // 触发change事件
        input.dispatchEvent(new Event('change'));
        
        this.closeDropdown();
        
        // 更新选中样式
        document.querySelectorAll('.ai-model-option').forEach(opt => {
            opt.classList.remove('selected');
        });
        
        const selectedOption = document.querySelector(`[data-model-key="${model.key}"]`);
        if (selectedOption) {
            selectedOption.classList.add('selected');
        }
    }
    
    toggleDropdown() {
        const dropdown = document.getElementById('model-dropdown');
        this.isOpen = !this.isOpen;
        dropdown.classList.toggle('show', this.isOpen);
        
        if (this.isOpen) {
            // 清空搜索
            document.getElementById('model-search').value = '';
            document.getElementById('model-list').innerHTML = this.renderModelList();
            this.bindModelOptions();
        }
    }
    
    closeDropdown() {
        const dropdown = document.getElementById('model-dropdown');
        this.isOpen = false;
        dropdown.classList.remove('show');
    }
    
    getSelectedModel() {
        return this.selectedModel;
    }
}

// 工具函数：初始化增强模型选择器
function initEnhancedModelSelector(containerId, models) {
    return new EnhancedModelSelector(containerId, models);
}
