"""
AWS RDS 性能指标采集器
通过 CloudWatch API 获取 RDS 实例的性能指标
"""
import os
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError

logger = logging.getLogger(__name__)


# AWS 区域列表
AWS_REGIONS = {
    # 美国东部
    "us-east-1": "美国东部 (弗吉尼亚北部)",
    "us-east-2": "美国东部 (俄亥俄)",
    # 美国西部
    "us-west-1": "美国西部 (加利福尼亚)",
    "us-west-2": "美国西部 (俄勒冈)",
    # 亚太地区
    "ap-east-1": "亚太地区 (香港)",
    "ap-northeast-1": "亚太地区 (东京)",
    "ap-northeast-2": "亚太地区 (首尔)",
    "ap-northeast-3": "亚太地区 (大阪)",
    "ap-southeast-1": "亚太地区 (新加坡)",
    "ap-southeast-2": "亚太地区 (悉尼)",
    "ap-southeast-3": "亚太地区 (雅加达)",
    "ap-south-1": "亚太地区 (孟买)",
    # 中国
    "cn-north-1": "中国 (北京)",
    "cn-northwest-1": "中国 (宁夏)",
    # 欧洲
    "eu-central-1": "欧洲 (法兰克福)",
    "eu-west-1": "欧洲 (爱尔兰)",
    "eu-west-2": "欧洲 (伦敦)",
    "eu-west-3": "欧洲 (巴黎)",
    "eu-north-1": "欧洲 (斯德哥尔摩)",
    # 南美洲
    "sa-east-1": "南美洲 (圣保罗)",
    # 加拿大
    "ca-central-1": "加拿大 (中部)",
}


def parse_aws_region_from_host(host: str) -> Optional[str]:
    """
    从 RDS endpoint 解析 AWS 区域
    
    AWS RDS endpoint 格式：
    - 国际版: {db-id}.{random-id}.{region}.rds.amazonaws.com
    - 中国版: {db-id}.{random-id}.{region}.rds.amazonaws.com.cn
    
    示例：
    - mydb.c9akciq32.us-east-1.rds.amazonaws.com → us-east-1
    - test-pg.xxxxx.cn-north-1.rds.amazonaws.com.cn → cn-north-1
    - mydb.xxxxx.ap-southeast-1.rds.amazonaws.com → ap-southeast-1
    
    Args:
        host: RDS 实例的主机地址
        
    Returns:
        AWS 区域代码，如果无法解析则返回 None
    """
    if not host:
        return None
    
    # 尝试匹配 RDS endpoint 模式
    # 模式1: 国际版 xxx.region.rds.amazonaws.com
    pattern_intl = r'\.([a-z]{2}-[a-z]+-\d+)\.rds\.amazonaws\.com$'
    match = re.search(pattern_intl, host, re.IGNORECASE)
    
    if match:
        region = match.group(1)
        if region in AWS_REGIONS:
            logger.debug(f"从 host {host} 解析出区域: {region}")
            return region
    
    # 模式2: 中国版 xxx.region.rds.amazonaws.com.cn
    pattern_cn = r'\.([a-z]{2}-[a-z]+-\d+)\.rds\.amazonaws\.com\.cn$'
    match = re.search(pattern_cn, host, re.IGNORECASE)
    
    if match:
        region = match.group(1)
        if region in AWS_REGIONS:
            logger.debug(f"从 host {host} 解析出区域 (中国): {region}")
            return region
    
    # 模式3: 宽松匹配，提取任何看起来像 AWS 区域的部分
    # 格式: xx-xxxx-n (如 us-east-1, ap-southeast-1)
    loose_pattern = r'([a-z]{2}-[a-z]+-\d+)'
    matches = re.findall(loose_pattern, host, re.IGNORECASE)
    
    for region in matches:
        if region in AWS_REGIONS:
            logger.debug(f"从 host {host} 宽松匹配出区域: {region}")
            return region
    
    logger.debug(f"无法从 host {host} 解析 AWS 区域")
    return None


def is_rds_endpoint(host: str) -> bool:
    """
    判断 host 是否为 AWS RDS endpoint
    
    Args:
        host: 主机地址
        
    Returns:
        是否为 RDS endpoint
    """
    if not host:
        return False
    
    rds_patterns = [
        r'\.rds\.amazonaws\.com$',
        r'\.rds\.amazonaws\.com\.cn$',
    ]
    
    for pattern in rds_patterns:
        if re.search(pattern, host, re.IGNORECASE):
            return True
    
    return False


@dataclass
class RDSMetrics:
    """RDS 性能指标数据类"""
    cpu_usage: Optional[float] = None  # CPU 使用率 %
    memory_usage: Optional[float] = None  # 内存使用率 % (计算得出)
    free_memory_mb: Optional[float] = None  # 可用内存 MB
    connections: Optional[int] = None  # 连接数
    qps: Optional[float] = None  # 每秒查询数
    read_iops: Optional[float] = None  # 读 IOPS
    write_iops: Optional[float] = None  # 写 IOPS
    latency: Optional[float] = None  # 延迟 ms
    collect_time: Optional[datetime] = None
    error: Optional[str] = None  # 错误信息


class RDSMetricsCollector:
    """AWS RDS 指标采集器"""
    
    # CloudWatch 指标命名空间
    NAMESPACE_RDS = "AWS/RDS"
    
    # 指标名称映射
    METRICS_CONFIG = {
        "cpu_usage": {
            "metric_name": "CPUUtilization",
            "statistics": ["Average"],
            "unit": "Percent"
        },
        "free_memory": {
            "metric_name": "FreeableMemory",
            "statistics": ["Average"],
            "unit": "Bytes"
        },
        "connections": {
            "metric_name": "DatabaseConnections",
            "statistics": ["Average"],
            "unit": "Count"
        },
        "read_iops": {
            "metric_name": "ReadIOPS",
            "statistics": ["Average"],
            "unit": "Count/Second"
        },
        "write_iops": {
            "metric_name": "WriteIOPS",
            "statistics": ["Average"],
            "unit": "Count/Second"
        },
        "read_latency": {
            "metric_name": "ReadLatency",
            "statistics": ["Average"],
            "unit": "Seconds"
        },
        "write_latency": {
            "metric_name": "WriteLatency",
            "statistics": ["Average"],
            "unit": "Seconds"
        }
    }
    
    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: Optional[str] = None
    ):
        """
        初始化 RDS 指标采集器
        
        Args:
            aws_access_key_id: AWS Access Key ID (可选，默认使用环境变量)
            aws_secret_access_key: AWS Secret Access Key (可选，默认使用环境变量)
            aws_region: AWS 区域 (可选，默认使用环境变量)
        """
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = aws_region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        
        self._cloudwatch_client = None
        self._rds_client = None
    
    def _get_cloudwatch_client(self):
        """获取 CloudWatch 客户端（延迟初始化）"""
        if self._cloudwatch_client is None:
            try:
                session_kwargs = {"region_name": self.aws_region}
                if self.aws_access_key_id and self.aws_secret_access_key:
                    session_kwargs.update({
                        "aws_access_key_id": self.aws_access_key_id,
                        "aws_secret_access_key": self.aws_secret_access_key
                    })
                
                session = boto3.Session(**session_kwargs)
                self._cloudwatch_client = session.client("cloudwatch")
            except Exception as e:
                logger.error(f"Failed to create CloudWatch client: {e}")
                raise
        return self._cloudwatch_client
    
    def _get_rds_client(self):
        """获取 RDS 客户端（延迟初始化）"""
        if self._rds_client is None:
            try:
                session_kwargs = {"region_name": self.aws_region}
                if self.aws_access_key_id and self.aws_secret_access_key:
                    session_kwargs.update({
                        "aws_access_key_id": self.aws_access_key_id,
                        "aws_secret_access_key": self.aws_secret_access_key
                    })
                
                session = boto3.Session(**session_kwargs)
                self._rds_client = session.client("rds")
            except Exception as e:
                logger.error(f"Failed to create RDS client: {e}")
                raise
        return self._rds_client
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试 AWS 连接是否正常
        
        Returns:
            {"success": bool, "message": str}
        """
        try:
            rds = self._get_rds_client()
            # 尝试列出 RDS 实例（限制返回数量）
            rds.describe_db_instances(MaxRecords=1)
            return {"success": True, "message": "AWS RDS 连接成功"}
        except NoCredentialsError:
            return {"success": False, "message": "AWS 凭证未配置，请设置 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY 环境变量"}
        except EndpointConnectionError as e:
            return {"success": False, "message": f"无法连接到 AWS 端点: {str(e)}"}
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "UnauthorizedOperation":
                return {"success": False, "message": "AWS 凭证无权限访问 RDS 服务"}
            elif error_code == "InvalidClientTokenId":
                return {"success": False, "message": "AWS 凭证无效"}
            return {"success": False, "message": f"AWS 错误: {error_code}"}
        except Exception as e:
            return {"success": False, "message": f"连接测试失败: {str(e)}"}
    
    def get_instance_info(self, db_instance_identifier: str) -> Optional[Dict[str, Any]]:
        """
        获取 RDS 实例信息
        
        Args:
            db_instance_identifier: RDS 实例标识符
            
        Returns:
            实例信息字典或 None
        """
        try:
            rds = self._get_rds_client()
            response = rds.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
            
            if response.get("DBInstances"):
                instance = response["DBInstances"][0]
                return {
                    "db_instance_identifier": instance.get("DBInstanceIdentifier"),
                    "db_instance_class": instance.get("DBInstanceClass"),
                    "engine": instance.get("Engine"),
                    "engine_version": instance.get("EngineVersion"),
                    "status": instance.get("DBInstanceStatus"),
                    "allocated_storage": instance.get("AllocatedStorage"),
                    "storage_type": instance.get("StorageType"),
                    "multi_az": instance.get("MultiAZ"),
                    "endpoint": {
                        "address": instance.get("Endpoint", {}).get("Address"),
                        "port": instance.get("Endpoint", {}).get("Port")
                    }
                }
            return None
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "DBInstanceNotFound":
                logger.warning(f"RDS instance not found: {db_instance_identifier}")
            else:
                logger.error(f"Failed to get RDS instance info: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get RDS instance info: {e}")
            return None
    
    def _get_metric_data(
        self,
        db_instance_identifier: str,
        metric_name: str,
        period: int = 300,
        statistics: List[str] = None,
        unit: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> Dict[str, float]:
        """
        获取单个指标的 CloudWatch 数据
        
        Args:
            db_instance_identifier: RDS 实例标识符
            metric_name: 指标名称
            period: 时间间隔（秒），默认 300 (5分钟)
            statistics: 统计类型列表
            unit: 单位
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            指标数据字典 {statistic: value}
        """
        if statistics is None:
            statistics = ["Average"]
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        
        try:
            cw = self._get_cloudwatch_client()
            
            dimensions = [
                {
                    "Name": "DBInstanceIdentifier",
                    "Value": db_instance_identifier
                }
            ]
            
            kwargs = {
                "Namespace": self.NAMESPACE_RDS,
                "MetricName": metric_name,
                "Dimensions": dimensions,
                "StartTime": start_time,
                "EndTime": end_time,
                "Period": period,
                "Statistics": statistics
            }
            
            response = cw.get_metric_statistics(**kwargs)
            
            result = {}
            datapoints = response.get("Datapoints", [])
            
            if datapoints:
                # 按时间排序，取最新的数据点
                datapoints.sort(key=lambda x: x["Timestamp"], reverse=True)
                latest = datapoints[0]
                
                for stat in statistics:
                    if stat in latest:
                        result[stat] = latest[stat]
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get metric {metric_name}: {e}")
            return {}
    
    def collect_metrics(
        self,
        db_instance_identifier: str,
        period_minutes: int = 5
    ) -> RDSMetrics:
        """
        采集 RDS 实例的性能指标
        
        Args:
            db_instance_identifier: RDS 实例标识符
            period_minutes: 采集周期（分钟）
            
        Returns:
            RDSMetrics 对象
        """
        metrics = RDSMetrics(collect_time=datetime.now())
        
        try:
            # 首先测试连接
            conn_test = self.test_connection()
            if not conn_test["success"]:
                metrics.error = conn_test["message"]
                return metrics
            
            # 检查实例是否存在
            instance_info = self.get_instance_info(db_instance_identifier)
            if not instance_info:
                metrics.error = f"RDS 实例 '{db_instance_identifier}' 不存在"
                return metrics
            
            # 检查实例状态
            if instance_info.get("status") != "available":
                metrics.error = f"RDS 实例状态为 '{instance_info.get('status')}'，无法采集指标"
                return metrics
            
            # 获取 CPU 使用率
            cpu_data = self._get_metric_data(
                db_instance_identifier,
                "CPUUtilization",
                period=period_minutes * 60,
                statistics=["Average"]
            )
            if cpu_data:
                metrics.cpu_usage = cpu_data.get("Average")
            
            # 获取可用内存
            memory_data = self._get_metric_data(
                db_instance_identifier,
                "FreeableMemory",
                period=period_minutes * 60,
                statistics=["Average"]
            )
            if memory_data:
                free_memory_bytes = memory_data.get("Average", 0)
                metrics.free_memory_mb = free_memory_bytes / (1024 * 1024) if free_memory_bytes else None
                # 注意：AWS RDS 不直接提供内存使用率，需要根据实例类型估算总内存
                # 这里暂时不计算内存使用率，只显示可用内存
            
            # 获取连接数
            conn_data = self._get_metric_data(
                db_instance_identifier,
                "DatabaseConnections",
                period=period_minutes * 60,
                statistics=["Average"]
            )
            if conn_data:
                metrics.connections = int(conn_data.get("Average", 0))
            
            # 获取 IOPS
            read_iops = self._get_metric_data(
                db_instance_identifier,
                "ReadIOPS",
                period=period_minutes * 60,
                statistics=["Average"]
            )
            if read_iops:
                metrics.read_iops = read_iops.get("Average")
            
            write_iops = self._get_metric_data(
                db_instance_identifier,
                "WriteIOPS",
                period=period_minutes * 60,
                statistics=["Average"]
            )
            if write_iops:
                metrics.write_iops = write_iops.get("Average")
            
            # 计算总 IOPS 作为 QPS 的近似值
            total_iops = 0
            if metrics.read_iops:
                total_iops += metrics.read_iops
            if metrics.write_iops:
                total_iops += metrics.write_iops
            if total_iops > 0:
                metrics.qps = total_iops  # IOPS 作为 QPS 的近似
            
            # 获取延迟
            read_latency = self._get_metric_data(
                db_instance_identifier,
                "ReadLatency",
                period=period_minutes * 60,
                statistics=["Average"]
            )
            write_latency = self._get_metric_data(
                db_instance_identifier,
                "WriteLatency",
                period=period_minutes * 60,
                statistics=["Average"]
            )
            
            read_ms = read_latency.get("Average", 0) * 1000 if read_latency else 0
            write_ms = write_latency.get("Average", 0) * 1000 if write_latency else 0
            if read_ms or write_ms:
                metrics.latency = (read_ms + write_ms) / 2
            
            logger.info(f"Successfully collected metrics for RDS instance: {db_instance_identifier}")
            
        except Exception as e:
            logger.error(f"Failed to collect RDS metrics: {e}")
            metrics.error = str(e)
        
        return metrics
    
    def to_performance_dict(self, metrics: RDSMetrics) -> Dict[str, Any]:
        """
        将 RDSMetrics 转换为性能指标字典格式（用于存储到数据库）
        
        Args:
            metrics: RDSMetrics 对象
            
        Returns:
            性能指标字典
        """
        return {
            "cpu_usage": metrics.cpu_usage,
            "memory_usage": metrics.memory_usage,
            "disk_io_read": metrics.read_iops,
            "disk_io_write": metrics.write_iops,
            "connections": metrics.connections,
            "qps": metrics.qps,
            "latency_ms": metrics.latency,
            "free_memory_mb": metrics.free_memory_mb,
            "collect_time": metrics.collect_time,
            "error": metrics.error
        }


# 全局采集器实例（已废弃，改为按环境动态创建）
_collector_instance: Optional[RDSMetricsCollector] = None

# 环境级别的采集器缓存
_environment_collectors: Dict[int, RDSMetricsCollector] = {}


def get_aws_credentials_from_environment(environment_id: int) -> Optional[dict]:
    """
    从环境配置获取 AWS 凭证
    
    用于 RDS CloudWatch 指标采集
    
    Args:
        environment_id: 环境 ID
        
    Returns:
        包含 aws_access_key_id, aws_secret_access_key, aws_region 的字典
        如果环境未配置 AWS 凭证则返回 None
    """
    try:
        from app.database import SessionLocal
        from app.models import Environment
        from app.utils.auth import decrypt_instance_password
        
        db = SessionLocal()
        try:
            env = db.query(Environment).filter(Environment.id == environment_id).first()
            if not env or not env.aws_configured:
                logger.debug(f"环境 {environment_id} 未配置 AWS 凭证")
                return None
            
            # 解密 AWS Secret Access Key
            secret_key = env.aws_secret_access_key
            if secret_key:
                try:
                    secret_key = decrypt_instance_password(secret_key)
                except Exception:
                    # 如果解密失败，可能是未加密的明文（兼容旧数据）
                    pass
            
            return {
                "aws_access_key_id": env.aws_access_key_id,
                "aws_secret_access_key": secret_key,
                "aws_region": env.aws_region or "us-east-1"
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"从环境 {environment_id} 获取 AWS 凭证失败: {e}")
        return None


def get_rds_collector_for_environment(environment_id: int, aws_region: str = None) -> Optional[RDSMetricsCollector]:
    """
    获取指定环境的 RDS 采集器
    
    根据环境配置的 AWS 凭证创建采集器实例
    
    Args:
        environment_id: 环境 ID
        aws_region: 可选的区域覆盖（如果实例有特定区域）
        
    Returns:
        RDSMetricsCollector 实例，如果环境未配置 AWS 则返回 None
    """
    # 从环境获取凭证
    creds = get_aws_credentials_from_environment(environment_id)
    if not creds:
        return None
    
    # 使用传入的区域覆盖（如实例级别的区域）
    if aws_region:
        creds["aws_region"] = aws_region
    
    # 创建采集器
    return RDSMetricsCollector(
        aws_access_key_id=creds["aws_access_key_id"],
        aws_secret_access_key=creds["aws_secret_access_key"],
        aws_region=creds["aws_region"]
    )


def get_aws_credentials_from_db() -> dict:
    """
    从数据库读取 AWS 凭证配置（已废弃，保留兼容）
    
    注意：此函数现在只用于 S3 存储配置，不用于 RDS 采集
    RDS 采集请使用 get_aws_credentials_from_environment
    
    优先级：数据库配置 > 环境变量
    
    Returns:
        包含 aws_access_key_id, aws_secret_access_key, aws_region 的字典
    """
    credentials = {
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "aws_region": os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    }
    
    try:
        from app.database import SessionLocal
        from app.models import GlobalConfig
        
        db = SessionLocal()
        try:
            # 从数据库读取 AWS 配置（用于 S3 存储）
            config_keys = ["aws_access_key_id", "aws_secret_access_key", "aws_region"]
            
            for key in config_keys:
                config = db.query(GlobalConfig).filter(
                    GlobalConfig.config_key == key
                ).first()
                if config and config.config_value:
                    if key == "aws_access_key_id":
                        credentials["aws_access_key_id"] = config.config_value
                    elif key == "aws_secret_access_key":
                        credentials["aws_secret_access_key"] = config.config_value
                    elif key == "aws_region":
                        credentials["aws_region"] = config.config_value
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"从数据库读取 AWS 凭证失败，使用环境变量: {e}")

    return credentials


def get_rds_collector() -> RDSMetricsCollector:
    """
    获取全局 RDS 采集器实例
    
    自动从数据库或环境变量加载 AWS 凭证
    优先级：数据库配置 > 环境变量
    """
    global _collector_instance
    if _collector_instance is None:
        # 从数据库或环境变量获取凭证
        creds = get_aws_credentials_from_db()
        _collector_instance = RDSMetricsCollector(
            aws_access_key_id=creds["aws_access_key_id"],
            aws_secret_access_key=creds["aws_secret_access_key"],
            aws_region=creds["aws_region"]
        )
        logger.info(f"RDS 采集器已初始化，区域: {creds['aws_region']}")
    return _collector_instance


def reload_rds_collector():
    """
    重新加载 RDS 采集器
    
    当 AWS 凭证配置变更时调用，使新配置生效
    """
    global _collector_instance
    _collector_instance = None
    logger.info("RDS 采集器已重置，下次调用将使用新配置")
    return get_rds_collector()
