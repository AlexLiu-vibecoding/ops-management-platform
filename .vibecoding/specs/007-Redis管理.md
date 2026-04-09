# Redis 管理

> 键管理、服务器信息、慢查询日志、客户端监控

---

## 基本信息

- **规格编号**: `SPEC-007`
- **功能名称**: Redis 管理
- **优先级**: P1 (重要功能)
- **状态**: ✅ 已完成

---

## 一、功能概述

### 1.1 支持的模式

| 模式 | 说明 |
|------|------|
| 单机 | Standalone |
| 集群 | Cluster |
| 哨兵 | Sentinel |

### 1.2 核心功能

- 键扫描、查看、编辑、删除
- 服务器信息（INFO）
- 内存使用分析
- 慢查询日志
- 客户端列表
- 配置查看与修改

---

## 二、实现位置

### 2.1 后端

| 文件 | 说明 |
|------|------|
| `backend/app/api/redis.py` | Redis API |
| `backend/app/services/redis_service.py` | Redis 服务 |

### 2.2 前端

| 文件 | 说明 |
|------|------|
| `frontend/src/views/instances/redis-detail.vue` | Redis 实例详情 |

---

## 三、核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/redis/{instance_id}/info` | GET | 服务器信息 |
| `/api/v1/redis/{instance_id}/keys` | GET | 键列表 |
| `/api/v1/redis/{instance_id}/keys/{key}` | GET | 获取键值 |
| `/api/v1/redis/{instance_id}/keys/{key}` | PUT | 设置键值 |
| `/api/v1/redis/{instance_id}/keys/{key}` | DELETE | 删除键 |
| `/api/v1/redis/{instance_id}/slowlog` | GET | 慢查询日志 |
| `/api/v1/redis/{instance_id}/clients` | GET | 客户端列表 |
| `/api/v1/redis/{instance_id}/config` | GET/PUT | 配置管理 |

---

## 四、键类型支持

| 类型 | 说明 |
|------|------|
| String | 字符串 |
| Hash | 哈希表 |
| List | 列表 |
| Set | 集合 |
| ZSet | 有序集合 |

---

## 五、注意事项

- 大键操作可能阻塞，建议使用 SCAN
- 敏感配置修改需要权限
- 集群模式需要处理MOVED重定向

---

## 四、实现位置

### 4.1 后端

| 文件 | 说明 |
|------|------|
| `backend/app/api/redis_instances.py` | Redis 实例 API |
| `backend/app/api/redis.py` | Redis 操作 API |
| `backend/app/models/instances.py` | RedisInstance 模型 |

### 4.2 前端

| 文件 | 说明 |
|------|------|
| `frontend/src/views/instances/index.vue` | 实例列表页面 |
| `frontend/src/views/instances/redis-detail.vue` | Redis 详情页面 |

### 4.3 数据库表

| 表名 | 说明 |
|------|------|
| `redis_instances` | Redis 实例表 |
| `redis_slow_logs` | Redis 慢日志表 |
| `redis_memory_stats` | Redis 内存统计表 |
| `redis_key_analyses` | Redis Key 分析表 |

---

*最后更新：2026-04-09*
*更新内容：添加实现位置*
