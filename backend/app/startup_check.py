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
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
    
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
    
    def run_all_checks(self) -> Tuple[bool, List[str], List[str], List[str]]:
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
