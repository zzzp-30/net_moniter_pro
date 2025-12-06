<script setup>
import { ref, nextTick, computed, onMounted } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

// --- 基础状态 ---
const isLoggedIn = ref(false)
const isRegisterMode = ref(false)
const isHistoryMode = ref(false)
const username = ref('')
const password = ref('')

// --- 仪表盘数据 ---
const dashboardData = ref({ traffic: [], packets: [], alerts: [], devices: {}, settings: { threshold: 2.0, filter: 'ALL' } })
const selectedFilter = ref('ALL')
const thresholdInput = ref(2.0)

// --- 历史记录专属状态 ---
// 默认选中今天
const todayStr = new Date().toISOString().split('T')[0]
const selectedDate = ref(todayStr) 
const selectedSlot = ref('ALL') // 'ALL' 或 '00:00', '00:30' 等
const historyRawData = ref([])  // 存储那一天所有的原始数据

// 生成 48 个 30分钟的时间段 (00:00, 00:30, ... 23:30)
const timeSlots = computed(() => {
  const slots = []
  for (let h = 0; h < 24; h++) {
    for (let m = 0; m < 60; m += 30) {
      const hour = h.toString().padStart(2, '0')
      const minute = m.toString().padStart(2, '0')
      slots.push(`${hour}:${minute}`)
    }
  }
  return slots
})

let chartInstance = null
let pollInterval = null

// --- 鉴权逻辑 (不变) ---
const handleAuth = async () => {
  if (!username.value || !password.value) return alert("请输入完整信息")
  const url = isRegisterMode.value ? 'http://127.0.0.1:8000/api/register/' : 'http://127.0.0.1:8000/api/login/'
  try {
    const res = await axios.post(url, { username: username.value, password: password.value })
    if (res.data.token) {
      isLoggedIn.value = true
      nextTick(() => initDashboard())
    } else if (isRegisterMode.value) {
      alert("注册成功! 请登录")
      isRegisterMode.value = false; password.value = ''
    }
  } catch (e) { alert("操作失败") }
}

const applySettings = async () => {
  try {
    await Promise.all([
      axios.post('http://127.0.0.1:8000/api/dashboard/', { action: 'set_threshold', value: thresholdInput.value }),
      axios.post('http://127.0.0.1:8000/api/dashboard/', { action: 'set_filter', value: selectedFilter.value })
    ])
    alert("系统配置已同步")
  } catch (e) { alert("配置更新失败") }
}

// --- 核心逻辑 ---
const initDashboard = () => {
  const chartDom = document.getElementById('main-chart')
  if (chartDom) {
    chartInstance = echarts.init(chartDom, 'dark')
    window.addEventListener('resize', () => chartInstance.resize())
  }
  startRealtime()
}

const startRealtime = () => {
  isHistoryMode.value = false
  if(pollInterval) clearInterval(pollInterval)
  pollInterval = setInterval(fetchRealtimeData, 1000)
}

// 切换到历史模式 / 改变日期 / 改变时段
const showHistory = async () => {
  isHistoryMode.value = true
  if(pollInterval) clearInterval(pollInterval)
  
  // 如果是第一次切过来，或者改变了日期，需要重新请求后端
  try {
    const res = await axios.get(`http://127.0.0.1:8000/api/history/?date=${selectedDate.value}`)
    historyRawData.value = res.data // 存下全天数据
    renderHistoryChart() // 渲染图表
  } catch(e) { 
    alert("获取历史数据失败") 
  }
}

// 根据当前选中的时段过滤数据并渲染
const renderHistoryChart = () => {
  let displayData = []

  if (selectedSlot.value === 'ALL') {
    // 显示全天
    displayData = historyRawData.value
  } else {
    // 过滤出选定30分钟内的数据
    // selectedSlot 格式如 "14:30"
    const [startH, startM] = selectedSlot.value.split(':').map(Number)
    
    // 计算结束时间 (用于逻辑判断)
    let endM = startM + 30
    let endH = startH
    if (endM >= 60) { endM = 0; endH += 1 }

    // 格式化便于比较的字符串
    const startStr = selectedSlot.value
    const endStr = `${endH.toString().padStart(2,'0')}:${endM.toString().padStart(2,'0')}`

    displayData = historyRawData.value.filter(item => {
      // item.time 格式 "14:35"
      // 简单字符串比较即可: startStr <= time < endStr
      return item.time >= startStr && item.time < endStr
    })
  }

  const times = displayData.map(i => i.time)
  const ups = displayData.map(i => i.up)
  const downs = displayData.map(i => i.down)

  const titleText = selectedSlot.value === 'ALL' 
    ? `${selectedDate.value} 全天流量趋势` 
    : `${selectedDate.value} [${selectedSlot.value} - 30min] 详情`

  chartInstance.setOption({
    title: { text: titleText, textStyle: { color: '#fff' } },
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 60, bottom: 30 },
    xAxis: { data: times },
    yAxis: { type: 'value' },
    series: [
      { name: '上传', data: ups, type: 'bar', itemStyle: { color: '#ff4d4f' }, barMaxWidth: 30 },
      { name: '下载', data: downs, type: 'bar', itemStyle: { color: '#409EFF' }, barMaxWidth: 30 }
    ]
  })
}

// --- 实时数据获取 ---
const fetchRealtimeData = async () => {
  if(isHistoryMode.value) return
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/dashboard/')
    dashboardData.value = res.data
    updateRealtimeChart(res.data.traffic)
    
    const logWin = document.getElementById('log-window')
    if(logWin) {
      const isScrolledToBottom = logWin.scrollHeight - logWin.clientHeight <= logWin.scrollTop + 50;
      if(isScrolledToBottom) logWin.scrollTop = logWin.scrollHeight
    }
  } catch (e) { console.error(e) }
}

const updateRealtimeChart = (data) => {
  if (!chartInstance) return
  const times = data.map(item => item.time)
  const sent = data.map(item => (item.sent / 1024).toFixed(1))
  const recv = data.map(item => (item.recv / 1024).toFixed(1))

  chartInstance.setOption({
    title: { text: '实时网络吞吐量 (KB/s)', textStyle: { color: '#fff' } },
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 20, textStyle: { color: '#ccc' } },
    grid: { top: 60, bottom: 30, left: 50, right: 30 },
    xAxis: { type: 'category', data: times },
    yAxis: { type: 'value' },
    series: [
      { name: '上传', type: 'line', data: sent, areaStyle: { opacity: 0.2 }, smooth: true, itemStyle: { color: '#ff4d4f' } },
      { name: '下载', type: 'line', data: recv, areaStyle: { opacity: 0.2 }, smooth: true, itemStyle: { color: '#409EFF' } }
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
          <div class="logo-glow">⚡</div><h2>NET SENTRY</h2>
        </div>
        <div class="input-group">
          <input v-model="username" type="text" placeholder="Access ID" class="cyber-input" />
          <input v-model="password" type="password" placeholder="Passcode" class="cyber-input" @keyup.enter="handleAuth"/>
        </div>
        <button @click="handleAuth" class="cyber-btn">{{ isRegisterMode ? 'REGISTER' : 'LOGIN' }}</button>
        <div class="switch-mode" @click="isRegisterMode = !isRegisterMode">{{ isRegisterMode ? '返回登录' : '立即注册' }}</div>
      </div>
    </div>
  </transition>

  <div v-if="isLoggedIn" class="dashboard">
    <header class="top-bar">
      <div class="logo-area"><span class="icon">⚡</span> NET MONITOR</div>
      
      <div class="control-bar">
        <div class="mode-switch">
          <button :class="['mode-btn', !isHistoryMode ? 'active' : '']" @click="startRealtime">实时</button>
          <button :class="['mode-btn', isHistoryMode ? 'active' : '']" @click="showHistory">历史</button>
        </div>

        <template v-if="isHistoryMode">
          <div class="control-group">
            <span class="label-text">DATE_SELECT:</span>
            <div class="date-wrapper">
              <input type="date" v-model="selectedDate" class="cyber-date-picker" @change="showHistory">
            </div>
          </div>
          <div class="control-group">
            <label>时段:</label>
            <select v-model="selectedSlot" class="cyber-select" @change="renderHistoryChart">
              <option value="ALL">全天 (24h)</option>
              <option v-for="slot in timeSlots" :key="slot" :value="slot">{{ slot }} - {{ slot.split(':')[1]=='00'?'30':'00' }}</option>
            </select>
          </div>
        </template>

        <template v-else>
          <select v-model="selectedFilter" class="cyber-select">
            <option value="ALL">ALL</option><option value="TCP">TCP</option><option value="UDP">UDP</option>
          </select>
          <input v-model="thresholdInput" type="number" class="cyber-input-sm" placeholder="MB">
          <button @click="applySettings" class="action-btn">应用</button>
        </template>
      </div>

      <div v-if="dashboardData.alerts.length" class="alert-ticker">⚠️ {{ dashboardData.alerts[dashboardData.alerts.length-1].msg }}</div>
      <button @click="isLoggedIn = false" class="logout-btn">EXIT</button>
    </header>

    <div class="main-content">
      <div class="col-main">
        <div class="panel chart-panel">
          <div id="main-chart" class="chart-container"></div>
        </div>
        
        <div v-if="!isHistoryMode" class="panel device-panel">
          <div class="panel-header"><h3>Active Interfaces</h3><span class="online">ONLINE</span></div>
          <div class="device-grid">
            <div v-for="(ip, name) in dashboardData.devices" :key="name" class="device-card">
              <span class="dev-name">{{ name }}</span>: <span class="dev-ip">{{ ip }}</span>
            </div>
          </div>
        </div>
        
        <div v-else class="panel device-panel">
          <div class="panel-header"><h3>Analysis Mode</h3></div>
          <div class="history-note">
             <p>📅 当前查看日期: <b>{{ selectedDate }}</b></p>
             <p>⏱️ 当前时间切片: <b>{{ selectedSlot === 'ALL' ? '24小时全景' : selectedSlot + ' (30分钟)' }}</b></p>
             <p>📊 数据点总数: {{ historyRawData.length }} (分钟级聚合)</p>
          </div>
        </div>
      </div>

      <div class="col-logs">
        <div class="panel log-panel">
          <div class="panel-header"><h3>{{ isHistoryMode ? 'Cached Logs' : `Sniffer [${selectedFilter}]` }}</h3></div>
          <div id="log-window" class="log-window">
            <div v-for="(log, index) in dashboardData.packets" :key="index" class="log-row">
              <span class="time">{{ log.time }}</span>
              <div class="proto-cell"><span :class="['proto', log.proto]">{{ log.proto }}</span></div>
              <div class="detail">
                <span class="addr src" :title="log.src">{{ log.src }}</span><span class="arrow">→</span><span class="addr dst" :title="log.dst">{{ log.dst }}</span>
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
body, html { margin: 0; background: #050b14; color: #cbd5e1; font-family: 'Segoe UI', sans-serif; height: 100%; overflow: hidden; }
</style>

<style scoped>
/* --- 登录页样式 --- */
.login-wrapper {
  position: fixed; inset: 0; width: 100vw; height: 100vh;
  display: flex; justify-content: center; align-items: center;
  background: #000; z-index: 999;
}
.login-bg-animation {
  position: absolute; inset: 0;
  background: linear-gradient(45deg, #020617, #0f172a, #1e1b4b);
  background-size: 400% 400%; animation: gradientBG 15s ease infinite; z-index: -1;
}
@keyframes gradientBG {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
.login-card {
  width: 380px; padding: 40px;
  background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 12px;
  box-shadow: 0 0 40px rgba(0, 0, 0, 0.6); text-align: center;
}
.brand .logo-glow { font-size: 48px; margin-bottom: 10px; text-shadow: 0 0 20px #3b82f6; }
.brand h2 { margin: 0; color: #fff; letter-spacing: 4px; font-weight: 800; }
.brand .subtitle { color: #64748b; margin-bottom: 30px; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 2px; }
.input-group { margin-bottom: 25px; display: flex; flex-direction: column; gap: 15px; }
.cyber-input {
  width: 100%; padding: 15px; background: rgba(0, 0, 0, 0.3);
  border: 1px solid #334155; border-radius: 4px;
  color: #e2e8f0; outline: none; box-sizing: border-box; transition: border-color 0.3s;
}
.cyber-input:focus { border-color: #3b82f6; background: rgba(0, 0, 0, 0.5); }
.cyber-btn {
  width: 100%; padding: 15px; background: #2563eb; border: none;
  color: white; font-weight: bold; letter-spacing: 2px; cursor: pointer;
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
  transition: all 0.2s;
}
.cyber-btn:hover { background: #1d4ed8; transform: translateY(-2px); box-shadow: 0 0 20px rgba(37, 99, 235, 0.5); }
.switch-mode { margin-top: 20px; color: #64748b; font-size: 0.85rem; cursor: pointer; transition: color 0.3s; }
.switch-mode:hover { color: #3b82f6; text-decoration: underline; }

/* --- 仪表盘布局 --- */
.dashboard {
  position: fixed; inset: 0; width: 100vw; height: 100vh;
  display: flex; flex-direction: column;
  background-color: #0b1120; color: #cbd5e1;
}
.top-bar {
  height: 60px; background: #1e293b; border-bottom: 1px solid #334155;
  display: flex; justify-content: space-between; align-items: center; padding: 0 20px; flex-shrink: 0;
}
.logo-area { display: flex; align-items: center; gap: 10px; color: #fff; font-weight: bold; font-size: 1.2rem; }
.logo-area small { color: #3b82f6; font-size: 0.8em; margin-left: 5px; }

/* 控制栏 */
.control-bar { display: flex; align-items: center; gap: 15px; margin: 0 20px; }
.mode-switch { display: flex; gap: 5px; }
.mode-btn { background: #0f172a; border: 1px solid #334155; color: #aaa; padding: 5px 15px; cursor: pointer; }
.mode-btn.active { background: #2563eb; color: white; border-color: #2563eb; }
.control-group { display: flex; align-items: center; }
.cyber-select, .cyber-input-sm {
  background: #0f172a; border: 1px solid #334155; color: #e2e8f0;
  padding: 5px 8px; border-radius: 4px; outline: none;
}
.cyber-input-sm { width: 60px; text-align: center; }
.action-btn {
  background: #10b981; border: none; color: white; padding: 5px 12px;
  border-radius: 4px; font-weight: bold; cursor: pointer;
}
.alert-ticker {
  background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5; padding: 5px 15px; border-radius: 20px; font-size: 0.9rem;
  display: flex; align-items: center; gap: 8px;
}
.logout-btn {
  background: transparent; border: 1px solid #475569; color: #94a3b8;
  padding: 6px 16px; border-radius: 4px; cursor: pointer; transition: all 0.2s;
}
.logout-btn:hover { border-color: #ef4444; color: #ef4444; }

/* 主内容区 */
.main-content { flex: 1; display: flex; padding: 15px; gap: 15px; overflow: hidden; }
.col-main { flex: 2; display: flex; flex-direction: column; gap: 15px; min-width: 0; }
.col-logs { flex: 1; min-width: 350px; display: flex; flex-direction: column; } /* 增加最小宽度 */

.panel {
  background: #162032; border: 1px solid #283548; border-radius: 8px;
  display: flex; flex-direction: column; overflow: hidden;
}
.panel-header {
  padding: 10px 15px; background: #1e293b; border-bottom: 1px solid #283548;
  display: flex; justify-content: space-between; align-items: center;
}
.panel-header h3 { margin: 0; font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; font-weight: 600; letter-spacing: 1px; }

.chart-panel { flex: 2; position: relative; }
.chart-container { width: 100%; height: 100%; }
.device-panel { flex: 1; overflow-y: auto; }
.history-note { padding: 20px; color: #94a3b8; font-family: monospace; }

.device-grid { padding: 15px; display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
.device-card {
  background: #0f172a; padding: 12px; border-radius: 6px;
  display: flex; align-items: center; gap: 12px; border: 1px solid transparent;
}
.device-card:hover { border-color: #3b82f6; }
.dev-icon { font-size: 1.5rem; color: #64748b; }
.dev-info { display: flex; flex-direction: column; }
.dev-name { font-size: 0.8rem; color: #94a3b8; font-weight: bold; }
.dev-ip { font-size: 0.9rem; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; }

/* --- 修复后的日志窗口 (使用 Grid) --- */
.log-panel { height: 100%; }
.log-window {
  flex: 1; overflow-y: auto; background: #0b1120;
  padding: 0; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
}
.log-row {
  display: grid; 
  grid-template-columns: 70px 50px 1fr 50px; /* 严格列宽 */
  align-items: center; gap: 10px; padding: 6px 10px;
  border-bottom: 1px solid #1e293b;
}
.log-row:hover { background: #1e293b; }

/* 单元格样式 */
.time { color: #64748b; font-size: 0.75rem; }
.proto-cell { display: flex; justify-content: center; }
.proto { 
  font-weight: bold; border-radius: 3px; padding: 1px 4px; font-size: 0.7rem; 
  min-width: 35px; text-align: center;
}
.proto.TCP { color: #60a5fa; background: rgba(96, 165, 250, 0.1); border: 1px solid rgba(96, 165, 250, 0.2); }
.proto.UDP { color: #fbbf24; background: rgba(251, 191, 36, 0.1); border: 1px solid rgba(251, 191, 36, 0.2); }
.proto.IP { color: #a5b4fc; background: rgba(165, 180, 252, 0.1); }

.detail { display: flex; align-items: center; gap: 5px; color: #cbd5e1; overflow: hidden; }
.addr { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100px; }
.src { color: #94a3b8; }
.dst { color: #e2e8f0; }
.arrow { color: #475569; font-size: 0.8em; }
.size { color: #64748b; text-align: right; font-size: 0.75rem; }

/* 滚动条美化 */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0b1120; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.5s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* --- 日期选择器样式 --- */

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #0f172a;
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid #334155;
}

.label-text {
  font-size: 0.75rem;
  color: #64748b;
  font-weight: bold;
  letter-spacing: 1px;
}

.cyber-date-picker {
  background: transparent;
  border: none;
  color: #3b82f6; /* 选中日期的颜色：科技蓝 */
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  font-weight: bold;
  outline: none;
  cursor: pointer;
  
  /* 关键：强制浏览器原生的日历弹窗使用暗黑模式 */
  color-scheme: dark; 
}

/* 鼠标悬停效果 */
.cyber-date-picker:hover {
  color: #60a5fa;
}

/* 定制右侧的“日历小图标” */
.cyber-date-picker::-webkit-calendar-picker-indicator {
  cursor: pointer;
  filter: invert(1); /* 关键：把默认黑图标反转成白色 */
  opacity: 0.6;
  transition: opacity 0.2s;
}

.cyber-date-picker::-webkit-calendar-picker-indicator:hover {
  opacity: 1;
  filter: drop-shadow(0 0 2px #3b82f6); /* 图标发光 */
}
</style>