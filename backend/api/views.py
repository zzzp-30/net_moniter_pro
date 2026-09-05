from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .monitor import monitor, traffic_data, packet_logs, alerts
import psutil
from .models import TrafficRecord
from django.utils import timezone
from django.utils.timezone import localtime, now
from datetime import timedelta, datetime
import logging

logger = logging.getLogger(__name__)

# 确保监控启动（模块加载时启动后台监控线程）
monitor.start()

# --- 功能 1 实现: 历史记录接口 ---
class HistoryReportView(APIView):
    def get(self, request):
        # 1. 获取前端传来的日期参数 (格式 YYYY-MM-DD)
        date_str = request.query_params.get('date')
        
        if not date_str:
            # 如果没传，默认查“今天”
            target_date = localtime(now()).date()
        else:
            try:
                # 解析字符串为日期对象
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "日期格式错误"}, status=400)

        # 2. 数据库查询：使用 __date 过滤器直接匹配那一天的数据
        records = TrafficRecord.objects.filter(timestamp__date=target_date).order_by('timestamp')
        
        data = []
        for r in records:
            # 转为本地时间字符串 "10:30"
            local_dt = localtime(r.timestamp)
            data.append({
                'time': local_dt.strftime("%H:%M"), 
                'up': r.upload_speed,
                'down': r.download_speed
            })
            
        return Response(data)
# --- 功能 2 实现: 用户注册接口 ---
class RegisterView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({"error": "用户名和密码不能为空"}, status=400)
        
        if User.objects.filter(username=username).exists():
            return Response({"error": "用户名已存在"}, status=400)
            
        # 创建新用户
        user = User.objects.create_user(username=username, password=password)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "msg": "注册成功"})

# --- 功能 3 实现: 登录接口 ---
class LoginView(APIView):
    def post(self, request):
        user = authenticate(username=request.data.get('username'), password=request.data.get('password'))
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({"token": token.key})
        return Response({"error": "认证失败"}, status=400)

# --- 功能 4 实现: 数据与控制接口 ---
class DashboardDataView(APIView):
    def get(self, request):
        # 获取设备信息
        interfaces = {}
        for name, addrs in psutil.net_if_addrs().items():
            ip = [a.address for a in addrs if a.family.name == 'AF_INET']
            if ip: interfaces[name] = ip[0]

        return Response({
            "traffic": list(traffic_data),
            "packets": list(packet_logs),
            "alerts": list(alerts),
            "devices": interfaces,
            # 返回当前设置状态供前端回显
            "settings": {
                "threshold": monitor.threshold_mb,
                "filter": monitor.packet_filter
            }
        })

    # 接收前端的设置指令 (功能 4 & 5)
    def post(self, request):
        action = request.data.get('action')
        value = request.data.get('value')
        
        if action == 'set_threshold':
            try:
                monitor.threshold_mb = float(value)
                return Response({"msg": f"阈值已更新为 {value} MB/s"})
            except (ValueError, TypeError):
                logger.warning("设置阈值失败，无效数值: %r", value)
                return Response({"error": "无效数值"}, status=400)
        
        elif action == 'set_filter':
            monitor.packet_filter = value # 'ALL', 'TCP', 'UDP'
            return Response({"msg": f"抓包过滤器已更新为 {value}"})
            
        return Response({"error": "未知指令"}, status=400)
    
