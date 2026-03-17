<template>
  <div class="login-container">
    <!-- 登录卡片 -->
    <div class="login-box" v-if="!showRegister && !showStatus">
      <h2 class="title">MySQL管理平台</h2>
      <p class="subtitle">企业级数据库运维管理平台</p>
      
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
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
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        <el-button type="primary" link @click="showRegister = true">
          没有账号？立即注册
        </el-button>
        <el-button type="info" link @click="showStatus = true">
          查询注册状态
        </el-button>
      </div>
      

    </div>
    
    <!-- 注册卡片 -->
    <div class="login-box register-box" v-if="showRegister">
      <h2 class="title">用户注册</h2>
      <p class="subtitle">注册申请需超级管理员审批</p>
      
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="用户名（3-50位字母数字）"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="密码（至少6位）"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="确认密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        
        <el-form-item prop="real_name">
          <el-input
            v-model="registerForm.real_name"
            placeholder="真实姓名"
            prefix-icon="UserFilled"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="邮箱地址"
            prefix-icon="Message"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="phone">
          <el-input
            v-model="registerForm.phone"
            placeholder="手机号（可选）"
            prefix-icon="Phone"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="reason">
          <el-input
            v-model="registerForm.reason"
            type="textarea"
            :rows="3"
            placeholder="申请理由（可选）"
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
            提交注册申请
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        <el-button type="primary" link @click="showRegister = false">
          返回登录
        </el-button>
      </div>
    </div>
    
    <!-- 查询注册状态卡片 -->
    <div class="login-box" v-if="showStatus">
      <h2 class="title">查询注册状态</h2>
      <p class="subtitle">输入用户名查询注册申请状态</p>
      
      <el-form
        ref="statusFormRef"
        :model="statusForm"
        :rules="statusRules"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="statusForm.username"
            placeholder="请输入用户名"
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
            查询状态
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
              <p><strong>用户名：</strong>{{ registrationStatus.username }}</p>
              <p><strong>真实姓名：</strong>{{ registrationStatus.real_name }}</p>
              <p><strong>申请时间：</strong>{{ formatTime(registrationStatus.created_at) }}</p>
              <p v-if="registrationStatus.review_time">
                <strong>审批时间：</strong>{{ formatTime(registrationStatus.review_time) }}
              </p>
              <p v-if="registrationStatus.review_comment">
                <strong>审批意见：</strong>{{ registrationStatus.review_comment }}
              </p>
            </div>
          </template>
        </el-alert>
      </div>
      
      <div class="login-footer">
        <el-button type="primary" link @click="showStatus = false; registrationStatus = null">
          返回登录
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import request from '@/api/index'
import dayjs from 'dayjs'

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
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
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
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为3-50位', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validatePass, trigger: 'blur' }
  ],
  real_name: [
    { required: true, message: '请输入真实姓名', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ]
}

// 状态查询表单
const statusForm = reactive({
  username: ''
})

const statusRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
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
        ElMessage.success('登录成功')
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
      
      ElMessage.success('注册申请已提交，请等待管理员审批')
      
      // 显示成功提示后返回登录
      setTimeout(() => {
        showRegister.value = false
        // 重置表单
        registerFormRef.value.resetFields()
      }, 1500)
      
    } catch (error) {
      const errorMsg = error.response?.data?.detail || '注册申请提交失败'
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
      const errorMsg = error.response?.data?.detail || '查询失败'
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
    pending: '待审批',
    approved: '已通过',
    rejected: '已拒绝'
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
    
    .login-tips {
      text-align: center;
      margin-top: 15px;
      color: #999;
      font-size: 12px;
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
}
</style>
