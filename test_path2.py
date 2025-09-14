import os
import json

# 直接测试用户数据文件
users_file = 'data/users.json'
print('Users file exists:', os.path.exists(users_file))

if os.path.exists(users_file):
    with open(users_file, 'r', encoding='utf-8') as f:
        users_data = json.load(f)
    print('Users data:', users_data)
    
    for username, user_info in users_data.items():
        user_dir = os.path.join('files', user_info.get('user_dir', username))
        print(f'User {username} directory: {user_dir}')
        print(f'Directory exists: {os.path.exists(user_dir)}')
        print(f'Absolute path: {os.path.abspath(user_dir)}')
        print('---')
else:
    print('No users file found')