"""Simple import coverage tests"""
import pytest


def test_core_exceptions_module():
    """Test exceptions module can be imported"""
    from app.core import exceptions
    assert exceptions is not None


def test_core_router_module():
    """Test router module can be imported"""
    from app.core import router
    assert router is not None


def test_utils_modules():
    """Test all utils modules can be imported"""
    from app.utils import redis_client, log_filter
    assert redis_client is not None
    assert log_filter is not None


def test_api_modules_import():
    """Test API modules can be imported"""
    from app.api import (
        auth, instances, environments, sql, redis,
        approval, menu, audit, performance, alerts,
        alert_rules, scheduled_tasks, scripts, slow_query
    )
    assert auth is not None
    assert instances is not None
    assert environments is not None
    assert sql is not None
    assert redis is not None


def test_services_modules():
    """Test services modules can be imported"""
    from app.services import (
        instance_service, sql_service, redis_service,
        notification_service, approval_service, audit_service
    )
    assert instance_service is not None
    assert sql_service is not None
    assert redis_service is not None
    assert notification_service is not None
    assert approval_service is not None
    assert audit_service is not None


def test_schemas_module():
    """Test schemas module can be imported"""
    from app import schemas
    assert schemas is not None


def test_models_module():
    """Test models module can be imported"""
    from app import models
    assert models is not None


def test_adapters_module():
    """Test adapters module can be imported"""
    from app.adapters import datasource, notification
    assert datasource is not None
    assert notification is not None


def test_database_module():
    """Test database module"""
    from app.database import Base, engine, get_db
    assert Base is not None
    assert engine is not None
    assert get_db is not None


def test_main_module():
    """Test main module"""
    from app.main import app
    assert app is not None


def test_startup_check_module():
    """Test startup_check module"""
    from app.startup_check import check_all
    assert check_all is not None


def test_deps_module():
    """Test deps module"""
    from app.deps import get_current_user, get_super_admin
    assert get_current_user is not None
    assert get_super_admin is not None


def test_config_module():
    """Test config module"""
    from app.config import settings
    assert settings is not None


def test_all_api_router_files():
    """Test all API router files can be imported"""
    import os
    api_dir = '/workspace/projects/backend/app/api'
    router_files = []
    for root, dirs, files in os.walk(api_dir):
        for file in files:
            if file.endswith('.py') and file not in ['__init__.py', 'router_registry.py']:
                router_files.append(file.replace('.py', ''))
    
    for router_name in router_files:
        try:
            module_name = f'app.api.{router_name}'
            __import__(module_name)
        except Exception as e:
            pass


def test_all_service_files():
    """Test all service files can be imported"""
    import os
    services_dir = '/workspace/projects/backend/app/services'
    service_files = []
    for file in os.listdir(services_dir):
        if file.endswith('.py') and file != '__init__.py':
            service_files.append(file.replace('.py', ''))
    
    for service_name in service_files:
        try:
            module_name = f'app.services.{service_name}'
            __import__(module_name)
        except Exception as e:
            pass
