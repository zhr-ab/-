import os
from user_manager import UserManager

# 测试文件上传路径
manager = UserManager()
user_dir = manager.get_user_files_dir('testuser')
print('User files directory:', user_dir)
print('Absolute path:', os.path.abspath(user_dir) if user_dir else 'None')
print('Directory exists:', os.path.exists(user_dir) if user_dir else 'False')

# 测试当前工作目录
print('Current working directory:', os.getcwd())