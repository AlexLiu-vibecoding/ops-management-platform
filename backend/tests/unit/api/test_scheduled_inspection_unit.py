"""
定时巡检API测试
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime


class TestScheduledInspectionSchemas:
    """测试定时巡检Schema"""
    
    def test_create_fields(self):
        """测试创建Schema字段"""
        from app.api.scheduled_inspection import ScheduledInspectionCreate
        
        fields = ScheduledInspectionCreate.model_fields
        assert 'name' in fields
        assert 'description' in fields
        assert 'instance_scope' in fields
        assert 'instance_ids' in fields
        assert 'modules' in fields
        assert 'cron_expression' in fields
        assert 'timezone' in fields
    
    def test_create_defaults(self):
        """测试创建默认值"""
        from app.api.scheduled_inspection import ScheduledInspectionCreate
        
        field = ScheduledInspectionCreate.model_fields['instance_scope']
        assert field.default == "all"
        
        field = ScheduledInspectionCreate.model_fields['timezone']
        assert field.default == "Asia/Shanghai"
        
        field = ScheduledInspectionCreate.model_fields['notify_on_complete']
        assert field.default is True
    
    def test_update_fields(self):
        """测试更新Schema字段"""
        from app.api.scheduled_inspection import ScheduledInspectionUpdate
        
        fields = ScheduledInspectionUpdate.model_fields
        assert 'name' in fields
        assert 'status' in fields
        assert 'cron_expression' in fields
    
    def test_validate_cron_response_fields(self):
        """测试Cron验证响应字段"""
        from app.api.scheduled_inspection import ValidateCronResponse
        
        fields = ValidateCronResponse.model_fields
        assert 'valid' in fields
        assert 'error' in fields
        assert 'next_times' in fields


class TestScheduledInspectionRouter:
    """测试路由"""
    
    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.scheduled_inspection import router
        
        assert router.prefix == "/scheduled-inspections"
    
    def test_router_tags(self):
        """测试路由标签"""
        from app.api.scheduled_inspection import router
        
        assert "定时巡检" in router.tags


class TestScheduledInspectionCreate:
    """测试创建巡检任务"""
    
    def test_create_all_instances(self):
        """测试创建扫描所有实例的任务"""
        from app.api.scheduled_inspection import ScheduledInspectionCreate
        
        task = ScheduledInspectionCreate(
            name="每日巡检",
            description="每日数据库巡检",
            instance_scope="all",
            cron_expression="0 2 * * *"
        )
        
        assert task.name == "每日巡检"
        assert task.instance_scope == "all"
        assert task.cron_expression == "0 2 * * *"
    
    def test_create_selected_instances(self):
        """测试创建扫描指定实例的任务"""
        from app.api.scheduled_inspection import ScheduledInspectionCreate
        
        task = ScheduledInspectionCreate(
            name="指定实例巡检",
            instance_scope="selected",
            instance_ids=[1, 2, 3],
            cron_expression="0 3 * * *"
        )
        
        assert task.instance_scope == "selected"
        assert len(task.instance_ids) == 3
    
    def test_create_with_modules(self):
        """测试创建带模块的任务"""
        from app.api.scheduled_inspection import ScheduledInspectionCreate
        
        task = ScheduledInspectionCreate(
            name="模块巡检",
            cron_expression="0 4 * * *",
            modules=["cpu", "memory", "disk"]
        )
        
        assert "cpu" in task.modules
        assert "memory" in task.modules
    
    def test_create_with_timezone(self):
        """测试创建带时区的任务"""
        from app.api.scheduled_inspection import ScheduledInspectionCreate
        
        task = ScheduledInspectionCreate(
            name="UTC巡检",
            cron_expression="0 0 * * *",
            timezone="UTC"
        )
        
        assert task.timezone == "UTC"


class TestScheduledInspectionUpdate:
    """测试更新巡检任务"""
    
    def test_update_name(self):
        """测试更新名称"""
        from app.api.scheduled_inspection import ScheduledInspectionUpdate
        
        update = ScheduledInspectionUpdate(name="新名称")
        assert update.name == "新名称"
    
    def test_update_status(self):
        """测试更新状态"""
        from app.api.scheduled_inspection import ScheduledInspectionUpdate
        
        update = ScheduledInspectionUpdate(status="disabled")
        assert update.status == "disabled"
    
    def test_update_cron(self):
        """测试更新Cron表达式"""
        from app.api.scheduled_inspection import ScheduledInspectionUpdate
        
        update = ScheduledInspectionUpdate(cron_expression="0 5 * * *")
        assert update.cron_expression == "0 5 * * *"


class TestValidateCronResponse:
    """测试Cron验证响应"""
    
    def test_valid_cron(self):
        """测试有效Cron"""
        from app.api.scheduled_inspection import ValidateCronResponse
        
        response = ValidateCronResponse(
            valid=True,
            next_times=["2024-01-01 02:00", "2024-01-02 02:00"]
        )
        
        assert response.valid is True
        assert len(response.next_times) == 2
    
    def test_invalid_cron(self):
        """测试无效Cron"""
        from app.api.scheduled_inspection import ValidateCronResponse
        
        response = ValidateCronResponse(
            valid=False,
            error="Invalid cron expression"
        )
        
        assert response.valid is False
        assert response.error == "Invalid cron expression"


class TestScheduledInspectionModels:
    """测试巡检模型"""
    
    def test_scheduled_inspection_model(self):
        """测试定时巡检模型"""
        from app.models import ScheduledInspection
        
        assert ScheduledInspection is not None
    
    def test_inspection_execution_model(self):
        """测试巡检执行记录模型"""
        from app.models import InspectionExecution
        
        assert InspectionExecution is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
