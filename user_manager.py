import os
import json
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

class UserManager:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, 'users.json')
        self.sessions_file = os.path.join(data_dir, 'sessions.json')
        self.reset_tokens_file = os.path.join(data_dir, 'reset_tokens.json')
        
        # 创建数据目录
        os.makedirs(data_dir, exist_ok=True)
        
        # 初始化文件
        self._init_files()
        
        # 邮件配置（需要用户配置）
        self.smtp_config = {
            'server': 'smtp.gmail.com',
            'port': 587,
            'username': 'your_email@gmail.com',
            'password': 'your_app_password'
        }
    
    def _init_files(self):
        """初始化数据文件"""
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        
        if not os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        
        if not os.path.exists(self.reset_tokens_file):
            with open(self.reset_tokens_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def _hash_password(self, password):
        """哈希密码"""
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${hashed}"
    
    def _verify_password(self, password, hashed_password):
        """验证密码"""
        if not hashed_password or '$' not in hashed_password:
            return False
        salt, stored_hash = hashed_password.split('$', 1)
        computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return computed_hash == stored_hash
    
    def _generate_token(self):
        """生成随机token"""
        return secrets.token_urlsafe(32)
    
    def _load_data(self, file_path):
        """加载JSON数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_data(self, file_path, data):
        """保存JSON数据"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def register_user(self, username, password, email):
        """注册新用户"""
        users = self._load_data(self.users_file)
        
        # 检查用户名和邮箱是否已存在
        if username in users:
            return False, "用户名已存在"
        
        for user_data in users.values():
            if user_data.get('email') == email:
                return False, "邮箱已被注册"
        
        # 创建用户
        users[username] = {
            'password_hash': self._hash_password(password),
            'email': email,
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'is_verified': False,
            'user_dir': username  # 用户文件目录
        }
        
        self._save_data(self.users_file, users)
        
        # 创建用户目录
        user_files_dir = os.path.join('files', username)
        os.makedirs(user_files_dir, exist_ok=True)
        
        return True, "注册成功"
    
    def login_user(self, username, password):
        """用户登录"""
        users = self._load_data(self.users_file)
        
        if username not in users:
            return False, "用户不存在", None
        
        user_data = users[username]
        if not self._verify_password(password, user_data['password_hash']):
            return False, "密码错误", None
        
        # 更新最后登录时间
        user_data['last_login'] = datetime.now().isoformat()
        self._save_data(self.users_file, users)
        
        # 创建会话
        session_token = self._generate_token()
        sessions = self._load_data(self.sessions_file)
        sessions[session_token] = {
            'username': username,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
        }
        self._save_data(self.sessions_file, sessions)
        
        return True, "登录成功", session_token
    
    def verify_session(self, session_token):
        """验证会话"""
        sessions = self._load_data(self.sessions_file)
        
        if session_token not in sessions:
            return False, None
        
        session_data = sessions[session_token]
        expires_at = datetime.fromisoformat(session_data['expires_at'])
        
        if datetime.now() > expires_at:
            # 会话过期，删除
            del sessions[session_token]
            self._save_data(self.sessions_file, sessions)
            return False, None
        
        return True, session_data['username']
    
    def logout_user(self, session_token):
        """用户登出"""
        sessions = self._load_data(self.sessions_file)
        
        if session_token in sessions:
            del sessions[session_token]
            self._save_data(self.sessions_file, sessions)
            return True, "登出成功"
        
        return False, "会话不存在"
    
    def get_user_info(self, username):
        """获取用户信息"""
        users = self._load_data(self.users_file)
        
        if username in users:
            user_data = users[username].copy()
            # 移除敏感信息
            user_data.pop('password_hash', None)
            return True, user_data
        
        return False, "用户不存在"
    
    def generate_reset_token(self, email):
        """生成密码重置token"""
        users = self._load_data(self.users_file)
        
        # 查找邮箱对应的用户
        username = None
        for uname, user_data in users.items():
            if user_data.get('email') == email:
                username = uname
                break
        
        if not username:
            return False, "邮箱未注册"
        
        # 生成重置token
        reset_token = self._generate_token()
        reset_tokens = self._load_data(self.reset_tokens_file)
        
        reset_tokens[reset_token] = {
            'username': username,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        self._save_data(self.reset_tokens_file, reset_tokens)
        
        # 发送重置邮件（需要配置SMTP）
        self._send_reset_email(email, reset_token)
        
        return True, "重置邮件已发送"
    
    def reset_password(self, reset_token, new_password):
        """重置密码"""
        reset_tokens = self._load_data(self.reset_tokens_file)
        
        if reset_token not in reset_tokens:
            return False, "无效的重置链接"
        
        token_data = reset_tokens[reset_token]
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        
        if datetime.now() > expires_at:
            del reset_tokens[reset_token]
            self._save_data(self.reset_tokens_file, reset_tokens)
            return False, "重置链接已过期"
        
        username = token_data['username']
        users = self._load_data(self.users_file)
        
        if username not in users:
            return False, "用户不存在"
        
        # 更新密码
        users[username]['password_hash'] = self._hash_password(new_password)
        self._save_data(self.users_file, users)
        
        # 删除已使用的token
        del reset_tokens[reset_token]
        self._save_data(self.reset_tokens_file, reset_tokens)
        
        return True, "密码重置成功"
    
    def _send_reset_email(self, email, reset_token):
        """发送密码重置邮件"""
        try:
            # 这里需要配置真实的SMTP服务器信息
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['username']
            msg['To'] = email
            msg['Subject'] = '文件管理器 - 密码重置'
            
            reset_url = f"http://localhost:8000/reset-password?token={reset_token}"
            body = f"""
            您请求重置文件管理器账户的密码。
            
            请点击以下链接重置密码（1小时内有效）：
            {reset_url}
            
            如果您没有请求重置密码，请忽略此邮件。
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # 实际发送邮件需要取消注释并配置SMTP
            # with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
            #     server.starttls()
            #     server.login(self.smtp_config['username'], self.smtp_config['password'])
            #     server.send_message(msg)
            
            print(f"重置邮件已生成（模拟）: {reset_url}")
            return True
            
        except Exception as e:
            print(f"发送邮件失败: {e}")
            return False
    
    def update_email(self, username, new_email):
        """更新邮箱"""
        users = self._load_data(self.users_file)
        
        if username not in users:
            return False, "用户不存在"
        
        # 检查邮箱是否已被其他用户使用
        for uname, user_data in users.items():
            if uname != username and user_data.get('email') == new_email:
                return False, "邮箱已被其他用户使用"
        
        users[username]['email'] = new_email
        self._save_data(self.users_file, users)
        
        return True, "邮箱更新成功"
    
    def get_user_files_dir(self, username):
        """获取用户文件目录"""
        users = self._load_data(self.users_file)
        
        if username in users:
            user_dir = users[username].get('user_dir', username)
            return os.path.join('files', user_dir)
        
        return None