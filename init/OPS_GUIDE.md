# OpsCenter 管理脚本使用指南

OpsCenter 提供统一的 `ops.sh` 脚本，用于管理项目的开发、构建、部署和服务管理。

## 快速开始

### 开发模式

```bash
# 启动开发模式（热重载）
./ops.sh dev
```

### 生产模式

```bash
# 启动生产模式
./ops.sh start

# 重新构建并启动
./ops.sh start --build
```

## 命令参考

### 服务管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `dev` | 启动开发模式（热重载） | `./ops.sh dev` |
| `start` | 启动生产模式 | `./ops.sh start --build` |
| `stop` | 停止服务 | `./ops.sh stop` |
| `restart` | 重启服务 | `./ops.sh restart` |
| `logs` | 查看日志 | `./ops.sh logs` |

### 构建与依赖

| 命令 | 说明 | 示例 |
|------|------|------|
| `build` | 构建前端 | `./ops.sh build` |
| `install` | 安装所有依赖 | `./ops.sh install` |

### 部署管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `check` | 检查更新 | `./ops.sh check` |
| `deploy` | 部署 | `./ops.sh deploy --force` |
| `reload` | 重载服务 | `./ops.sh reload --hard` |
| `rollback` | 回滚版本 | `./ops.sh rollback v1.0.0_20240101_120000` |

### 信息查询

| 命令 | 说明 | 示例 |
|------|------|------|
| `status` | 查看服务状态 | `./ops.sh status` |
| `history` | 查看部署历史 | `./ops.sh history` |
| `help` | 显示帮助信息 | `./ops.sh help` |

## 常见场景

### 1. 本地开发

```bash
# 启动开发环境
./ops.sh dev

# 在另一个终端查看日志
./ops.sh logs
```

### 2. 生产部署

```bash
# 检查是否有更新
./ops.sh check

# 部署到生产环境
./ops.sh deploy

# 强制重新部署
./ops.sh deploy --force
```

### 3. 版本回滚

```bash
# 查看可回滚的版本
./ops.sh rollback

# 回滚到指定版本
./ops.sh rollback v1.0.0_20240101_120000
```

### 4. 构建前端

```bash
# 构建前端
./ops.sh build

# 生产模式启动（会自动构建）
./ops.sh start
```

## 环境配置

脚本会根据 Git 分支自动选择环境：

- `main` 或 `master` 分支 → 生产环境 (prod)
- 其他分支 → 开发环境 (dev)

也可以手动指定：

```bash
./ops.sh deploy --env=prod
```

## 日志文件

- 应用日志：`logs/app.log`
- 部署状态：`.deploy.json`
- 进程 PID：`.app.pid`

## 故障排查

### 服务启动失败

1. 检查日志：
   ```bash
   ./ops.sh logs
   ```

2. 检查端口占用：
   ```bash
   ss -lptn 'sport = :5000'
   ```

3. 强制重启：
   ```bash
   ./ops.sh stop
   ./ops.sh start
   ```

### 依赖安装失败

```bash
# 清理后重新安装
rm -rf backend/__pycache__ frontend/node_modules
./ops.sh install
```

### 部署失败

1. 查看部署历史：
   ```bash
   ./ops.sh history
   ```

2. 回滚到上一个版本：
   ```bash
   ./ops.sh rollback
   ```

## 更多帮助

```bash
# 查看完整帮助信息
./ops.sh help
```
