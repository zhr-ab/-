class FileManager {
    constructor() {
        this.currentPath = '';
        this.selectedFiles = new Set();
        this.username = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadFiles();
    }

    bindEvents() {
        // 刷新按钮
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadFiles();
        });

        // 返回上级按钮
        document.getElementById('back-btn').addEventListener('click', () => {
            this.navigateUp();
        });

        // 新建文件夹按钮
        document.getElementById('new-folder-btn').addEventListener('click', () => {
            this.showCreateFolderModal();
        });

        // 上传文件按钮
        document.getElementById('upload-btn').addEventListener('click', () => {
            document.getElementById('file-input').click();
        });

        // 文件选择
        document.getElementById('file-input').addEventListener('change', (e) => {
            this.handleFileUpload(e.target.files);
        });

        // 模态框事件
        document.getElementById('modal-cancel').addEventListener('click', () => {
            this.hideModal();
        });

        document.getElementById('modal-confirm').addEventListener('click', () => {
            this.handleModalConfirm();
        });

        // 登录/退出按钮
        document.getElementById('login-btn').addEventListener('click', () => {
            window.location.href = 'login.html';
        });

        document.getElementById('logout-btn').addEventListener('click', () => {
            this.logout();
        });
    }

    async loadFiles() {
        try {
            if (!this.username) {
                this.setStatus('请先登录');
                this.renderLoginPrompt();
                return;
            }

            this.setStatus('加载中...');
            const response = await fetch('http://localhost:8000/api/files', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ path: this.currentPath })
            });

            if (response.status === 401) {
                this.handleUnauthorized();
                return;
            }

            if (!response.ok) {
                throw new Error('加载文件列表失败');
            }

            const files = await response.json();
            this.renderFileList(files);
            this.updatePathDisplay();
            this.setStatus('就绪');
        } catch (error) {
            this.setStatus('错误: ' + error.message);
            console.error('加载文件失败:', error);
        }
    }

    renderFileList(files) {
        const tbody = document.getElementById('file-list');
        tbody.innerHTML = '';

        // 添加父目录链接（如果不是根目录）
        if (this.currentPath !== '') {
            const parentRow = this.createFileRow({
                name: '..',
                is_dir: true,
                size: '',
                modified: '',
                full_path: this.getParentPath()
            }, true);
            tbody.appendChild(parentRow);
        }

        files.forEach(file => {
            const row = this.createFileRow(file);
            tbody.appendChild(row);
        });

        this.updateSelectedCount();
    }

    createFileRow(file, isParent = false) {
        const row = document.createElement('tr');
        row.className = 'file-item';
        if (isParent) row.classList.add('parent-dir');

        // 名称列
        const nameCell = document.createElement('td');
        const icon = document.createElement('span');
        icon.className = 'file-icon';
        icon.textContent = file.is_dir ? '📁' : '📄';
        
        const nameSpan = document.createElement('span');
        nameSpan.className = 'file-name';
        nameSpan.textContent = file.name;
        
        nameCell.appendChild(icon);
        nameCell.appendChild(nameSpan);

        // 类型列
        const typeCell = document.createElement('td');
        typeCell.className = 'file-type';
        typeCell.textContent = file.is_dir ? '文件夹' : this.getFileType(file.name);

        // 大小列
        const sizeCell = document.createElement('td');
        sizeCell.className = 'file-size';
        sizeCell.textContent = file.is_dir ? '-' : this.formatFileSize(file.size);

        // 修改时间列
        const timeCell = document.createElement('td');
        timeCell.className = 'file-time';
        timeCell.textContent = file.modified || '-'; 

        // 操作列
        const actionsCell = document.createElement('td');
        actionsCell.className = 'file-actions';
        
        if (!isParent) {
            if (!file.is_dir) {
                const downloadBtn = document.createElement('button');
                downloadBtn.className = 'btn btn-primary';
                downloadBtn.textContent = '下载';
                downloadBtn.onclick = (e) => {
                    e.stopPropagation();
                    this.downloadFile(file);
                };
                actionsCell.appendChild(downloadBtn);
            }
            
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn btn-danger';
            deleteBtn.textContent = '删除';
            deleteBtn.onclick = (e) => {
                e.stopPropagation();
                this.deleteFile(file);
            };
            actionsCell.appendChild(deleteBtn);
        }

        row.appendChild(nameCell);
        row.appendChild(typeCell);
        row.appendChild(sizeCell);
        row.appendChild(timeCell);
        row.appendChild(actionsCell);

        // 点击行事件
        if (file.is_dir) {
            row.addEventListener('click', () => {
                if (isParent) {
                    this.navigateTo(file.full_path);
                } else {
                    this.navigateTo(file.full_path);
                }
            });
        } else {
            row.addEventListener('click', (e) => {
                if (e.target.tagName !== 'BUTTON') {
                    this.toggleFileSelection(row, file.name);
                }
            });
        }

        return row;
    }

    toggleFileSelection(row, fileName) {
        if (this.selectedFiles.has(fileName)) {
            this.selectedFiles.delete(fileName);
            row.classList.remove('selected');
        } else {
            this.selectedFiles.add(fileName);
            row.classList.add('selected');
        }
        this.updateSelectedCount();
    }

    updateSelectedCount() {
        document.getElementById('selected-count').textContent = 
            `已选择: ${this.selectedFiles.size} 个项目`;
    }

    navigateTo(path) {
        this.currentPath = path;
        this.selectedFiles.clear();
        this.loadFiles();
    }

    navigateUp() {
        if (this.currentPath !== '') {
            this.navigateTo(this.getParentPath());
        }
    }

    getParentPath() {
        const pathParts = this.currentPath.split('/').filter(part => part);
        pathParts.pop();
        return pathParts.join('/');
    }

    async deleteFile(file) {
        if (!confirm(`确定要删除 "${file.name}" 吗？`)) {
            return;
        }

        try {
            this.setStatus('删除中...');
            const response = await fetch('http://localhost:8000/api/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    path: this.currentPath,
                    name: file.name,
                    is_dir: file.is_dir
                })
            });

            if (response.status === 401) {
                this.handleUnauthorized();
                return;
            }

            if (!response.ok) {
                throw new Error('删除失败');
            }

            this.setStatus('删除成功');
            this.loadFiles();
        } catch (error) {
            this.setStatus('错误: ' + error.message);
            console.error('删除文件失败:', error);
        }
    }

    async downloadFile(file) {
        try {
            this.setStatus('准备下载中...');
            
            // 创建下载链接
            const downloadUrl = `http://localhost:8000/api/download?path=${encodeURIComponent(this.currentPath)}&filename=${encodeURIComponent(file.name)}`;
            
            // 创建临时链接并触发下载
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = file.name;
            link.style.display = 'none';
            
            // 添加凭证信息（cookies）
            link.setAttribute('crossorigin', 'use-credentials');
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            this.setStatus('下载已开始');
        } catch (error) {
            this.setStatus('错误: ' + error.message);
            console.error('下载文件失败:', error);
        }
    }

    showCreateFolderModal() {
        document.getElementById('modal-title').textContent = '新建文件夹';
        document.getElementById('folder-name').value = '';
        document.getElementById('modal').style.display = 'flex';
    }

    hideModal() {
        document.getElementById('modal').style.display = 'none';
    }

    async handleModalConfirm() {
        const folderName = document.getElementById('folder-name').value.trim();
        if (!folderName) {
            alert('请输入文件夹名称');
            return;
        }

        try {
            this.setStatus('创建文件夹中...');
            const response = await fetch('http://localhost:8000/api/create-folder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    path: this.currentPath,
                    name: folderName
                })
            });

            if (response.status === 401) {
                this.handleUnauthorized();
                return;
            }

            if (!response.ok) {
                throw new Error('创建文件夹失败');
            }

            this.hideModal();
            this.setStatus('文件夹创建成功');
            this.loadFiles();
        } catch (error) {
            this.setStatus('错误: ' + error.message);
            console.error('创建文件夹失败:', error);
        }
    }

    async handleFileUpload(files) {
        if (files.length === 0) return;

        try {
            this.setStatus('上传中...');
            
            for (let i = 0; i < files.length; i++) {
                const formData = new FormData();
                formData.append('file', files[i]);
                formData.append('path', this.currentPath);

                const response = await fetch('http://localhost:8000/api/upload', {
                    method: 'POST',
                    credentials: 'include',
                    body: formData
                });

                if (response.status === 401) {
                    this.handleUnauthorized();
                    return;
                }

                if (!response.ok) {
                    throw new Error(`上传文件 ${files[i].name} 失败`);
                }
            }

            this.setStatus('上传完成');
            this.loadFiles();
        } catch (error) {
            this.setStatus('错误: ' + error.message);
            console.error('上传文件失败:', error);
        }
    }

    setStatus(message) {
        document.getElementById('status-info').textContent = message;
    }

    updatePathDisplay() {
        document.getElementById('current-path').textContent = this.currentPath;
    }

    getFileType(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const types = {
            'txt': '文本文件',
            'pdf': 'PDF文档',
            'doc': 'Word文档',
            'docx': 'Word文档',
            'xls': 'Excel表格',
            'xlsx': 'Excel表格',
            'jpg': 'JPEG图像',
            'jpeg': 'JPEG图像',
            'png': 'PNG图像',
            'gif': 'GIF图像',
            'mp4': 'MP4视频',
            'mp3': 'MP3音频',
            'zip': '压缩文件',
            'rar': '压缩文件',
            'exe': '可执行文件',
            'js': 'JavaScript文件',
            'html': '网页文件',
            'css': '样式表文件',
            'py': 'Python脚本'
        };
        return types[ext] || '文件';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async checkAuth() {
        try {
            const response = await fetch('http://localhost:8000/api/user/info', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const userInfo = await response.json();
                this.username = userInfo.username || userInfo.user_dir;
                this.updateUserDisplay();
                this.loadFiles();
            } else {
                this.renderLoginPrompt();
            }
        } catch (error) {
            this.renderLoginPrompt();
        }
    }

    updateUserDisplay() {
        if (this.username) {
            document.getElementById('username-display').textContent = this.username;
            document.getElementById('login-btn').style.display = 'none';
            document.getElementById('logout-btn').style.display = 'block';
        } else {
            document.getElementById('username-display').textContent = '未登录';
            document.getElementById('login-btn').style.display = 'block';
            document.getElementById('logout-btn').style.display = 'none';
        }
    }

    async logout() {
        try {
            const response = await fetch('http://localhost:8000/api/logout', {
                method: 'POST',
                credentials: 'include'
            });
            
            if (response.ok) {
                this.username = null;
                this.currentPath = '';
                this.updateUserDisplay();
                this.renderLoginPrompt();
                this.setStatus('已退出登录');
            }
        } catch (error) {
            console.error('退出登录失败:', error);
        }
    }

    handleUnauthorized() {
        this.username = null;
        this.updateUserDisplay();
        this.renderLoginPrompt();
        this.setStatus('会话已过期，请重新登录');
    }

    renderLoginPrompt() {
        const tbody = document.getElementById('file-list');
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 40px;">
                    <h3>请登录以访问文件管理器</h3>
                    <p>您需要登录才能查看和管理您的文件</p>
                    <button onclick="window.location.href='login.html'" class="btn btn-primary">
                        立即登录
                    </button>
                </td>
            </tr>
        `;
        this.updatePathDisplay();
    }
}

// 初始化文件管理器
document.addEventListener('DOMContentLoaded', () => {
    const fileManager = new FileManager();
    fileManager.checkAuth();
});