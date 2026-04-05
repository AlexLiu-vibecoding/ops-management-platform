"""
通知插件API接口

提供插件管理的RESTful API。
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from pydantic import BaseModel

from app.plugins.notification.manager import notification_plugin_manager
from app.plugins.notification.base import NotificationMessage
from app.deps import get_current_user


router = APIRouter(prefix="/notification/plugins", tags=["通知插件管理"])


class PluginConfig(BaseModel):
    """插件配置"""
    channel_type: str
    config: Dict[str, Any]


class NotificationRequest(BaseModel):
    """发送通知请求"""
    channel_type: str
    config: Dict[str, Any]
    title: str
    content: str
    markdown: bool = True
    at_users: List[str] = []


@router.get("")
async def list_plugins():
    """列出所有可用的通知插件
    
    返回所有已加载的通知插件信息。
    """
    plugins = notification_plugin_manager.list_plugins()
    return {
        "success": True,
        "data": plugins,
        "total": len(plugins)
    }


@router.get("/{channel_type}")
async def get_plugin_info(channel_type: str):
    """获取指定插件的详细信息
    
    Args:
        channel_type: 通道类型
    
    Returns:
        插件详细信息
    """
    plugin = notification_plugin_manager.get_plugin(channel_type)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {channel_type} not found")
    
    return {
        "success": True,
        "data": plugin.to_dict()
    }


@router.get("/{channel_type}/schema")
async def get_plugin_schema(channel_type: str):
    """获取插件的配置schema
    
    用于前端动态生成配置表单。
    
    Args:
        channel_type: 通道类型
    
    Returns:
        配置schema
    """
    plugin = notification_plugin_manager.get_plugin(channel_type)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {channel_type} not found")
    
    return {
        "success": True,
        "data": {
            "channel_type": plugin.channel_type,
            "display_name": plugin.display_name,
            "description": plugin.description,
            "config_schema": plugin.config_schema
        }
    }


@router.post("/validate")
async def validate_plugin_config(request: PluginConfig):
    """验证插件配置
    
    Args:
        request: 插件配置请求
    
    Returns:
        验证结果
    """
    if not notification_plugin_manager.plugin_exists(request.channel_type):
        raise HTTPException(status_code=404, detail=f"Plugin {request.channel_type} not found")
    
    is_valid = await notification_plugin_manager.validate_config(
        request.channel_type,
        request.config
    )
    
    return {
        "success": True,
        "data": {
            "valid": is_valid,
            "message": "配置有效" if is_valid else "配置无效"
        }
    }


@router.post("/test")
async def test_plugin_connection(request: PluginConfig):
    """测试插件连接
    
    Args:
        request: 插件配置请求
    
    Returns:
        测试结果
    """
    if not notification_plugin_manager.plugin_exists(request.channel_type):
        raise HTTPException(status_code=404, detail=f"Plugin {request.channel_type} not found")
    
    # 先验证配置
    is_valid = await notification_plugin_manager.validate_config(
        request.channel_type,
        request.config
    )
    
    if not is_valid:
        return {
            "success": False,
            "message": "配置无效，无法测试连接"
        }
    
    # 测试连接
    is_connected = await notification_plugin_manager.test_connection(
        request.channel_type,
        request.config
    )
    
    return {
        "success": True,
        "data": {
            "connected": is_connected,
            "message": "连接成功" if is_connected else "连接失败"
        }
    }


@router.post("/send")
async def send_notification(request: NotificationRequest):
    """发送通知
    
    Args:
        request: 发送通知请求
    
    Returns:
        发送结果
    """
    if not notification_plugin_manager.plugin_exists(request.channel_type):
        raise HTTPException(status_code=404, detail=f"Plugin {request.channel_type} not found")
    
    # 构建消息
    message = NotificationMessage(
        title=request.title,
        content=request.content,
        markdown=request.markdown,
        at_users=request.at_users if request.at_users else None
    )
    
    # 发送消息
    result = await notification_plugin_manager.send_message(
        request.channel_type,
        request.config,
        message
    )
    
    return {
        "success": result.success,
        "data": result.to_dict()
    }


@router.post("/reload")
async def reload_plugin(channel_type: str):
    """重新加载插件
    
    用于开发调试，重新加载指定插件。
    
    Args:
        channel_type: 通道类型
    
    Returns:
        重载结果
    """
    if not notification_plugin_manager.plugin_exists(channel_type):
        raise HTTPException(status_code=404, detail=f"Plugin {channel_type} not found")
    
    is_reloaded = notification_plugin_manager.reload_plugin(channel_type)
    
    return {
        "success": is_reloaded,
        "message": "插件已重新加载" if is_reloaded else "插件重新加载失败"
    }


@router.get("/discover")
async def discover_plugins():
    """重新发现并加载插件
    
    扫描插件目录，发现并加载新的插件。
    
    Returns:
        发现结果
    """
    loaded_count = notification_plugin_manager.discover_plugins()
    
    return {
        "success": True,
        "message": f"成功加载 {loaded_count} 个插件",
        "data": {
            "loaded_count": loaded_count,
            "total_plugins": len(notification_plugin_manager.list_plugins())
        }
    }
