# MySQL 管理平台 - 问题记录

## 问题 #1: Token 过期后未自动清除

### 现象
- 用户登录后，Token 过期（2小时）后刷新页面
- 页面显示"登录已过期，请重新登录"和"用户名或密码错误"
- 需要手动清除浏览器缓存才能重新登录

### 原因分析
1. **Token 过期时间**: 后端设置 `ACCESS_TOKEN_EXPIRE_HOURS = 2`（2小时）
2. **前端检查逻辑缺陷**: 
   - 原代码只检查 `!!token.value`（token 是否存在）
   - 没有检查 token 是否已过期
   - 即使 token 过期，`isLoggedIn` 仍返回 `true`
3. **页面加载时未清理**: localStorage 中过期的 token 不会被自动清除

### 解决方案（已实施）
修改 `frontend/src/stores/user.js`：

```javascript
// 新增：解析 JWT Token
function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
    }).join(''))
    return JSON.parse(jsonPayload)
  } catch (e) {
    return null
  }
}

// 新增：检查 Token 是否过期
function isTokenExpired(token) {
  if (!token) return true
  const payload = parseJwt(token)
  if (!payload || !payload.exp) return true
  return Date.now() >= payload.exp * 1000
}

// 新增：页面加载时清除过期 token
clearExpiredAuth()

// 修改：isLoggedIn 计算属性
const isLoggedIn = computed(() => {
  if (!token.value) return false
  return !isTokenExpired(token.value)  // 检查是否过期
})
```

### 效果
- ✅ 页面加载时自动检查 token 是否过期
- ✅ 过期 token 自动清除
- ✅ 用户被正确重定向到登录页
- ✅ 不再需要手动清除浏览器缓存

---

## 配置说明

### Token 过期时间
- 文件: `backend/app/config.py`
- 配置: `ACCESS_TOKEN_EXPIRE_HOURS: int = 2`
- 默认值: 2 小时

### 如需修改过期时间
```python
# 方式1: 修改代码默认值
ACCESS_TOKEN_EXPIRE_HOURS: int = 8  # 改为 8 小时

# 方式2: 通过环境变量配置
export ACCESS_TOKEN_EXPIRE_HOURS=8
```

---

## 后续优化建议

1. **Token 刷新机制**: 实现 refresh token，在 token 快过期时自动刷新
2. **记住登录状态**: 添加"记住我"选项，延长 token 有效期
3. **Token 黑名单**: 使用 Redis 存储已登出的 token，实现真正的登出
