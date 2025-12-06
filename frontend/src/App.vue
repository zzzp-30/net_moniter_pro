<script setup>
import { ref, nextTick } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

// --- 状态变量 ---
const isLoggedIn = ref(false)
const isRegisterMode = ref(false) // 新增：控制登录/注册模式切换
const username = ref('')
const password = ref('')

// 仪表盘数据，新增 settings 字段用于回显后端配置
const dashboardData = ref({ 
  traffic: [], 
  packets: [], 
  alerts: [], 
  devices: {}, 
  settings: { threshold: 2.0, filter: 'ALL' } 
})

// 控制面板绑定变量
const selectedFilter = ref('ALL')
const thresholdInput = ref(2.0)

let chartInstance = null
let pollInterval = null

// --- 功能 1: 统一处理 登录/注册 ---
const handleAuth = async () => {
  if (!username.value || !password.value) return alert("请输入用户名和密码")
  
  // 根据模式判断请求地址
  const url = isRegisterMode.value 
    ? 'http://127.0.0.1:8000/api/register/' 
    : 'http://127.0.0.1:8000/api/login/'

  try {
    const res = await axios.post(url, {
      username: username.value,
      password: password.value
    })

    if (res.data.token) {
      // 登录成功
      isLoggedIn.value = true
      nextTick(() => initDashboard())
    } else if (isRegisterMode.value) {
      // 注册成功后，切换回登录模式让用户登录
      alert("注册成功！请使用账号登录系统")
      isRegisterMode.value = false
      password.value = '' // 清空密码
    }
  } catch (e) {
    const errorMsg = e.response?.data?.error || "连接服务器失败"
    alert(`操作失败: ${errorMsg}`)
  }
}

// --- 功能 3 & 4: 应用配置到后端 ---
const applySettings = async () => {
  try {
    // 并行发送请求
    await Promise.all([
      axios.post('http://127.0.0.1:8000/api/dashboard/', {
        action: 'set_threshold', 
        value: thresholdInput.value
      }),
      axios.post('http://127.0.0.1:8000/api/dashboard/', {
        action: 'set_filter', 
        value: selectedFilter.value
      })
    ])
    alert("系统配置已更新")
  } catch (e) {
    alert("配置更新失败，请检查网络")
  }
}

// 初始化仪表盘
const initDashboard = () => {
  const chartDom = document.getElementById('main-chart')
  if (chartDom) {
    chartInstance = echarts.init(chartDom, 'dark')
    window.addEventListener('resize', () => chartInstance.resize())
  }
  // 启动轮询
  pollInterval = setInterval(fetchData, 1000)
}

// 获取数据
const fetchData = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/dashboard/')
    dashboardData.value = res.data
    updateChart(res.data.traffic)
    
    // 首次加载或后端配置变更时，同步到前端输入框 (可选逻辑，这里简单处理为首次同步)
    // 如果你想让输入框始终跟随后端，可以取消注释下面两行，但这会影响用户正在输入时的体验
    // if (pollInterval && pollInterval < 2) { 
    //     thresholdInput.value = res.data.settings.threshold
    //     selectedFilter.value = res.data.settings.filter
    // }

    // 自动滚动日志
    const logWin = document.getElementById('log-window')
    if(logWin) {
        const isScrolledToBottom = logWin.scrollHeight - logWin.clientHeight <= logWin.scrollTop + 50;
        if(isScrolledToBottom) logWin.scrollTop = logWin.scrollHeight
    }
  } catch (e) {
    console.error("数据获取失败", e)
  }
}

// 更新图表
const updateChart = (data) => {
  if (!chartInstance) return
  const times = data.map(item => item.time)
  const sent = data.map(item => (item.sent / 1024).toFixed(1))
  const recv = data.map(item => (item.recv / 1024).toFixed(1))

  chartInstance.setOption({
    backgroundColor: 'transparent',
    title: { text: '实时网络吞吐量 (KB/s)', left: '20', textStyle: { color: '#fff', fontSize: 16 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { top: 0, right: 20, textStyle: { color: '#ccc' } },
    grid: { top: 60, bottom: 30, left: 50, right: 30, containLabel: true },
    xAxis: { type: 'category', data: times, boundaryGap: false, axisLine: { lineStyle: { color: '#555' } } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#333', type: 'dashed' } } },
    series: [
      { 
        name: '上传 Upload', type: 'line', data: sent, smooth: true, showSymbol: false,
        lineStyle: { width: 3, color: '#ff4d4f' },
        areaStyle: { opacity: 0.2, color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{offset: 0, color: '#ff4d4f'}, {offset: 1, color: 'rgba(255, 77, 79, 0)'}]) }
      },
      { 
        name: '下载 Download', type: 'line', data: recv, smooth: true, showSymbol: false,
        lineStyle: { width: 3, color: '#409EFF' },
        areaStyle: { opacity: 0.2, color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{offset: 0, color: '#409EFF'}, {offset: 1, color: 'rgba(64, 158, 255, 0)'}]) }
      }
    ]
  })
}
</script>

<template>
  <transition name="fade">
    <div v-if="!isLoggedIn" class="login-wrapper">
      <div class="login-bg-animation"></div>
      <div class="login-card">
        <div class="brand">
          <div class="logo-glow">⚡</div>
          <h2>NET SENTRY</h2>
          <p class="subtitle">网络态势感知系统</p>
        </div>
        <div class="input-group">
          <input v-model="username" type="text" placeholder="Access ID" class="cyber-input" />
          <input v-model="password" type="password" placeholder="Passcode" class="cyber-input" @keyup.enter="handleAuth"/>
        </div>
        
        <button @click="handleAuth" class="cyber-btn">
          <span class="btn-text">{{ isRegisterMode ? 'REGISTER ID' : 'INITIALIZE LINK' }}</span>
          <span class="btn-glitch"></span>
        </button>

        <div class="switch-mode" @click="isRegisterMode = !isRegisterMode">
          {{ isRegisterMode ? '已有账号? 返回登录 [LOGIN]' : '没有账号? 立即注册 [REGISTER]' }}
        </div>
      </div>
    </div>
  </transition>

  <div v-if="isLoggedIn" class="dashboard">
    <header class="top-bar">
      <div class="logo-area">
        <span class="icon">⚡</span>
        <span class="text">NET MONITOR <small>PRO</small></span>
      </div>
      
      <div class="control-bar">
        <div class="control-group">
          <label>Filter:</label>
          <select v-model="selectedFilter" class="cyber-select">
            <option value="ALL">ALL PROTOCOLS</option>
            <option value="TCP">TCP ONLY</option>
            <option value="UDP">UDP ONLY</option>
          </select>
        </div>
        
        <div class="control-group">
          <label>Threshold(MB):</label>
          <input v-model="thresholdInput" type="number" step="0.5" class="cyber-input-sm">
        </div>

        <button @click="applySettings" class="action-btn">APPLY</button>
      </div>

      <div v-if="dashboardData.alerts.length" class="alert-ticker">
        <span class="alert-icon">⚠️</span>
        <span class="alert-msg">{{ dashboardData.alerts[dashboardData.alerts.length-1].msg }}</span>
      </div>

      <div class="actions">
        <button @click="isLoggedIn = false" class="logout-btn">DISCONNECT</button>
      </div>
    </header>

    <div class="main-content">
      <div class="col-main">
        <div class="panel chart-panel">
          <div id="main-chart" class="chart-container"></div>
        </div>
        
        <div class="panel device-panel">
          <div class="panel-header">
            <h3>active_interfaces</h3>
            <span class="status-indicator online">ONLINE</span>
          </div>
          <div class="device-grid">
            <div v-for="(ip, name) in dashboardData.devices" :key="name" class="device-card">
              <div class="dev-icon">🖧</div>
              <div class="dev-info">
                <span class="dev-name">{{ name }}</span>
                <span class="dev-ip">{{ ip }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="col-logs">
        <div class="panel log-panel">
          <div class="panel-header">
            <h3>packet_sniffer_logs [{{ selectedFilter }}]</h3>
            <span class="count">{{ dashboardData.packets.length }} packets</span>
          </div>
          <div id="log-window" class="log-window">
            <div v-for="(log, index) in dashboardData.packets" :key="index" class="log-row">
              <span class="time">{{ log.time }}</span>
              <span class="proto" :class="log.proto">{{ log.proto }}</span>
              <div class="detail">
                <span class="addr src">{{ log.src }}</span>
                <span class="arrow">→</span>
                <span class="addr dst">{{ log.dst }}</span>
              </div>
              <span class="size">{{ log.len }}B</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* 全局样式：去除默认边距，确保铺满 */
body, html {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background-color: #050b14;
  font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
</style>

<style scoped>
/* --- 登录页样式 --- */
.login-wrapper {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #000;
  z-index: 999;
}

.login-bg-animation {
  position: absolute;
  inset: 0;
  background: linear-gradient(45deg, #020617, #0f172a, #1e1b4b);
  background-size: 400% 400%;
  animation: gradientBG 15s ease infinite;
  z-index: -1;
}
@keyframes gradientBG {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.login-card {
  width: 380px;
  padding: 40px;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  box-shadow: 0 0 40px rgba(0, 0, 0, 0.6);
  text-align: center;
}

.brand .logo-glow {
  font-size: 48px;
  margin-bottom: 10px;
  text-shadow: 0 0 20px #3b82f6;
  animation: pulse 2s infinite;
}
.brand h2 { margin: 0; color: #fff; letter-spacing: 4px; font-weight: 800; }
.brand .subtitle { color: #64748b; margin-bottom: 30px; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 2px; }

.input-group { margin-bottom: 25px; display: flex; flex-direction: column; gap: 15px; }
.cyber-input {
  width: 100%;
  padding: 15px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #334155;
  border-radius: 4px;
  color: #e2e8f0;
  font-size: 1rem;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.3s;
}
.cyber-input:focus { border-color: #3b82f6; background: rgba(0, 0, 0, 0.5); }

.cyber-btn {
  width: 100%;
  padding: 15px;
  background: #2563eb;
  border: none;
  color: white;
  font-weight: bold;
  letter-spacing: 2px;
  cursor: pointer;
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
  transition: all 0.2s;
}
.cyber-btn:hover { background: #1d4ed8; transform: translateY(-2px); box-shadow: 0 0 20px rgba(37, 99, 235, 0.5); }

/* 切换模式文字样式 */
.switch-mode {
  margin-top: 20px;
  color: #64748b;
  font-size: 0.85rem;
  cursor: pointer;
  transition: color 0.3s;
}
.switch-mode:hover { color: #3b82f6; text-decoration: underline; }

/* --- 仪表盘样式 --- */
.dashboard {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #0b1120;
  color: #cbd5e1;
}

.top-bar {
  height: 60px;
  background: #1e293b;
  border-bottom: 1px solid #334155;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  flex-shrink: 0;
}
.logo-area { display: flex; align-items: center; gap: 10px; color: #fff; font-weight: bold; font-size: 1.2rem; }
.logo-area small { color: #3b82f6; font-size: 0.8em; margin-left: 5px; }

/* 新增：中间控制栏样式 */
.control-bar {
  display: flex;
  align-items: center;
  gap: 15px;
  margin: 0 20px;
}
.control-group { display: flex; align-items: center; gap: 5px; font-size: 0.8rem; color: #94a3b8; }
.cyber-select, .cyber-input-sm {
  background: #0f172a;
  border: 1px solid #334155;
  color: #e2e8f0;
  padding: 5px 8px;
  border-radius: 4px;
  font-family: inherit;
  outline: none;
}
.cyber-input-sm { width: 50px; text-align: center; }
.action-btn {
  background: #10b981;
  border: none;
  color: white;
  padding: 5px 12px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}
.action-btn:hover { background: #059669; }

/* 报警样式 */
.alert-ticker {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5;
  padding: 5px 15px;
  border-radius: 20px;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

.logout-btn {
  background: transparent;
  border: 1px solid #475569;
  color: #94a3b8;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}
.logout-btn:hover { border-color: #ef4444; color: #ef4444; }

/* 主布局 */
.main-content {
  flex: 1;
  display: flex;
  padding: 15px;
  gap: 15px;
  overflow: hidden;
}

.col-main { flex: 2; display: flex; flex-direction: column; gap: 15px; min-width: 0; }
.col-logs { flex: 1; min-width: 300px; display: flex; flex-direction: column; }

.panel {
  background: #162032;
  border: 1px solid #283548;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.panel-header {
  padding: 10px 15px;
  background: #1e293b;
  border-bottom: 1px solid #283548;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-header h3 { margin: 0; font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; font-weight: 600; letter-spacing: 1px; }

/* 图表与设备 */
.chart-panel { flex: 2; position: relative; }
.chart-container { width: 100%; height: 100%; }
.device-panel { flex: 1; overflow-y: auto; }
.device-grid { padding: 15px; display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
.device-card {
  background: #0f172a;
  padding: 12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid transparent;
  transition: border-color 0.2s;
}
.device-card:hover { border-color: #3b82f6; }
.dev-icon { font-size: 1.5rem; color: #64748b; }
.dev-info { display: flex; flex-direction: column; }
.dev-name { font-size: 0.8rem; color: #94a3b8; font-weight: bold; }
.dev-ip { font-size: 0.9rem; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; }

/* 日志窗口 */
.log-panel { height: 100%; }
.log-window {
  flex: 1;
  overflow-y: auto;
  background: #0b1120;
  padding: 5px 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
}
.log-row {
  padding: 6px 15px;
  border-bottom: 1px solid #1e293b;
  display: grid;
  grid-template-columns: 70px 50px 1fr 60px;
  align-items: center;
  gap: 10px;
}
.log-row:hover { background: #162032; }
.time { color: #64748b; }
.proto { text-align: center; font-weight: bold; border-radius: 3px; padding: 1px 0; }
.proto.TCP { color: #60a5fa; background: rgba(96, 165, 250, 0.1); }
.proto.UDP { color: #fbbf24; background: rgba(251, 191, 36, 0.1); }
.detail { display: flex; align-items: center; gap: 5px; color: #cbd5e1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.arrow { color: #64748b; font-size: 0.8em; }
.addr { max-width: 120px; overflow: hidden; text-overflow: ellipsis; }
.size { color: #94a3b8; text-align: right; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0b1120; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }

@keyframes pulse { 0% { opacity: 0.8; } 50% { opacity: 1; transform: scale(1.1); } 100% { opacity: 0.8; } }
.fade-enter-active, .fade-leave-active { transition: opacity 0.5s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>