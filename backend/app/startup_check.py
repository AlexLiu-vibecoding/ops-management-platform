"""
启动自检模块
在应用启动前检查所有依赖和配置是否正确
"""
import sys
import os
from typing import List, Tuple
from pathlib import Path


class StartupCheck:
    """启动检查器"""
    
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passed: list[str] = []
    
    def check_python_version(self) -> bool:
        """检查 Python 版本"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 11:
            self.passed.append(f"Python 版本: {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            self.errors.append(f"Python 版本过低: {version.major}.{version.minor}.{version.micro}, 需要 >= 3.11")
            return False
    
    def check_dependencies(self) -> bool:
        """检查必要的依赖包"""
        required_packages = [
            ("fastapi", "FastAPI"),
            ("uvicorn", "Uvicorn"),
            ("sqlalchemy", "SQLAlchemy"),
            ("pydantic", "Pydantic"),
            ("pydantic_settings", "Pydantic Settings"),
            ("pymysql", "PyMySQL"),
            ("psycopg2", "psycopg2"),
            ("redis", "Redis"),
            ("aiohttp", "AIOHTTP"),
            ("httpx", "HTTPX"),
            ("jose", "python-jose"),
            ("passlib", "Passlib"),
            ("apscheduler", "APScheduler"),
            ("openai", "OpenAI"),
            ("sqlparse", "SQLParse"),
            ("dbutils", "DBUtils"),
            ("boto3", "Boto3"),
        ]
        
        all_ok = True
        for module_name, display_name in required_packages:
            try:
                __import__(module_name)
                self.passed.append(f"依赖包: {display_name}")
            except ImportError:
                self.errors.append(f"缺少依赖包: {display_name} (pip install {module_name})")
                all_ok = False
        
        return all_ok
    
    def check_pydantic_version(self) -> bool:
        """检查 Pydantic 版本兼容性"""
        try:
            import pydantic
            import pydantic_core
            
            pydantic_version = pydantic.__version__
            core_version = pydantic_core.__version__
            
            # 检查版本是否兼容 (pydantic 2.5+ ~ 2.8)
            major, minor = map(int, pydantic_version.split('.')[:2])
            if major == 2 and 5 <= minor <= 8:
                self.passed.append(f"Pydantic 版本兼容: {pydantic_version} (core: {core_version})")
                return True
            else:
                self.warnings.append(f"Pydantic 版本可能不兼容: {pydantic_version}, 建议使用 2.5.x - 2.7.x")
                return True
        except Exception as e:
            self.errors.append(f"检查 Pydantic 版本失败: {e}")
            return False
    
    def check_fastapi_pydantic_compat(self) -> bool:
        """检查 FastAPI 和 Pydantic 版本兼容性"""
        try:
            import fastapi
            import pydantic
            
            fastapi_version = fastapi.__version__
            pydantic_version = pydantic.__version__
            
            # FastAPI 0.109+ 需要 Pydantic 2.5+
            fmajor, fminor = map(int, fastapi_version.split('.')[:2])
            pmajor, pminor = map(int, pydantic_version.split('.')[:2])
            
            if fmajor == 0 and fminor >= 109:
                if pmajor == 2 and pminor >= 5:
                    self.passed.append(f"FastAPI {fastapi_version} + Pydantic {pydantic_version} 兼容")
                    return True
                else:
                    self.errors.append(f"FastAPI {fastapi_version} 需要 Pydantic >= 2.5, 当前: {pydantic_version}")
                    return False
            return True
        except Exception as e:
            self.errors.append(f"检查 FastAPI/Pydantic 兼容性失败: {e}")
            return False
    
    def check_database_url(self) -> bool:
        """检查数据库连接配置"""
        db_url = os.getenv("DATABASE_URL") or os.getenv("PGDATABASE_URL")
        if db_url:
            # 隐藏密码
            if "@" in db_url:
                parts = db_url.split("@")
                safe_url = parts[0].rsplit(":", 1)[0] + ":***@" + parts[1]
            else:
                safe_url = db_url[:50] + "..."
            self.passed.append(f"数据库配置: {safe_url[:60]}...")
            return True
        else:
            self.errors.append("未配置数据库连接 (DATABASE_URL 或 PGDATABASE_URL)")
            return False
    
    def check_redis_config(self) -> bool:
        """检查 Redis 配置"""
        redis_host = os.getenv("REDIS_HOST")
        if redis_host:
            self.passed.append(f"Redis 配置: {redis_host}")
            return True
        else:
            self.warnings.append("未配置 Redis, 部分功能可能不可用")
            return True
    
    def check_frontend_build(self) -> bool:
        """检查前端构建产物"""
        # 检查多个可能的前端目录
        possible_paths = [
            Path(__file__).parent.parent.parent / "frontend" / "dist",
            Path(__file__).parent.parent.parent / "dist",
            Path("/workspace/projects/frontend/dist"),
        ]
        
        for frontend_path in possible_paths:
            if frontend_path.exists() and (frontend_path / "index.html").exists():
                self.passed.append(f"前端构建产物: {frontend_path}")
                return True
        
        self.warnings.append("前端构建产物不存在, 请先执行: cd frontend && pnpm build")
        return True
    
    def check_imports(self) -> bool:
        """检查核心模块能否正常导入"""
        try:
            # 尝试导入核心模块
            from app.config import settings
            from app.database import engine, Base
            self.passed.append("核心模块导入: config, database")
            
            # 检查是否能创建 FastAPI 应用
            from fastapi import FastAPI
            self.passed.append("FastAPI 应用创建: OK")
            return True
        except ImportError as e:
            self.errors.append(f"核心模块导入失败: {e}")
            return False
        except Exception as e:
            self.errors.append(f"模块检查失败: {e}")
            return False
    
    def check_security_keys(self) -> bool:
        """检查安全密钥配置"""
        try:
            from app.database import SessionLocal
            from app.models.key_rotation import KeyRotationKey, JWTRotationKey, KeyRotationConfig, JWTRotationConfig
            
            db = SessionLocal()
            
            # 检查 JWT 密钥
            jwt_keys = db.query(JWTRotationKey).all()
            jwt_versions = [k.key_id for k in jwt_keys]
            jwt_has_multiple = len(jwt_keys) > 1 or (len(jwt_keys) == 1 and jwt_keys[0].key_id != 'v1')
            
            if jwt_has_multiple:
                self.passed.append(f"JWT 密钥: 轮换系统已配置 {len(jwt_keys)} 个版本")
            elif len(jwt_keys) == 1 and jwt_keys[0].key_value.startswith('dev-'):
                self.warnings.append("JWT 密钥使用开发默认值，建议执行密钥轮换")
            else:
                self.passed.append("JWT 密钥: 已配置")
            
            # 检查 AES 密钥
            aes_keys = db.query(KeyRotationKey).all()
            aes_has_multiple = len(aes_keys) > 1 or (len(aes_keys) == 1 and aes_keys[0].key_id != 'v1')
            
            if aes_has_multiple:
                self.passed.append(f"AES 密钥: 轮换系统已配置 {len(aes_keys)} 个版本")
            elif len(aes_keys) == 1 and aes_keys[0].key_value.startswith('dev-'):
                self.warnings.append("AES 密钥使用开发默认值，建议执行密钥轮换")
            else:
                self.passed.append("AES 密钥: 已配置")
            
            db.close()
            return True
        except Exception as e:
            self.warnings.append(f"安全密钥检查跳过: {e}")
            return True
    
    def check_key_rotation_system(self) -> bool:
        """检查密钥轮换系统"""
        try:
            from app.database import SessionLocal
            from app.models.key_rotation import KeyRotationKey, JWTRotationKey, KeyRotationConfig, JWTRotationConfig
            
            db = SessionLocal()
            
            # 检查 AES 密钥轮换
            aes_keys = db.query(KeyRotationKey).all()
            aes_config = db.query(KeyRotationConfig).first()
            if aes_keys:
                current_aes = aes_config.current_key_id if aes_config else None
                self.passed.append(f"AES 密钥轮换: {len(aes_keys)} 个版本，当前 {current_aes}")
            else:
                self.warnings.append("AES 密钥轮换: 尚未初始化")
            
            # 检查 JWT 密钥轮换
            jwt_keys = db.query(JWTRotationKey).all()
            jwt_config = db.query(JWTRotationConfig).first()
            if jwt_keys:
                current_jwt = jwt_config.current_key_id if jwt_config else None
                self.passed.append(f"JWT 密钥轮换: {len(jwt_keys)} 个版本，当前 {current_jwt}")
            else:
                self.warnings.append("JWT 密钥轮换: 尚未初始化")
            
            db.close()
            return True
        except Exception as e:
            self.warnings.append(f"密钥轮换系统检查跳过: {e}")
            return True
    
    def run_all_checks(self) -> tuple[bool, list[str], list[str], list[str]]:
        """运行所有检查"""
        print("\n" + "=" * 60)
        print("  运维管理平台 - 启动自检")
        print("=" * 60 + "\n")
        
        checks = [
            ("Python 版本", self.check_python_version),
            ("依赖包", self.check_dependencies),
            ("Pydantic 版本", self.check_pydantic_version),
            ("FastAPI/Pydantic 兼容性", self.check_fastapi_pydantic_compat),
            ("数据库配置", self.check_database_url),
            ("Redis 配置", self.check_redis_config),
            ("前端构建", self.check_frontend_build),
            ("模块导入", self.check_imports),
            ("安全密钥", self.check_security_keys),
            ("密钥轮换系统", self.check_key_rotation_system),
        ]
        
        for name, check_func in checks:
            try:
                check_func()
            except Exception as e:
                self.errors.append(f"{name}: 检查异常 - {e}")
        
        # 输出结果
        print("【通过项】")
        for item in self.passed:
            print(f"  ✓ {item}")
        
        if self.warnings:
            print("\n【警告项】")
            for item in self.warnings:
                print(f"  ⚠ {item}")
        
        if self.errors:
            print("\n【错误项】")
            for item in self.errors:
                print(f"  ✗ {item}")
        
        print("\n" + "-" * 60)
        
        if self.errors:
            print(f"自检失败: {len(self.errors)} 个错误, {len(self.warnings)} 个警告")
            print("-" * 60 + "\n")
            return False, self.errors, self.warnings, self.passed
        else:
            print(f"自检通过: {len(self.passed)} 项检查通过, {len(self.warnings)} 个警告")
            print("-" * 60 + "\n")
            return True, self.errors, self.warnings, self.passed


def run_startup_check() -> bool:
    """
    运行启动检查
    返回 True 表示可以启动，False 表示有严重错误
    """
    checker = StartupCheck()
    success, errors, warnings, passed = checker.run_all_checks()
    
    if not success:
        print("\n请修复上述错误后重新启动服务！")
        print("常见问题解决方法:")
        print("  1. 缺少依赖: pip install -r backend/requirements.txt")
        print("  2. Pydantic 版本冲突: pip install pydantic==2.7.4 pydantic-core==2.18.4 pydantic-settings==2.3.4")
        print("  3. 前端未构建: cd frontend && pnpm install && pnpm build")
        print("  4. 数据库未配置: 设置环境变量 DATABASE_URL 或 PGDATABASE_URL")
        print("")
        return False
    
    return True


if __name__ == "__main__":
    # 直接运行此模块进行检查
    success = run_startup_check()
    sys.exit(0 if success else 1)
