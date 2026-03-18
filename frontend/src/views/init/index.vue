<template>
  <div class="init-container">
    <div class="init-card">
      <!-- 步骤指示器 -->
      <div class="steps-header">
        <div class="logo">
          <el-icon :size="40"><Coin /></el-icon>
          <h1>运维管理平台</h1>
        </div>
        <el-steps :active="currentStep" align-center finish-status="success">
          <el-step title="数据库配置" description="配置数据库连接" />
          <el-step title="Redis配置" description="配置缓存服务" />
          <el-step title="管理员设置" description="创建管理员账户" />
          <el-step title="完成" description="开始使用" />
        </el-steps>
      </div>

      <!-- 步骤内容 -->
      <div class="step-content">
        <!-- 步骤1: 数据库配置 -->
        <div v-show="currentStep === 0" class="step-panel">
          <h2>数据库配置</h2>
          <p class="desc">请配置系统使用的数据库连接信息</p>
          
          <el-form
            ref="dbFormRef"
            :model="dbConfig"
            :rules="dbRules"
            label-width="100px"
            class="config-form"
          >
            <el-form-item label="数据库类型" prop="db_type">
              <el-radio-group v-model="dbConfig.db_type">
                <el-radio value="postgresql">PostgreSQL</el-radio>
                <el-radio value="mysql">MySQL</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item label="主机地址" prop="host">
              <el-input v-model="dbConfig.host" placeholder="如: localhost 或 db.example.com" />
            </el-form-item>
            
            <el-form-item label="端口" prop="port">
              <el-input-number v-model="dbConfig.port" :min="1" :max="65535" />
            </el-form-item>
            
            <el-form-item label="数据库名" prop="database">
              <el-input v-model="dbConfig.database" placeholder="数据库名称" />
            </el-form-item>
            
            <el-form-item label="用户名" prop="username">
              <el-input v-model="dbConfig.username" placeholder="数据库用户名" />
            </el-form-item>
            
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="dbConfig.password"
                type="password"
                show-password
                placeholder="数据库密码"
              />
            </el-form-item>
          </el-form>
          
          <div class="test-connection">
            <el-button
              type="primary"
              plain
              @click="testDatabaseConnection"
              :loading="testingDb"
            >
              <el-icon><Link /></el-icon>
              测试连接
            </el-button>
            <span v-if="dbTestResult" :class="['test-result', dbTestResult.success ? 'success' : 'error']">
              {{ dbTestResult.message }}
            </span>
          </div>
        </div>

        <!-- 步骤2: Redis配置 -->
        <div v-show="currentStep === 1" class="step-panel">
          <h2>Redis配置</h2>
          <p class="desc">Redis用于缓存和会话管理（可选，可跳过）</p>
          
          <el-form
            ref="redisFormRef"
            :model="redisConfig"
            :rules="redisRules"
            label-width="100px"
            class="config-form"
          >
            <el-form-item label="主机地址" prop="host">
              <el-input v-model="redisConfig.host" placeholder="如: localhost" />
            </el-form-item>
            
            <el-form-item label="端口" prop="port">
              <el-input-number v-model="redisConfig.port" :min="1" :max="65535" />
            </el-form-item>
            
            <el-form-item label="密码">
              <el-input
                v-model="redisConfig.password"
                type="password"
                show-password
                placeholder="Redis密码（如有）"
              />
            </el-form-item>
            
            <el-form-item label="数据库">
              <el-input-number v-model="redisConfig.db" :min="0" :max="15" />
            </el-form-item>
          </el-form>
          
          <div class="test-connection">
            <el-button
              type="primary"
              plain
              @click="testRedisConnection"
              :loading="testingRedis"
            >
              <el-icon><Link /></el-icon>
              测试连接
            </el-button>
            <span v-if="redisTestResult" :class="['test-result', redisTestResult.success ? 'success' : 'error']">
              {{ redisTestResult.message }}
            </span>
          </div>
        </div>

        <!-- 步骤3: 管理员设置 -->
        <div v-show="currentStep === 2" class="step-panel">
          <h2>创建管理员账户</h2>
          <p class="desc">创建系统的超级管理员账户</p>
          
          <el-form
            ref="adminFormRef"
            :model="adminConfig"
            :rules="adminRules"
            label-width="100px"
            class="config-form"
          >
            <el-form-item label="用户名" prop="username">
              <el-input v-model="adminConfig.username" placeholder="管理员用户名" />
            </el-form-item>
            
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="adminConfig.password"
                type="password"
                show-password
                placeholder="管理员密码"
              />
            </el-form-item>
            
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input
                v-model="adminConfig.confirmPassword"
                type="password"
                show-password
                placeholder="再次输入密码"
              />
            </el-form-item>
            
            <el-form-item label="真实姓名" prop="real_name">
              <el-input v-model="adminConfig.real_name" placeholder="您的姓名" />
            </el-form-item>
            
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="adminConfig.email" placeholder="您的邮箱" />
            </el-form-item>
          </el-form>
        </div>

        <!-- 步骤4: 完成 -->
        <div v-show="currentStep === 3" class="step-panel complete-panel">
          <el-icon :size="80" color="#67C23A"><CircleCheckFilled /></el-icon>
          <h2>系统初始化完成</h2>
          <p class="desc">恭喜！系统已成功初始化，可以开始使用了</p>
          
          <div class="summary">
            <h3>配置摘要</h3>
            <div class="summary-item">
              <span class="label">数据库:</span>
              <span class="value">{{ dbConfig.host }}:{{ dbConfig.port }}/{{ dbConfig.database }}</span>
            </div>
            <div class="summary-item">
              <span class="label">Redis:</span>
              <span class="value">{{ redisConfig.host || '未配置' }}:{{ redisConfig.port }}</span>
            </div>
            <div class="summary-item">
              <span class="label">管理员:</span>
              <span class="value">{{ adminConfig.username }}</span>
            </div>
          </div>
          
          <el-button type="primary" size="large" @click="goToLogin">
            开始使用
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="step-actions">
        <el-button v-if="currentStep > 0 && currentStep < 3" @click="prevStep">
          上一步
        </el-button>
        <el-button
          v-if="currentStep === 0"
          @click="skipAll"
        >
          跳过配置
        </el-button>
        <el-button
          v-if="currentStep === 0"
          type="primary"
          @click="nextStep"
          :disabled="!dbTestResult?.success"
        >
          下一步
        </el-button>
        <el-button
          v-if="currentStep === 1"
          @click="skipRedis"
        >
          跳过
        </el-button>
        <el-button
          v-if="currentStep === 1"
          type="primary"
          @click="saveConfig"
          :loading="saving"
        >
          保存配置
        </el-button>
        <el-button
          v-if="currentStep === 2"
          type="primary"
          @click="createAdmin"
          :loading="creating"
        >
          完成初始化
        </el-button>
      </div>
      
      <!-- 跳过提示 -->
      <div class="skip-tip">
        <p>提示：您可以跳过配置，系统将使用默认配置运行</p>
        <p>后续可在"系统设置"中修改配置</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Coin, Link, CircleCheckFilled, ArrowRight } from '@element-plus/icons-vue'
import request from '@/api/index'

const router = useRouter()
const currentStep = ref(0)

// 数据库配置
const dbFormRef = ref(null)
const testingDb = ref(false)
const dbTestResult = ref(null)
const dbConfig = reactive({
  db_type: 'mysql',
  host: 'localhost',
  port: 3306,
  database: 'ops_platform',
  username: 'root',
  password: ''
})

// 监听数据库类型变化，自动切换默认端口
watch(() => dbConfig.db_type, (newType) => {
  if (newType === 'mysql') {
    dbConfig.port = 3306
    dbConfig.username = 'root'
  } else {
    dbConfig.port = 5432
    dbConfig.username = 'postgres'
  }
})

const dbRules = {
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  database: [{ required: true, message: '请输入数据库名', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// Redis配置
const redisFormRef = ref(null)
const testingRedis = ref(false)
const redisTestResult = ref(null)
const redisConfig = reactive({
  host: 'localhost',
  port: 6379,
  password: '',
  db: 0
})

const redisRules = {
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }]
}

// 管理员配置
const adminFormRef = ref(null)
const creating = ref(false)
const adminConfig = reactive({
  username: 'admin',
  password: '',
  confirmPassword: '',
  real_name: '',
  email: ''
})

const validatePassword = (rule, value, callback) => {
  if (value !== adminConfig.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const adminRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度3-50字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validatePassword, trigger: 'blur' }
  ],
  real_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ]
}

const saving = ref(false)

// 测试数据库连接
const testDatabaseConnection = async () => {
  await dbFormRef.value.validate()
  
  testingDb.value = true
  try {
    const result = await request.post('/init/test-database', dbConfig)
    dbTestResult.value = result
    
    if (result.success) {
      ElMessage.success('数据库连接成功')
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    dbTestResult.value = { success: false, message: error.message || '连接失败' }
  } finally {
    testingDb.value = false
  }
}

// 测试Redis连接
const testRedisConnection = async () => {
  testingRedis.value = true
  try {
    const result = await request.post('/init/test-redis', redisConfig)
    redisTestResult.value = result
    
    if (result.success) {
      ElMessage.success('Redis连接成功')
    } else {
      ElMessage.warning(result.message)
    }
  } catch (error) {
    redisTestResult.value = { success: false, message: error.message || '连接失败' }
  } finally {
    testingRedis.value = false
  }
}

// 下一步
const nextStep = () => {
  currentStep.value++
}

// 上一步
const prevStep = () => {
  currentStep.value--
}

// 跳过Redis
const skipRedis = () => {
  redisConfig.host = ''
  redisConfig.port = 6379
  saveConfig()
}

// 跳过所有配置，使用默认配置
const skipAll = async () => {
  try {
    // 标记系统初始化完成（使用默认配置）
    const result = await request.post('/init/skip-config')
    
    if (result.success) {
      ElMessage.success('使用默认配置启动')
      currentStep.value = 3
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    ElMessage.error('跳过配置失败')
  }
}

// 保存配置
const saveConfig = async () => {
  saving.value = true
  try {
    const result = await request.post('/init/save-config', {
      database: dbConfig,
      redis: redisConfig.host ? redisConfig : null,
      admin: adminConfig
    })
    
    if (result.success) {
      ElMessage.success('配置保存成功')
      currentStep.value = 2
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    ElMessage.error('保存配置失败')
  } finally {
    saving.value = false
  }
}

// 创建管理员
const createAdmin = async () => {
  await adminFormRef.value.validate()
  
  creating.value = true
  try {
    const result = await request.post('/init/create-admin', adminConfig)
    
    if (result.success) {
      ElMessage.success('管理员账户创建成功')
      currentStep.value = 3
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

// 跳转到登录页
const goToLogin = () => {
  router.push('/login')
}

// 检查初始化状态
onMounted(async () => {
  try {
    const status = await request.get('/init/status')
    if (status.is_initialized) {
      // 已初始化，跳转到登录页
      router.push('/login')
    }
  } catch (error) {
    console.error('检查初始化状态失败:', error)
  }
})
</script>

<style lang="scss" scoped>
.init-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.init-card {
  width: 100%;
  max-width: 800px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  padding: 40px;
}

.steps-header {
  .logo {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 15px;
    margin-bottom: 30px;
    
    h1 {
      font-size: 24px;
      color: #303133;
      margin: 0;
    }
    
    .el-icon {
      color: #667eea;
    }
  }
}

.step-content {
  margin: 40px 0;
  min-height: 350px;
}

.step-panel {
  h2 {
    text-align: center;
    color: #303133;
    margin-bottom: 10px;
  }
  
  .desc {
    text-align: center;
    color: #909399;
    margin-bottom: 30px;
  }
}

.config-form {
  max-width: 450px;
  margin: 0 auto;
}

.test-connection {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  margin-top: 20px;
  
  .test-result {
    font-size: 14px;
    
    &.success {
      color: #67C23A;
    }
    
    &.error {
      color: #F56C6C;
    }
  }
}

.step-actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-top: 20px;
}

.complete-panel {
  text-align: center;
  
  .el-icon {
    margin-bottom: 20px;
  }
  
  h2 {
    color: #67C23A;
  }
  
  .summary {
    background: #f5f7fa;
    border-radius: 8px;
    padding: 20px;
    margin: 30px auto;
    max-width: 400px;
    text-align: left;
    
    h3 {
      margin: 0 0 15px 0;
      font-size: 14px;
      color: #606266;
      border-bottom: 1px solid #ebeef5;
      padding-bottom: 10px;
    }
    
    .summary-item {
      display: flex;
      margin: 8px 0;
      
      .label {
        width: 70px;
        color: #909399;
      }
      
      .value {
        color: #303133;
        font-weight: 500;
      }
    }
  }
}

.skip-tip {
  text-align: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
  
  p {
    font-size: 12px;
    color: #909399;
    margin: 5px 0;
  }
}
</style>
