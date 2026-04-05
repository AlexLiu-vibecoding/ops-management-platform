"""
通知插件管理器

负责插件的注册、发现、加载和生命周期管理。
"""
import importlib
import inspect
import logging
from pathlib import Path
from typing import Dict, Type, List, Optional
from app.plugins.notification.base import NotificationPlugin, NotificationMessage, NotificationResult

logger = logging.getLogger(__name__)


class NotificationPluginManager:
    """通知插件管理器
    
    管理所有通知插件的注册、发现和调用。
    """
    
    def __init__(self):
        self._plugins: Dict[str, NotificationPlugin] = {}
        self._plugin_classes: Dict[str, Type[NotificationPlugin]] = {}
    
    def register_plugin(self, plugin_class: Type[NotificationPlugin]) -> bool:
        """注册插件
        
        Args:
            plugin_class: 插件类
        
        Returns:
            是否注册成功
        """
        try:
            plugin = plugin_class()
            channel_type = plugin.channel_type
            
            if channel_type in self._plugins:
                logger.warning(f"Plugin {channel_type} already registered, skipping")
                return False
            
            self._plugins[channel_type] = plugin
            self._plugin_classes[channel_type] = plugin_class
            logger.info(f"Registered notification plugin: {channel_type} ({plugin.display_name})")
            return True
        except Exception as e:
            logger.error(f"Failed to register plugin {plugin_class.__name__}: {e}")
            return False
    
    def get_plugin(self, channel_type: str) -> Optional[NotificationPlugin]:
        """获取插件实例
        
        Args:
            channel_type: 通道类型
        
        Returns:
            插件实例，如果不存在则返回None
        """
        return self._plugins.get(channel_type)
    
    def list_plugins(self) -> List[Dict[str, any]]:
        """列出所有插件
        
        Returns:
            插件信息列表
        """
        return [
            plugin.to_dict()
            for plugin in self._plugins.values()
        ]
    
    def plugin_exists(self, channel_type: str) -> bool:
        """检查插件是否存在
        
        Args:
            channel_type: 通道类型
        
        Returns:
            插件是否存在
        """
        return channel_type in self._plugins
    
    async def send_message(
        self,
        channel_type: str,
        config: Dict[str, any],
        message: NotificationMessage
    ) -> NotificationResult:
        """发送消息
        
        Args:
            channel_type: 通道类型
            config: 配置字典
            message: 消息内容
        
        Returns:
            发送结果
        
        Raises:
            ValueError: 如果插件不存在
        """
        plugin = self.get_plugin(channel_type)
        if not plugin:
            return NotificationResult(
                status=NotificationStatus.FAILED,
                channel_type=channel_type,
                message=f"Plugin {channel_type} not found"
            )
        
        try:
            return await plugin.send(config, message)
        except Exception as e:
            logger.error(f"Failed to send message via {channel_type}: {e}")
            return NotificationResult(
                status=NotificationStatus.FAILED,
                channel_type=channel_type,
                message=str(e)
            )
    
    async def validate_config(
        self,
        channel_type: str,
        config: Dict[str, any]
    ) -> bool:
        """验证插件配置
        
        Args:
            channel_type: 通道类型
            config: 配置字典
        
        Returns:
            配置是否有效
        
        Raises:
            ValueError: 如果插件不存在
        """
        plugin = self.get_plugin(channel_type)
        if not plugin:
            raise ValueError(f"Plugin {channel_type} not found")
        
        return await plugin.validate_config(config)
    
    async def test_connection(
        self,
        channel_type: str,
        config: Dict[str, any]
    ) -> bool:
        """测试插件连接
        
        Args:
            channel_type: 通道类型
            config: 配置字典
        
        Returns:
            连接是否成功
        
        Raises:
            ValueError: 如果插件不存在
        """
        plugin = self.get_plugin(channel_type)
        if not plugin:
            raise ValueError(f"Plugin {channel_type} not found")
        
        return await plugin.test_connection(config)
    
    def discover_plugins(self, plugin_dir: str = "app/plugins/notification") -> int:
        """自动发现并加载插件
        
        Args:
            plugin_dir: 插件目录路径
        
        Returns:
            成功加载的插件数量
        """
        plugin_path = Path(plugin_dir)
        if not plugin_path.exists():
            logger.warning(f"Plugin directory {plugin_dir} does not exist")
            return 0
        
        loaded_count = 0
        
        for py_file in plugin_path.glob("*.py"):
            # 跳过以下划线开头的文件和base.py
            if py_file.name.startswith("_") or py_file.name == "base.py":
                continue
            
            module_name = f"app.plugins.notification.{py_file.stem}"
            
            try:
                module = importlib.import_module(module_name)
                
                # 查找插件类
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) 
                        and issubclass(obj, NotificationPlugin) 
                        and obj != NotificationPlugin):
                        if self.register_plugin(obj):
                            loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to load plugin from {module_name}: {e}")
        
        logger.info(f"Discovered and loaded {loaded_count} notification plugins")
        return loaded_count
    
    def reload_plugin(self, channel_type: str) -> bool:
        """重新加载插件
        
        Args:
            channel_type: 通道类型
        
        Returns:
            是否重新加载成功
        """
        if channel_type not in self._plugin_classes:
            logger.warning(f"Plugin {channel_type} not found for reload")
            return False
        
        try:
            plugin_class = self._plugin_classes[channel_type]
            self._plugins[channel_type] = plugin_class()
            logger.info(f"Reloaded plugin: {channel_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to reload plugin {channel_type}: {e}")
            return False
    
    def unregister_plugin(self, channel_type: str) -> bool:
        """注销插件
        
        Args:
            channel_type: 通道类型
        
        Returns:
            是否注销成功
        """
        if channel_type in self._plugins:
            del self._plugins[channel_type]
            if channel_type in self._plugin_classes:
                del self._plugin_classes[channel_type]
            logger.info(f"Unregistered plugin: {channel_type}")
            return True
        return False


# 全局插件管理器实例
notification_plugin_manager = NotificationPluginManager()
