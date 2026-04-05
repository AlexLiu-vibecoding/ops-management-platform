"""
默认通知通道测试
"""
import pytest
from fastapi.testclient import TestClient


class TestDefaultChannel:
    """测试默认通知通道功能"""
    
    @pytest.fixture(autouse=True)
    def setup_test_channel(self, db_session):
        """设置测试通道"""
        from app.models.notification_new import NotificationChannel
        from app.models import GlobalConfig

        # 确保有测试通道
        channel = db_session.query(NotificationChannel).filter_by(name="Alex-test").first()
        if channel:
            self.test_channel_id = channel.id
        else:
            # 创建测试通道
            channel = NotificationChannel(
                name="DefaultTest",
                channel_type="dingtalk",
                config={"webhook": "https://oapi.dingtalk.com/robot/send?access_token=test"},
                is_enabled=True,
                description="测试默认通道"
            )
            db_session.add(channel)
            db_session.commit()
            db_session.refresh(channel)
            self.test_channel_id = channel.id

        # 确保有默认通道配置
        config = db_session.query(GlobalConfig).filter_by(config_key="default_notification_channel_id").first()
        if config:
            config.config_value = str(self.test_channel_id)
        else:
            config = GlobalConfig(
                config_key="default_notification_channel_id",
                config_value=str(self.test_channel_id),
                description="默认通知通道ID"
            )
            db_session.add(config)
        db_session.commit()
        
        yield self.test_channel_id
    
    def test_get_default_channel(self, client, auth_headers):
        """测试获取默认通道"""
        response = client.get(
            "/api/v1/notification/channels/default",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] is not None
        assert "id" in data["data"]
        assert "name" in data["data"]
        assert "channel_type" in data["data"]
    
    def test_get_default_channel_without_config(self, client, auth_headers, db_session):
        """测试获取默认通道 - 无配置"""
        # 临时删除配置
        from app.models import GlobalConfig
        db_session.query(GlobalConfig).filter_by(config_key="default_notification_channel_id").delete()
        db_session.commit()
        
        response = client.get(
            "/api/v1/notification/channels/default",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] is None
        assert "未设置默认通道" in data["message"]
    
    def test_set_default_channel(self, client, admin_headers, db_session, setup_test_channel):
        """测试设置默认通道"""
        # 获取所有通道
        channels_response = client.get(
            "/api/v1/notification/channels",
            headers=admin_headers
        )
        channels_data = channels_response.json()

        if len(channels_data["items"]) > 0:
            # 设置第一个通道为默认
            first_channel = channels_data["items"][0]
            response = client.post(
                f"/api/v1/notification/channels/default/{first_channel['id']}",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "已将" in data["message"]
            assert data["data"]["channel_id"] == first_channel["id"]

    def test_set_default_channel_not_exist(self, client, admin_headers):
        """测试设置默认通道 - 通道不存在"""
        response = client.post(
            "/api/v1/notification/channels/default/99999",
            headers=admin_headers
        )

        assert response.status_code == 404
        assert "通道不存在" in response.json()["message"]

    def test_set_default_channel_disabled(self, client, admin_headers, db_session):
        """测试设置默认通道 - 通道未启用"""
        from app.models.notification_new import NotificationChannel

        # 创建未启用的通道
        disabled_channel = NotificationChannel(
            name="DisabledChannel",
            channel_type="dingtalk",
            config={"webhook": "https://oapi.dingtalk.com/robot/send?access_token=test"},
            is_enabled=False,
            description="未启用的通道"
        )
        db_session.add(disabled_channel)
        db_session.commit()
        db_session.refresh(disabled_channel)

        response = client.post(
            f"/api/v1/notification/channels/default/{disabled_channel.id}",
            headers=admin_headers
        )

        assert response.status_code == 400
        assert "通道未启用" in response.json()["message"]
    
    def test_default_channel_integration_with_plugin(self, client, auth_headers):
        """测试默认通道与插件系统集成"""
        # 获取默认通道
        default_response = client.get(
            "/api/v1/notification/channels/default",
            headers=auth_headers
        )
        default_data = default_response.json()

        if default_data["success"] and default_data["data"]:
            default_channel = default_data["data"]

            # 获取插件列表
            plugins_response = client.get(
                "/api/v1/notification/plugins",
                headers=auth_headers
            )
            plugins_data = plugins_response.json()

            # 验证默认通道类型对应的插件是否存在
            channel_type = default_channel["channel_type"]
            plugin_types = [p["channel_type"] for p in plugins_data["data"]]

            assert channel_type in plugin_types, f"通道类型 {channel_type} 对应的插件不存在"

    def test_preserve_existing_data(self, client, auth_headers, db_session):
        """测试保留原有数据"""
        from app.models.notification_new import NotificationChannel

        # 获取设置前的通道数量
        channels_before = db_session.query(NotificationChannel).count()

        # 设置默认通道
        channels_response = client.get(
            "/api/v1/notification/channels",
            headers=auth_headers
        )
        channels_data = channels_response.json()

        if len(channels_data["items"]) > 0:
            first_channel = channels_data["items"][0]
            client.post(
                f"/api/v1/notification/channels/default/{first_channel['id']}",
                headers=auth_headers
            )

        # 获取设置后的通道数量
        channels_after = db_session.query(NotificationChannel).count()

        # 验证数据没有丢失
        assert channels_after >= channels_before, "原有通道数据丢失"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
