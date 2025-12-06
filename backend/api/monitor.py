import threading
import time
import psutil
from collections import deque
from scapy.all import sniff, IP, TCP, UDP
# 引入 Django 模型 (需要放在函数内部或确保 App 已加载)
from .models import TrafficRecord 
from django.utils import timezone
from datetime import timedelta


traffic_data = deque(maxlen=60) # 内存中保留最近60秒用于实时展示
packet_logs = deque(maxlen=100)
alerts = deque(maxlen=10)

class NetworkMonitor:
    def __init__(self):
        self.running = False
        self.threshold_mb = 2.0 
        self.packet_filter = 'ALL' 
        self.history_counter = 0     # 计时器
        self.temp_up = 0             # 累积上传量
        self.temp_down = 0           # 累积下载量

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self._monitor_traffic, daemon=True).start()
            threading.Thread(target=self._sniff_packets, daemon=True).start()

    def _monitor_traffic(self):
        last_io = psutil.net_io_counters()
        while self.running:
            time.sleep(1)
            curr_io = psutil.net_io_counters()
            sent = curr_io.bytes_sent - last_io.bytes_sent
            recv = curr_io.bytes_recv - last_io.bytes_recv
            
            # 1. 实时数据处理
            timestamp = time.strftime("%H:%M:%S")
            traffic_data.append({'time': timestamp, 'sent': sent, 'recv': recv})
            
            # 2. 累积数据 (用于历史存库)
            self.temp_up += sent
            self.temp_down += recv
            self.history_counter += 1

            # 3. 每60秒存一次数据库
            if self.history_counter >= 60:
                try:
                    avg_up = (self.temp_up / 60) / 1024
                    avg_down = (self.temp_down / 60) / 1024
                    
                    # A. 保存新数据
                    TrafficRecord.objects.create(
                        upload_speed=round(avg_up, 2),
                        download_speed=round(avg_down, 2)
                    )
                    
                    # B. [新增] 数据清洗：删除 30 天前的记录
                    # 计算30天前的时刻
                    retention_limit = timezone.now() - timedelta(days=30)
                    # 执行删除指令
                    TrafficRecord.objects.filter(timestamp__lt=retention_limit).delete()
                    
                except Exception as e:
                    print(f"数据存储/清理失败: {e}")
                
                # 重置计数器
                self.history_counter = 0
                self.temp_up = 0
                self.temp_down = 0
                
            # 4. 阈值报警检测
            total_speed_mb = (sent + recv) / 1024 / 1024
            if total_speed_mb > self.threshold_mb:
                alerts.append({
                    'time': timestamp, 
                    'msg': f"高负载警报: {total_speed_mb:.2f} MB/s (阈值: {self.threshold_mb})"
                })
            
            last_io = curr_io

    def _sniff_packets(self):
        def process(pkt):
            if IP in pkt:
                # --- 功能 3 实现: 逻辑过滤 ---
                proto = "TCP" if TCP in pkt else "UDP" if UDP in pkt else "IP"
                
                # 如果过滤器不是 ALL，且协议不匹配，则丢弃
                if self.packet_filter != 'ALL' and proto != self.packet_filter:
                    return

                log = {
                    'time': time.strftime("%H:%M:%S"),
                    'src': pkt[IP].src,
                    'dst': pkt[IP].dst,
                    'proto': proto,
                    'len': len(pkt)
                }
                packet_logs.append(log)
        
        try:
            # store=False 避免内存溢出
            sniff(iface="eth0", prn=process, store=False)
        except Exception as e:
            print(f"Sniffer Error: {e}")

monitor = NetworkMonitor()