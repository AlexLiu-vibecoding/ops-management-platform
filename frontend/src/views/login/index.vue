<template>
  <div class="login-page-ios">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
      <div class="blob blob-3"></div>
    </div>

    <!-- 语言切换 -->
    <div class="lang-switch-wrapper">
      <LangSwitch />
    </div>

    <!-- 主内容 -->
    <div class="login-container">
      <!-- 左侧品牌区 -->
      <div class="brand-section">
        <div class="brand-content">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <h1 class="brand-title">OpsCenter</h1>
          <p class="brand-subtitle">{{ $t('login.subtitle') || '企业级数据库运维管理平台' }}</p>
          
          <div class="features">
            <div class="feature-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <span>{{ $t('feature.multiInstance') || '多实例管理' }}</span>
            </div>
            <div class="feature-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <span>{{ $t('feature.realTime') || '实时监控' }}</span>
            </div>
            <div class="feature-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <span>{{ $t('feature.aiOptimize') || 'AI智能优化' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧表单区 -->
      <div class="form-section">
        <div class="form-wrapper">
          <!-- 登录表单 -->
          <div v-if="!showRegister && !showStatus" class="form-container">
            <h2 class="form-title">{{ $t('login.welcome') || '欢迎回来' }}</h2>
            <p class="form-subtitle">{{ $t('login.loginHint') || '请登录您的账户' }}</p>
            
            <el-form
              ref="loginFormRef"
              :model="loginForm"
              :rules="loginRules"
              class="login-form"
            >
              <el-form-item prop="username">
                <div class="input-wrapper">
                  <label class="input-label">{{ $t('login.username') }}</label>
                  <el-input
                    v-model="loginForm.username"
                    :placeholder="$t('login.usernamePlaceholder') || '请输入用户名'"
                    size="large"
                    class="ios-input"
                  >
                    <template #prefix>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                      </svg>
                    </template>
                  </el-input>
                </div>
              </el-form-item>
              
              <el-form-item prop="password">
                <div class="input-wrapper">
                  <label class="input-label">{{ $t('login.password') }}</label>
                  <el-input
                    v-model="loginForm.password"
                    type="password"
                    :placeholder="$t('login.passwordPlaceholder') || '请输入密码'"
                    size="large"
                    show-password
                    class="ios-input"
                    @keyup.enter="handleLogin"
                  >
                    <template #prefix>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                      </svg>
                    </template>
                  </el-input>
                </div>
              </el-form-item>
              
              <button
                type="button"
                class="login-btn"
                :disabled="loading"
                @click="handleLogin"
              >
                <span v-if="!loading">{{ $t('login.login') }}</span>
                <span v-else class="loading-content">
                  <svg class="spinner" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-dashoffset="10"/>
                  </svg>
                  {{ $t('login.logging') || '登录中...' }}
                </span>
              </button>
            </el-form>
            
            <div class="form-footer">
              <button type="button" class="link-btn" @click="showRegister = true">
                {{ $t('login.noAccount') || '没有账号？立即注册' }}
              </button>
              <button type="button" class="link-btn secondary" @click="showStatus = true">
                {{ $t('login.checkStatus') || '查询注册状态' }}
              </button>
            </div>
          </div>

          <!-- 注册表单 -->
          <div v-if="showRegister" class="form-container register-form">
            <button type="button" class="back-btn" @click="showRegister = false">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
              </svg>
            </button>
            
            <h2 class="form-title">{{ $t('login.register') || '用户注册' }}</h2>
            <p class="form-subtitle">{{ $t('login.registerHint') || '注册申请需超级管理员审批' }}</p>
            
            <el-form
              ref="registerFormRef"
              :model="registerForm"
              :rules="registerRules"
              class="login-form"
              label-position="top"
            >
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item prop="username" :label="$t('login.username')">
                    <el-input
                      v-model="registerForm.username"
                      :placeholder="$t('login.usernameHint') || '3-50位字母数字'"
                      size="large"
                      class="ios-input"
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item prop="real_name" :label="$t('user.realName')">
                    <el-input
                      v-model="registerForm.real_name"
                      :placeholder="$t('common.pleaseInput')"
                      size="large"
                      class="ios-input"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item prop="password" :label="$t('login.password')">
                    <el-input
                      v-model="registerForm.password"
                      type="password"
                      :placeholder="$t('login.passwordHint') || '至少6位'"
                      size="large"
                      show-password
                      class="ios-input"
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item prop="confirmPassword" :label="$t('user.confirmPassword')">
                    <el-input
                      v-model="registerForm.confirmPassword"
                      type="password"
                      :placeholder="$t('common.pleaseInput')"
                      size="large"
                      show-password
                      class="ios-input"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-form-item prop="email" :label="$t('user.email')">
                <el-input
                  v-model="registerForm.email"
                  placeholder="example@company.com"
                  size="large"
                  class="ios-input"
                />
              </el-form-item>
              
              <el-form-item prop="phone" :label="$t('user.phone') + ' (' + ($t('common.optional') || '可选') + ')'">
                <el-input
                  v-model="registerForm.phone"
                  placeholder="138xxxxxxxx"
                  size="large"
                  class="ios-input"
                />
              </el-form-item>
              
              <el-form-item prop="reason" :label="$t('login.reason') + ' (' + ($t('common.optional') || '可选') + ')'">
                <el-input
                  v-model="registerForm.reason"
                  type="textarea"
                  :rows="3"
                  :placeholder="$t('login.reasonPlaceholder') || '请说明申请理由'"
                  class="ios-textarea"
                />
              </el-form-item>
              
              <button
                type="button"
                class="login-btn"
                :disabled="registerLoading"
                @click="handleRegister"
              >
                <span v-if="!registerLoading">{{ $t('login.submitRegister') || '提交注册申请' }}</span>
                <span v-else class="loading-content">
                  <svg class="spinner" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-dashoffset="10"/>
                  </svg>
                  {{ $t('common.submitting') || '提交中...' }}
                </span>
              </button>
            </el-form>
          </div>

          <!-- 查询状态 -->
          <div v-if="showStatus" class="form-container">
            <button type="button" class="back-btn" @click="showStatus = false; registrationStatus = null">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
              </svg>
            </button>
            
            <h2 class="form-title">{{ $t('login.checkStatus') || '查询注册状态' }}</h2>
            <p class="form-subtitle">{{ $t('login.checkStatusHint') || '输入用户名查询注册申请状态' }}</p>
            
            <el-form
              ref="statusFormRef"
              :model="statusForm"
              :rules="statusRules"
              class="login-form"
            >
              <el-form-item prop="username">
                <div class="input-wrapper">
                  <label class="input-label">{{ $t('login.username') }}</label>
                  <el-input
                    v-model="statusForm.username"
                    :placeholder="$t('login.usernamePlaceholder') || '请输入用户名'"
                    size="large"
                    class="ios-input"
                  >
                    <template #prefix>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                      </svg>
                    </template>
                  </el-input>
                </div>
              </el-form-item>
              
              <button
                type="button"
                class="login-btn"
                :disabled="statusLoading"
                @click="checkStatus"
              >
                <span v-if="!statusLoading">{{ $t('login.checkStatus') || '查询状态' }}</span>
                <span v-else class="loading-content">
                  <svg class="spinner" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-dashoffset="10"/>
                  </svg>
                  {{ $t('common.querying') || '查询中...' }}
                </span>
              </button>
            </el-form>
            
            <!-- 状态结果 -->
            <div v-if="registrationStatus" class="status-result">
              <div class="status-card" :class="registrationStatus.status">
                <div class="status-icon">
                  <svg v-if="registrationStatus.status === 'pending'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                  </svg>
                  <svg v-else-if="registrationStatus.status === 'approved'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="15" y1="9" x2="9" y2="15"/>
                    <line x1="9" y1="9" x2="15" y2="15"/>
                  </svg>
                </div>
                <div class="status-info">
                  <h3>{{ getStatusTitle(registrationStatus.status) }}</h3>
                  <div class="status-detail">
                    <p><strong>{{ $t('login.username') }}：</strong>{{ registrationStatus.username }}</p>
                    <p><strong>{{ $t('user.realName') }}：</strong>{{ registrationStatus.real_name }}</p>
                    <p><strong>{{ $t('common.createTime') }}：</strong>{{ formatTime(registrationStatus.created_at) }}</p>
                    <p v-if="registrationStatus.review_time">
                      <strong>{{ $t('approval.approvalTime') }}：</strong>{{ formatTime(registrationStatus.review_time) }}
                    </p>
                    <p v-if="registrationStatus.review_comment" class="comment">
                      <strong>{{ $t('approval.approvalComment') }}：</strong>{{ registrationStatus.review_comment }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import request from '@/api/index'
import dayjs from 'dayjs'
import LangSwitch from '@/components/LangSwitch.vue'

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()

const loginFormRef = ref(null)
const registerFormRef = ref(null)
const statusFormRef = ref(null)

const loading = ref(false)
const registerLoading = ref(false)
const statusLoading = ref(false)

const showRegister = ref(false)
const showStatus = ref(false)
const registrationStatus = ref(null)

// 登录表单
const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules = {
  username: [
    { required: true, message: t('common.pleaseInput'), trigger: 'blur' }
  ],
  password: [
    { required: true, message: t('common.pleaseInput'), trigger: 'blur' },
    { min: 6, message: t('login.passwordMin') || '密码长度不能少于6位', trigger: 'blur' }
  ]
}

// 注册表单
const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  real_name: '',
  email: '',
  phone: '',
  reason: ''
})

const validatePass = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error(t('login.passwordMismatch') || '两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules = {
  username: [
    { required: true, message: t('common.pleaseInput'), trigger: 'blur' },
    { min: 3, max: 50, message: t('login.usernameLength') || '用户名长度为3-50位', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: t('login.usernamePattern') || '用户名只能包含字母、数字和下划线', trigger: 'blur' }
  ],
  password: [
    { required: true, message: t('common.pleaseInput'), trigger: 'blur' },
    { min: 6, message: t('login.passwordMin') || '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: t('common.pleaseInput'), trigger: 'blur' },
    { validator: validatePass, trigger: 'blur' }
  ],
  real_name: [
    { required: true, message: t('common.pleaseInput'), trigger: 'blur' }
  ],
  email: [
    { required: true, message: t('common.pleaseInput'), trigger: 'blur' },
    { type: 'email', message: t('login.invalidEmail') || '请输入有效的邮箱地址', trigger: 'blur' }
  ]
}

// 状态查询表单
const statusForm = reactive({
  username: ''
})

const statusRules = {
  username: [
    { required: true, message: t('common.pleaseInput'), trigger: 'blur' }
  ]
}

// 登录
const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      const result = await userStore.login(loginForm.username, loginForm.password)
      
      if (result.success) {
        ElMessage.success(t('login.loginSuccess'))
        router.push('/dashboard')
      } else {
        ElMessage.error(result.message)
      }
    } finally {
      loading.value = false
    }
  })
}

// 注册
const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    registerLoading.value = true
    try {
      await request.post('/auth/register', {
        username: registerForm.username,
        password: registerForm.password,
        real_name: registerForm.real_name,
        email: registerForm.email,
        phone: registerForm.phone || null,
        reason: registerForm.reason || null
      })
      
      ElMessage.success(t('login.registerSuccess') || '注册申请已提交，请等待管理员审批')
      
      setTimeout(() => {
        showRegister.value = false
        registerFormRef.value.resetFields()
      }, 1500)
      
    } catch (error) {
      const errorMsg = error.response?.data?.detail || t('common.failed')
      ElMessage.error(errorMsg)
    } finally {
      registerLoading.value = false
    }
  })
}

// 查询状态
const checkStatus = async () => {
  if (!statusFormRef.value) return
  
  await statusFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    statusLoading.value = true
    try {
      registrationStatus.value = await request.get(`/auth/register/status/${statusForm.username}`)
    } catch (error) {
      const errorMsg = error.response?.data?.detail || t('common.failed')
      ElMessage.error(errorMsg)
      registrationStatus.value = null
    } finally {
      statusLoading.value = false
    }
  })
}

// 状态相关方法
const getStatusTitle = (status) => {
  const titles = {
    pending: t('login.statusPending') || '待审批',
    approved: t('login.statusApproved') || '已通过',
    rejected: t('login.statusRejected') || '已拒绝'
  }
  return titles[status] || status
}

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}
</script>

<style lang="scss" scoped>
// ========================================
// iOS-Style Modern Login Page
// ========================================

.login-page-ios {
  position: relative;
  width: 100%;
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  overflow: hidden;
}

// ========================================
// Background Decoration
// ========================================
.bg-decoration {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  
  .blob {
    position: absolute;
    border-radius: 50%;
    filter: blur(60px);
    opacity: 0.6;
    animation: float 20s ease-in-out infinite;
  }
  
  .blob-1 {
    width: 500px;
    height: 500px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    top: -100px;
    right: -100px;
    animation-delay: 0s;
  }
  
  .blob-2 {
    width: 400px;
    height: 400px;
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    bottom: -50px;
    left: -100px;
    animation-delay: -5s;
  }
  
  .blob-3 {
    width: 300px;
    height: 300px;
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    top: 50%;
    left: 30%;
    animation-delay: -10s;
  }
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  33% {
    transform: translate(30px, -30px) scale(1.05);
  }
  66% {
    transform: translate(-20px, 20px) scale(0.95);
  }
}

// ========================================
// Language Switch
// ========================================
.lang-switch-wrapper {
  position: absolute;
  top: 24px;
  right: 24px;
  z-index: 100;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 8px 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

// ========================================
// Main Container
// ========================================
.login-container {
  position: relative;
  display: flex;
  min-height: 100vh;
  z-index: 1;
}

// ========================================
// Brand Section (Left)
// ========================================
.brand-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  
  @media (max-width: 968px) {
    display: none;
  }
  
  .brand-content {
    max-width: 400px;
    text-align: center;
    
    .logo-icon {
      width: 80px;
      height: 80px;
      margin: 0 auto 24px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
      
      svg {
        width: 44px;
        height: 44px;
        color: white;
      }
    }
    
    .brand-title {
      font-size: 42px;
      font-weight: 700;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin: 0 0 8px;
      letter-spacing: -1px;
    }
    
    .brand-subtitle {
      font-size: 16px;
      color: #666;
      margin: 0 0 40px;
    }
    
    .features {
      display: flex;
      flex-direction: column;
      gap: 16px;
      
      .feature-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px 20px;
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        text-align: left;
        
        svg {
          width: 20px;
          height: 20px;
          color: #667eea;
          flex-shrink: 0;
        }
        
        span {
          font-size: 14px;
          color: #333;
          font-weight: 500;
        }
      }
    }
  }
}

// ========================================
// Form Section (Right)
// ========================================
.form-section {
  width: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  box-shadow: -20px 0 60px rgba(0, 0, 0, 0.1);
  
  @media (max-width: 968px) {
    width: 100%;
    max-width: 480px;
    margin: 0 auto;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  }
}

.form-wrapper {
  width: 100%;
  max-width: 400px;
}

.form-container {
  position: relative;
  
  .back-btn {
    position: absolute;
    top: -8px;
    left: -8px;
    width: 36px;
    height: 36px;
    border: none;
    background: transparent;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    transition: all 0.2s ease;
    
    svg {
      width: 20px;
      height: 20px;
      color: #666;
    }
    
    &:hover {
      background: #f0f0f0;
      
      svg {
        color: #333;
      }
    }
  }
  
  .form-title {
    font-size: 28px;
    font-weight: 700;
    color: #1a1a2e;
    margin: 0 0 8px;
    letter-spacing: -0.5px;
  }
  
  .form-subtitle {
    font-size: 14px;
    color: #666;
    margin: 0 0 32px;
  }
}

// ========================================
// Form Styles
// ========================================
.login-form {
  :deep(.el-form-item) {
    margin-bottom: 20px;
  }
  
  :deep(.el-form-item__label) {
    font-size: 13px;
    font-weight: 500;
    color: #333;
    padding-bottom: 8px;
  }
  
  .input-wrapper {
    width: 100%;
    
    .input-label {
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: #333;
      margin-bottom: 8px;
    }
  }
  
  .ios-input {
    :deep(.el-input__wrapper) {
      background: #f5f5f7;
      border: 2px solid transparent;
      border-radius: 12px;
      padding: 4px 16px;
      box-shadow: none;
      transition: all 0.2s ease;
      
      &:hover {
        background: #e8e8ea;
      }
      
      &.is-focus {
        background: white;
        border-color: #667eea;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
      }
    }
    
    :deep(.el-input__inner) {
      font-size: 15px;
      color: #1a1a2e;
      
      &::placeholder {
        color: #999;
      }
    }
    
    :deep(.el-input__prefix) {
      svg {
        width: 18px;
        height: 18px;
        color: #666;
      }
    }
  }
  
  .ios-textarea {
    :deep(.el-textarea__inner) {
      background: #f5f5f7;
      border: 2px solid transparent;
      border-radius: 12px;
      padding: 12px 16px;
      font-size: 15px;
      color: #1a1a2e;
      resize: none;
      transition: all 0.2s ease;
      
      &:hover {
        background: #e8e8ea;
      }
      
      &:focus {
        background: white;
        border-color: #667eea;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
      }
      
      &::placeholder {
        color: #999;
      }
    }
  }
}

// ========================================
// Login Button
// ========================================
.login-btn {
  width: 100%;
  height: 52px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 14px;
  font-size: 16px;
  font-weight: 600;
  color: white;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 8px;
  
  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
  }
  
  &:active:not(:disabled) {
    transform: translateY(0);
  }
  
  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
  
  .loading-content {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    
    .spinner {
      width: 18px;
      height: 18px;
      animation: spin 1s linear infinite;
    }
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// ========================================
// Form Footer
// ========================================
.form-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e0e0e0;
  
  .link-btn {
    background: none;
    border: none;
    font-size: 14px;
    color: #667eea;
    cursor: pointer;
    padding: 0;
    transition: color 0.2s ease;
    
    &:hover {
      color: #764ba2;
    }
    
    &.secondary {
      color: #666;
      
      &:hover {
        color: #333;
      }
    }
  }
}

// ========================================
// Status Result
// ========================================
.status-result {
  margin-top: 24px;
  
  .status-card {
    display: flex;
    gap: 16px;
    padding: 20px;
    border-radius: 16px;
    
    &.pending {
      background: linear-gradient(135deg, rgba(250, 173, 20, 0.1) 0%, rgba(250, 173, 20, 0.05) 100%);
      border: 1px solid rgba(250, 173, 20, 0.3);
      
      .status-icon svg {
        color: #faad14;
      }
    }
    
    &.approved {
      background: linear-gradient(135deg, rgba(82, 196, 26, 0.1) 0%, rgba(82, 196, 26, 0.05) 100%);
      border: 1px solid rgba(82, 196, 26, 0.3);
      
      .status-icon svg {
        color: #52c41a;
      }
    }
    
    &.rejected {
      background: linear-gradient(135deg, rgba(255, 77, 79, 0.1) 0%, rgba(255, 77, 79, 0.05) 100%);
      border: 1px solid rgba(255, 77, 79, 0.3);
      
      .status-icon svg {
        color: #ff4d4f;
      }
    }
    
    .status-icon {
      flex-shrink: 0;
      
      svg {
        width: 28px;
        height: 28px;
      }
    }
    
    .status-info {
      flex: 1;
      
      h3 {
        font-size: 16px;
        font-weight: 600;
        color: #1a1a2e;
        margin: 0 0 12px;
      }
      
      .status-detail {
        p {
          font-size: 13px;
          color: #666;
          margin: 6px 0;
          
          strong {
            color: #333;
          }
          
          &.comment {
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid rgba(0, 0, 0, 0.06);
          }
        }
      }
    }
  }
}

// ========================================
// Register Form Adjustments
// ========================================
.register-form {
  :deep(.el-form-item) {
    margin-bottom: 16px;
  }
  
  :deep(.el-form-item__label) {
    padding-bottom: 4px;
  }
}
</style>
