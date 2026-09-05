# Net Monitor Pro · 网络性能监测工具

> 一个前后端分离的实时网络监测平台：后端基于 **Django + Scapy + psutil** 采集流量与抓取数据包，
> 前端基于 **Vue 3 + Vite + ECharts** 呈现赛博朋克风格的实时仪表盘，支持登录鉴权、
> 实时吞吐曲线、数据包嗅探、阈值告警与历史流量回溯。

---

## ✨ 功能特性

- **实时吞吐监控**：每秒采集上下行流量，前端 1s 轮询绘制动态曲线（KB/s）
- **数据包嗅探**：基于 Scapy 抓包，按 `ALL / TCP / UDP` 协议过滤，滚动展示源/目的地址与包长
- **阈值告警**：可在线设置流量阈值（MB/s），超阈值实时告警
- **历史回溯**：每分钟聚合入库、保留 30 天；按日期 + 30 分钟时段切片查看柱状趋势
- **网卡信息**：展示本机活跃网络接口及其 IPv4 地址
- **用户体系**：注册 / 登录，基于 DRF Token 认证

## 🛠 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.10+、Django 5.2、Django REST Framework 3.16、django-cors-headers |
| 采集 | psutil（流量统计）、Scapy（数据包捕获与解析） |
| 数据库 | SQLite（默认，可替换为 PostgreSQL/MySQL） |
| 前端 | Vue 3、Vite、ECharts、Axios、Element Plus |
| 运行环境 | 推荐 Linux / WSL（Scapy 抓包需要原始套接字权限） |

## 🧭 系统架构

```
┌────────────────────────┐         HTTP/JSON          ┌─────────────────────────────┐
│   前端 Vue3 + Vite      │  ───────────────────────►  │   后端 Django + DRF          │
│   (localhost:5173)      │   登录/仪表盘/历史/设置     │   (localhost:8000)           │
│                         │  ◄───────────────────────  │                             │
│  ECharts 实时/历史图表   │        1s 轮询              │  api/views.py  接口层        │
│  抓包日志 · 网卡 · 告警  │                            │  api/monitor.py 采集层       │
└────────────────────────┘                            │   ├─ 流量线程 (psutil)       │
                                                        │   └─ 抓包线程 (Scapy)        │
                                                        │  SQLite: TrafficRecord       │
                                                        └─────────────────────────────┘
```

采集层由两个后台守护线程组成：
- **流量线程**：每秒读取 `psutil.net_io_counters()` 计算增量，写入内存环形队列（最近 60 秒）；每满 60 秒计算平均 KB/s 落库，并清理 30 天前的旧记录；同时做阈值告警检测。
- **抓包线程**：`scapy.sniff()` 捕获数据包，按协议过滤后写入内存队列（最近 100 条）。

## 📁 项目结构

```
net_moniter_pro/
├── backend/                    # Django 后端（项目根）
│   ├── manage.py
│   ├── api/                    # 核心应用
│   │   ├── monitor.py          # 流量监控 + 数据包嗅探（双线程）
│   │   ├── views.py            # DRF 接口：登录/注册/仪表盘/历史
│   │   ├── models.py           # TrafficRecord 数据模型
│   │   ├── admin.py / apps.py
│   │   └── migrations/
│   └── config/                 # Django 配置
│       ├── settings.py         # 支持环境变量注入密钥/调试/主机
│       ├── urls.py             # 路由
│       └── wsgi.py / asgi.py
├── frontend/                   # Vue3 + Vite 前端
│   ├── src/
│   │   ├── App.vue             # 单页应用（登录 + 仪表盘 + 历史）
│   │   ├── main.js / style.css
│   │   └── assets/
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── requirements.txt            # 后端依赖（固定版本）
├── .env.example                # 环境变量示例
├── .gitignore
└── README.md
```

## 🚀 快速开始

### 0. 环境准备

- Python 3.10+
- Node.js 18+（前端）
- Linux / WSL 环境（抓包功能需要；Windows 原生需安装 Npcap 且以管理员运行）

### 1. 启动后端

```bash
# 进入项目根目录，创建并激活虚拟环境
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（可选，开发环境有默认值）
cp .env.example .env                # 按需修改；Django 需在启动前导出这些变量

# 进入后端目录，迁移数据库并创建管理员
cd backend
python manage.py migrate
python manage.py createsuperuser

# 启动开发服务器（抓包需要 root 权限）
sudo ../venv/bin/python manage.py runserver 0.0.0.0:8000
```

> **关于抓包权限**：Scapy 的 `sniff()` 依赖原始套接字，Linux/WSL 下通常需要 `sudo`。
> 若默认网卡抓不到包，请设置环境变量指定网卡，例如 `export NET_MONITOR_IFACE=eth0`。

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev                         # 默认 http://localhost:5173
```

打开浏览器访问 `http://localhost:5173`，注册账号后即可进入仪表盘。

## ⚙️ 配置说明

后端支持通过环境变量配置（见 `.env.example`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DJANGO_SECRET_KEY` | 开发占位密钥 | **生产环境必须**替换为随机密钥 |
| `DJANGO_DEBUG` | `True` | 生产环境请设为 `False` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | 逗号分隔的允许主机列表 |
| `NET_MONITOR_IFACE` | 空（scapy 默认网卡） | 指定抓包网卡，如 `eth0` |

前端跨域已在 `backend/config/settings.py` 的 `CORS_ALLOWED_ORIGINS` 中放行 `http://localhost:5173`；
若前端部署地址不同，请同步修改。

## 🔌 API 接口

基础地址：`http://localhost:8000`

| 方法 | 路径 | 说明 | 请求体 / 参数 | 返回 |
|------|------|------|----------------|------|
| POST | `/api/register/` | 用户注册 | `{username, password}` | `{token, msg}` 或 `{error}` |
| POST | `/api/login/` | 用户登录 | `{username, password}` | `{token}` 或 `{error}` |
| GET | `/api/dashboard/` | 实时仪表盘数据 | — | `{traffic[], packets[], alerts[], devices{}, settings{}}` |
| POST | `/api/dashboard/` | 下发控制指令 | `{action, value}` | `{msg}` 或 `{error}` |
| GET | `/api/history/?date=YYYY-MM-DD` | 历史流量（按天） | `date` 可选，默认今天 | `[{time, up, down}]` |

**控制指令（POST `/api/dashboard/`）**：
- `{"action": "set_threshold", "value": 5.0}` —— 设置告警阈值（MB/s）
- `{"action": "set_filter", "value": "TCP"}` —— 设置抓包过滤器（`ALL` / `TCP` / `UDP`）

**仪表盘返回字段**：
- `traffic`：最近 60 秒 `{time, sent, recv}`（sent/recv 单位：字节/秒）
- `packets`：最近 100 条 `{time, src, dst, proto, len}`
- `alerts`：最近告警 `{time, msg}`
- `devices`：`{网卡名: IPv4}`
- `settings`：当前 `{threshold, filter}`（供前端回显）

## 🗄 数据模型

`TrafficRecord`（每分钟一条聚合记录，保留 30 天）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | DateTime | 记录时间（自动） |
| `upload_speed` | Float | 该分钟平均上传速度（KB/s） |
| `download_speed` | Float | 该分钟平均下载速度（KB/s） |

## ❓ 常见问题

**Q：抓包日志一直为空？**
A：① 确认以 `sudo`/管理员权限运行；② 用 `NET_MONITOR_IFACE` 指定正确网卡（`ip addr` 或 `ifconfig` 查看）；③ Windows 原生需安装 [Npcap](https://npcap.com/)，推荐直接用 WSL。

**Q：前端请求报跨域或连不上后端？**
A：确认后端在 `8000` 端口运行，且 `CORS_ALLOWED_ORIGINS` 含前端地址（默认 `localhost:5173`）。前端接口地址硬编码为 `http://127.0.0.1:8000`，如后端不在本机请自行调整 `frontend/src/App.vue`。

**Q：历史图表没有数据？**
A：历史数据按“每分钟”聚合入库，需后端持续运行满 1 分钟以上才会有第一条记录。

## 🔒 安全提示

- 生产部署务必通过环境变量设置 `DJANGO_SECRET_KEY` 并将 `DJANGO_DEBUG=False`。
- 不要把 `.env`、数据库文件、虚拟环境提交到仓库（已在 `.gitignore` 中忽略）。
- 首次部署请立即修改默认管理员口令，不要沿用示例口令。

## 🧹 本次工程优化说明

相较早期版本，本分支做了如下整理（不改变对外接口行为）：

- **仓库瘦身**：将误提交的 `venv/`（约 7200 个文件）与 `__pycache__/*.pyc` 移出 Git 跟踪，改用 `requirements.txt` 复现依赖。
- **消除重复**：后端仅保留 `backend/` 一份（此前根目录存在重复副本），结构更清晰。
- **安全加固**：`SECRET_KEY / DEBUG / ALLOWED_HOSTS` 改为环境变量注入；移除仓库中的明文口令记录。
- **健壮性**：抓包网卡由硬编码 `eth0` 改为可配置（`NET_MONITOR_IFACE`），错误输出由 `print` 改为标准 `logging`。

## 📄 License

本项目供学习与研究使用。抓包功能请仅在获得授权的网络与主机上使用，遵守当地法律法规。
