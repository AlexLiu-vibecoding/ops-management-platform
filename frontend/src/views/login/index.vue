<template>
  <div class="login-container">
    <!-- 登录卡片 -->
    <div class="login-box" v-if="!showRegister && !showStatus">
      <h2 class="title">{{ $t('dashboard.title') }}</h2>
      <p class="subtitle">{{ $t('login.subtitle') || '企业级数据库运维管理平台' }}</p>
      
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            :placeholder="$t('login.username')"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            :placeholder="$t('login.password')"
            prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            {{ $t('login.login') }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        <el-button type="primary" link @click="showRegister = true">
          {{ $t('login.noAccount') || '没有账号？立即注册' }}
        </el-button>
        <el-button type="info" link @click="showStatus = true">
          {{ $t('login.checkStatus') || '查询注册状态' }}
        </el-button>
      </div>
    </div>
    
    <!-- 注册卡片 -->
    <div class="login-box register-box" v-if="showRegister">
      <h2 class="title">{{ $t('login.register') || '用户注册' }}</h2>
      <p class="subtitle">{{ $t('login.registerHint') || '注册申请需超级管理员审批' }}</p>
      
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            :placeholder="$t('login.usernameHint') || '用户名（3-50位字母数字）'"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            :placeholder="$t('login.passwordHint') || '密码（至少6位）'"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            :placeholder="$t('user.confirmPassword')"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        
        <el-form-item prop="real_name">
          <el-input
            v-model="registerForm.real_name"
            :placeholder="$t('user.realName')"
            prefix-icon="UserFilled"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="email">
          <el-input
            v-model="registerForm.email"
            :placeholder="$t('user.email')"
            prefix-icon="Message"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="phone">
          <el-input
            v-model="registerForm.phone"
            :placeholder="$t('user.phone') + ' (' + ($t('common.optional') || '可选') + ')'"
            prefix-icon="Phone"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="reason">
          <el-input
            v-model="registerForm.reason"
            type="textarea"
            :rows="3"
            :placeholder="$t('login.reason') || '申请理由（可选）'"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="registerLoading"
            @click="handleRegister"
          >
            {{ $t('login.submitRegister') || '提交注册申请' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        <el-button type="primary" link @click="showRegister = false">
          {{ $t('login.backToLogin') || '返回登录' }}
        </el-button>
      </div>
    </div>
    
    <!-- 查询注册状态卡片 -->
    <div class="login-box" v-if="showStatus">
      <h2 class="title">{{ $t('login.checkStatus') || '查询注册状态' }}</h2>
      <p class="subtitle">{{ $t('login.checkStatusHint') || '输入用户名查询注册申请状态' }}</p>
      
      <el-form
        ref="statusFormRef"
        :model="statusForm"
        :rules="statusRules"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="statusForm.username"
            :placeholder="$t('login.username')"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="statusLoading"
            @click="checkStatus"
          >
            {{ $t('login.checkStatus') || '查询状态' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <!-- 状态结果 -->
      <div v-if="registrationStatus" class="status-result">
        <el-alert
          :title="getStatusTitle(registrationStatus.status)"
          :type="getStatusType(registrationStatus.status)"
          :closable="false"
          show-icon
        >
          <template #default>
            <div class="status-detail">
              <p><strong>{{ $t('login.username') }}：</strong>{{ registrationStatus.username }}</p>
              <p><strong>{{ $t('user.realName') }}：</strong>{{ registrationStatus.real_name }}</p>
              <p><strong>{{ $t('common.createTime') }}：</strong>{{ formatTime(registrationStatus.created_at) }}</p>
              <p v-if="registrationStatus.review_time">
                <strong>{{ $t('approval.approvalTime') }}：</strong>{{ formatTime(registrationStatus.review_time) }}
              </p>
              <p v-if="registrationStatus.review_comment">
                <strong>{{ $t('approval.approvalComment') }}：</strong>{{ registrationStatus.review_comment }}
              </p>
            </div>
          </template>
        </el-alert>
      </div>
      
      <div class="login-footer">
        <el-button type="primary" link @click="showStatus = false; registrationStatus = null">
          {{ $t('login.backToLogin') || '返回登录' }}
        </el-button>
      </div>
    </div>
    
    <!-- 语言切换 -->
    <div class="lang-switch-wrapper">
      <LangSwitch />
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
      
      // 显示成功提示后返回登录
      setTimeout(() => {
        showRegister.value = false
        // 重置表单
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

const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    approved: 'success',
    rejected: 'error'
  }
  return types[status] || 'info'
}

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}
</script>

<style lang="scss" scoped>
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  
  .login-box {
    width: 400px;
    padding: 40px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
    
    &.register-box {
      width: 450px;
    }
    
    .title {
      text-align: center;
      font-size: 28px;
      color: #333;
      margin-bottom: 10px;
    }
    
    .subtitle {
      text-align: center;
      color: #999;
      margin-bottom: 30px;
    }
    
    .login-form {
      .login-btn {
        width: 100%;
        height: 44px;
        font-size: 16px;
      }
    }
    
    .login-footer {
      text-align: center;
      margin-top: 15px;
      display: flex;
      justify-content: center;
      gap: 20px;
    }
    
    .status-result {
      margin-top: 20px;
      
      .status-detail {
        margin-top: 10px;
        font-size: 13px;
        
        p {
          margin: 5px 0;
        }
      }
    }
  }
  
  .lang-switch-wrapper {
    position: absolute;
    top: 20px;
    right: 20px;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 6px;
    padding: 8px 12px;
  }
}
</style>
