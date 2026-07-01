"""
数据库初始化种子脚本：创建默认角色和管理员账号
运行: python seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models.user import User
from app.models.role import Role, user_roles

# 初始化表结构
init_db()
db = SessionLocal()

# ===== 创建默认角色 =====
default_roles = [
    {
        "name": "super_admin",
        "display_name": "超级管理员",
        "permissions": [
            "admin:users", "admin:roles", "admin:logs", "admin:settings",
            "doc:upload", "doc:delete", "doc:view",
            "kb:manage", "kb:export",
            "chat:use",
            "report:generate", "report:view",
        ],
    },
    {
        "name": "admin",
        "display_name": "管理员",
        "permissions": [
            "doc:upload", "doc:delete", "doc:view",
            "kb:manage", "kb:export",
            "chat:use",
            "report:generate", "report:view",
        ],
    },
    {
        "name": "user",
        "display_name": "普通用户",
        "permissions": [
            "doc:upload", "doc:view",
            "chat:use",
            "report:generate", "report:view",
        ],
    },
    {
        "name": "guest",
        "display_name": "访客",
        "permissions": [],
    },
]

created_roles = {}
for role_data in default_roles:
    existing = db.query(Role).filter(Role.name == role_data["name"]).first()
    if existing:
        print(f"[SKIP] 角色 {role_data['name']} 已存在")
        created_roles[role_data["name"]] = existing
    else:
        role = Role(**role_data)
        db.add(role)
        db.flush()
        created_roles[role_data["name"]] = role
        print(f"[OK] 创建角色: {role_data['name']}")

# ===== 创建默认超级管理员 =====
admin_user = db.query(User).filter(User.username == "admin").first()
if admin_user:
    print("[SKIP] 管理员账号 admin 已存在")
else:
    admin_user = User(
        username="admin",
        password_hash=hash_password("admin123456"),
        email="admin@rag-financial.com",
        status="active",
    )
    db.add(admin_user)
    db.flush()

    # 分配超级管理员角色
    super_admin_role = created_roles.get("super_admin")
    if super_admin_role:
        db.execute(
            user_roles.insert().values(user_id=admin_user.id, role_id=super_admin_role.id)
        )

    print("[OK] 创建管理员账号: admin / admin123456")

db.commit()
db.close()
print("\n====== 初始化完成 ======")
print("管理员: admin / admin123456")
print("角色: super_admin, admin, user, guest")
