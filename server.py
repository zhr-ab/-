import os
import json
import shutil
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from user_manager import UserManager

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 设置秘钥用于会话管理
app.secret_key = 'your-secret-key-here-change-in-production'

class FileManagerServer:
    def __init__(self):
        self.allowed_extensions = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar'}
        self.user_manager = UserManager()
    
    def get_user_files_path(self, username, path=''):
        """获取用户文件路径"""
        user_base_dir = self.user_manager.get_user_files_dir(username)
        if not user_base_dir:
            return None
        
        # 安全检查：防止目录遍历攻击
        if path and ('..' in path or path.startswith('/') or path.startswith('\\')):
            return user_base_dir
        
        # 确保路径使用正确的分隔符
        if path:
            path = path.replace('\\', '/')
        
        full_path = os.path.join(user_base_dir, path) if path else user_base_dir
        return os.path.normpath(full_path)
    
    def get_file_info(self, file_path):
        """获取文件信息"""
        try:
            stat = os.stat(file_path)
            return {
                'name': os.path.basename(file_path),
                'is_dir': os.path.isdir(file_path),
                'size': stat.st_size if not os.path.isdir(file_path) else 0,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'full_path': file_path
            }
        except Exception as e:
            print(f"Error getting file info for {file_path}: {e}")
            return None
    
    def list_files(self, username, path=''):
        """列出用户目录下的文件"""
        user_path = self.get_user_files_path(username, path)
        if not user_path or not os.path.exists(user_path):
            return []
        
        try:
            files = []
            for item in os.listdir(user_path):
                item_path = os.path.join(user_path, item)
                file_info = self.get_file_info(item_path)
                if file_info:
                    files.append(file_info)
            
            # 按文件夹优先排序
            files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            return files
        except Exception as e:
            print(f"Error listing files in {user_path}: {e}")
            return []
    
    def create_folder(self, username, path, name):
        """创建文件夹"""
        user_path = self.get_user_files_path(username, path)
        if not user_path:
            return False, "用户目录不存在"
        
        try:
            folder_path = os.path.join(user_path, name)
            if os.path.exists(folder_path):
                return False, "文件夹已存在"
            
            os.makedirs(folder_path)
            return True, "文件夹创建成功"
        except Exception as e:
            return False, f"创建文件夹失败: {str(e)}"
    
    def delete_item(self, username, path, name, is_dir):
        """删除文件或文件夹"""
        user_path = self.get_user_files_path(username, path)
        if not user_path:
            return False, "用户目录不存在"
        
        try:
            item_path = os.path.join(user_path, name)
            if not os.path.exists(item_path):
                return False, "文件或文件夹不存在"
            
            if is_dir:
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
            
            return True, "删除成功"
        except Exception as e:
            return False, f"删除失败: {str(e)}"
    
    def allowed_file(self, filename):
        """检查文件扩展名是否允许"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

file_manager = FileManagerServer()

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

def require_auth(f):
    """认证装饰器"""
    def decorated(*args, **kwargs):
        session_token = request.headers.get('X-Session-Token') or request.cookies.get('session_token')
        
        if not session_token:
            return jsonify({'error': '未授权访问'}), 401
        
        valid, username = file_manager.user_manager.verify_session(session_token)
        if not valid:
            return jsonify({'error': '会话已过期或无效'}), 401
        
        # 将用户名添加到请求上下文中
        request.username = username
        return f(*args, **kwargs)
    
    decorated.__name__ = f.__name__
    return decorated

@app.route('/api/register', methods=['POST'])
def api_register():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        
        if not username or not password or not email:
            return jsonify({'error': '用户名、密码和邮箱不能为空'}), 400
        
        success, message = file_manager.user_manager.register_user(username, password, email)
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400
        
        success, message, session_token = file_manager.user_manager.login_user(username, password)
        if success:
            response = jsonify({'message': message, 'username': username})
            response.set_cookie('session_token', session_token, httponly=True, max_age=24*3600)
            return response
        else:
            return jsonify({'error': message}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
@require_auth
def api_logout():
    try:
        session_token = request.headers.get('X-Session-Token') or request.cookies.get('session_token')
        success, message = file_manager.user_manager.logout_user(session_token)
        
        if success:
            response = jsonify({'message': message})
            response.set_cookie('session_token', '', expires=0)
            return response
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/info', methods=['GET'])
@require_auth
def api_user_info():
    try:
        success, user_info = file_manager.user_manager.get_user_info(request.username)
        if success:
            return jsonify(user_info)
        else:
            return jsonify({'error': user_info}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/forgot-password', methods=['POST'])
def api_forgot_password():
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'error': '邮箱不能为空'}), 400
        
        success, message = file_manager.user_manager.generate_reset_token(email)
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    try:
        data = request.get_json()
        token = data.get('token', '')
        new_password = data.get('new_password', '')
        
        if not token or not new_password:
            return jsonify({'error': '重置token和新密码不能为空'}), 400
        
        success, message = file_manager.user_manager.reset_password(token, new_password)
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files', methods=['POST'])
@require_auth
def api_list_files():
    try:
        data = request.get_json()
        path = data.get('path', '')
        
        files = file_manager.list_files(request.username, path)
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-folder', methods=['POST'])
@require_auth
def api_create_folder():
    try:
        data = request.get_json()
        path = data.get('path', '')
        name = data.get('name', '')
        
        if not name:
            return jsonify({'error': '文件夹名称不能为空'}), 400
        
        success, message = file_manager.create_folder(request.username, path, name)
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete', methods=['POST'])
@require_auth
def api_delete_item():
    try:
        data = request.get_json()
        path = data.get('path', '')
        name = data.get('name', '')
        is_dir = data.get('is_dir', False)
        
        if not name:
            return jsonify({'error': '文件名不能为空'}), 400
        
        success, message = file_manager.delete_item(request.username, path, name, is_dir)
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['GET'])
@require_auth
def api_download_file():
    try:
        path = request.args.get('path', '')
        filename = request.args.get('filename', '')
        
        if not filename:
            return jsonify({'error': '文件名不能为空'}), 400
        
        user_path = file_manager.get_user_files_path(request.username, path)
        if not user_path or not os.path.exists(user_path):
            return jsonify({'error': '用户目录不存在'}), 404
        
        file_path = os.path.join(user_path, filename)
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            return jsonify({'error': '文件不存在或不是文件'}), 404
        
        # 安全检查：防止目录遍历攻击
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            return jsonify({'error': '无效的文件名'}), 400
        
        return send_from_directory(user_path, filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
@require_auth
def api_upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400
        
        file = request.files['file']
        path = request.form.get('path', '')
        
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        if file:
            user_path = file_manager.get_user_files_path(request.username, path)
            if not user_path:
                return jsonify({'error': '用户目录不存在'}), 400
            
            # 确保目标目录存在
            os.makedirs(user_path, exist_ok=True)
            
            file_path = os.path.join(user_path, file.filename)
            
            try:
                file.save(file_path)
                return jsonify({'message': '文件上传成功'})
            except Exception as save_error:
                print(f"文件保存错误: {save_error}")
                return jsonify({'error': f'文件保存失败: {str(save_error)}'}), 500
        else:
            return jsonify({'error': '文件无效'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '接口不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '服务器内部错误'}), 500

if __name__ == '__main__':
    print("启动文件管理器服务器...")
    print("访问地址: http://localhost:8000")
    print("按 Ctrl+C 停止服务器")
    
    app.run(host='0.0.0.0', port=8000, debug=True)