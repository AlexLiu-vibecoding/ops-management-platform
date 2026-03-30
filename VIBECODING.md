# VibeCoding 协作经验记录

> 本文档记录 AI 与用户协作开发过程中积累的经验、偏好和注意事项，确保下次开发能直接复用，减少重复沟通和 token 消耗。

---

## 一、开发流程经验

### 1.1 新功能开发流程

```
1. 先讨论方案，确认后再动手写代码
2. 写代码前，先检查现有实现，避免重复造轮子
3. 代码写完后，自动生成/更新对应的测试用例
4. 让用户验证效果，而不是自己假设完成了
```

### 1.2 容易遗漏的事项

| 场景 | 容易遗漏 | 正确做法 |
|------|----------|----------|
| 新增 API | 忘记添加测试用例 | 同步更新 `tests/test_xxx_api.py` |
| 新增菜单 | 忘记更新数据库 | 提供调用 `/api/v1/menu/add-missing` 的提示 |
| 修改前端 | 忘记确认页面效果 | 让用户刷新验证，或截图确认 |
| 新增字段 | 忘记更新 Schema | 同步更新 Pydantic 模型 |

---

## 二、用户开发偏好

### 2.1 代码风格偏好

- **Python**：使用 Ruff 格式化，行宽 120
- **前端**：Vue 3 组合式 API，`<script setup>` 语法
- **表格操作列**：统一使用 `TableActions` 组件
- **筛选区域**：使用 `el-form inline` 布局

### 2.2 工作习惯

- **不要擅自扩展范围**：用户说改什么就改什么，不要自作主张
- **先确认再开发**：不确定的地方先问，不要猜测
- **改完要验证**：让用户确认效果，不要自己认为完成了

### 2.3 不喜欢的事情

- ❌ 用户只问一个问题，AI 却改了一堆代码
- ❌ 没确认需求就开始写代码
- ❌ 代码写完不验证就说完成了
- ❌ 重复问已经确认过的问题

---

## 三、项目特定经验

### 3.1 菜单/路由修改

**新增菜单需要同时修改：**
1. `backend/app/api/menu.py` - 菜单数据
2. `frontend/src/router/index.js` - 路由配置
3. 数据库 - 调用 `/api/v1/menu/add-missing`

**经验教训：**
- 修改后端菜单配置时，`add-missing` API 会删除 `old_paths` 列表中的旧菜单
- 如果只是移动菜单位置，要小心别误删

### 3.2 测试用例

**位置：** `backend/tests/`

**命名规范：**
- `test_xxx_api.py` - API 测试
- `test_xxx_flow.py` - 流程测试

**习惯：** 新增 API 后，用户会提醒添加测试用例

### 3.3 日志位置

```bash
/app/work/logs/bypass/app.log      # 后端主日志
/app/work/logs/bypass/console.log  # 前端控制台日志
/app/work/logs/bypass/dev.log      # 开发环境日志
```

---

## 四、踩坑记录

### 4.1 端口检测

**问题：** `lsof -i:5000` 会检测到所有包含 5000 的连接（包括 50001）

**正确做法：**
```bash
curl -I http://localhost:5000           # 检查 HTTP 响应
ss -tuln | grep -E ':5000[[:space:]]'  # 精准匹配端口
```

### 4.2 文件下载

**问题：** 跨域 URL 的 `<a download>` 属性会被浏览器忽略

**正确做法：**
```javascript
const downloadFile = async (url, filename) => {
  const response = await fetch(url);
  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(blobUrl);
};
```

### 4.3 热更新机制

**前端：** Vite 支持热更新，修改代码后无需重启
**后端：** FastAPI + uvicorn 默认热重载

**经验：** 改完代码让用户刷新页面验证，不要自己重启服务

---

## 五、协作模式总结

### 5.1 高效协作模式

```
用户提问 → AI 确认理解 → 执行修改 → 让用户验证 → 完成
```

### 5.2 低效协作模式（避免）

```
用户提问 → AI 猜测意图 → 擅自扩展 → 改了一堆 → 用户不满意 → 回滚 → 重新沟通
```

### 5.3 沟通原则

1. **一个需求一次确认** - 不要来回问多次
2. **精准回答** - 用户问什么答什么，不要展开太多
3. **主动展示结果** - 改完代码告诉用户改了什么，让用户验证

---

## 六、持续积累

> 本节用于记录新的协作经验，每次遇到新问题后补充

### 待补充...

- [ ] 遇到新问题时记录在这里
- [ ] 用户提醒的新偏好
- [ ] 新的踩坑记录

---

*文档版本：v1.0*
*说明：本文档是动态积累的，遇到新的协作经验时更新*
