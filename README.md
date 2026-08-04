网络性能监测工具 (Net Monitor Pro)
这是一个功能强大的网络性能监测工具，主要用于网络抓包分析与数据日志记录。项目采用了前后端分离的架构设计，确保了高效的网络数据处理与流畅的用户交互体验。

🛠 技术栈
后端 (Backend): Python, Django (提供 API 接口), Scapy (用于网络抓包), Speedtest。  
前端 (Frontend): JavaScript, Vue.js, Vite。  
运行环境: 兼容 Linux 及 WSL 环境，便于执行底层网络指令。

📁 项目结构
api/ & backend/ & config/: Django 后端应用逻辑、路由配置、数据模型以及核心设置。  
frontend/: 基于 Vue 的前端源代码，包含应用组件 (src/components/)、入口文件 (src/main.js) 与全局样式 (src/style.css)。  
venv/: 预设的 Python 虚拟环境，包含了项目所需的所有依赖库（如 django, corsheaders, scapy, speedtest-cli 等）。  
manage.py: Django 项目的命令行管理脚本。  
frontend/vite.config.js & package.json: 前端项目的 Vite 构建配置与 npm 依赖管理。 

🚀 快速启动
后端服务
激活虚拟环境：source venv/bin/activate
运行数据库迁移：python manage.py migrate
启动 Django 开发服务器：python manage.py runserver
前端服务
进入前端目录：cd frontend
安装依赖：npm install
启动 Vite 开发服务器：npm run dev


