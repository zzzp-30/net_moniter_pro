import logging
import os
import threading
import time
from collections import deque                 # 双端队列，用于高效的流量数据存储和管理
from datetime import timedelta

import psutil                                 # 系统网络流量监控，用于获取实时收发字节数
from django.utils import timezone
from scapy.all import sniff, IP, TCP, UDP     # 网络数据包捕获与解析

# 引入 Django 模型（需确保 App 已加载）
from .models import TrafficRecord

logger = logging.getLogger(__name__)

# 抓包网卡：优先读环境变量 NET_MONITOR_IFACE；未设置则为 None，交给 scapy 自动选择默认网卡。
# 说明：原实现硬编码为 "eth0"，在 Windows 或部分 Linux 上不存在该网卡会导致抓包线程直接失败，
# 现改为可配置以提升跨平台健壮性（例如在 WSL 中可设置 NET_MONITOR_IFACE=eth0）。
SNIFF_IFACE = os.environ.get("NET_MONITOR_IFACE") or None

traffic_data = deque(maxlen=60)   # 内存中保留最近 60 秒数据，用于实时展示
packet_logs = deque(maxlen=100)   # 内存中保留最近 100 条数据包日志
alerts = deque(maxlen=10)         # 内存中保留最近 10 条报警信息


class NetworkMonitor:
    def __init__(self):
        self.running = False
        self.threshold_mb = 2.0      # 流量报警阈值（MB/s）
        self.packet_filter = 'ALL'   # 抓包过滤器：ALL / TCP / UDP
        self.history_counter = 0     # 计时器（累计秒数）
        self.temp_up = 0             # 累积上传量（字节）
        self.temp_down = 0           # 累积下载量（字节）

    def start(self):
        """启动监控（幂等：已运行则不重复启动）"""
        if not self.running:
            self.running = True
            # 宏观流量监控线程（含速度报警）
            threading.Thread(target=self._monitor_traffic, daemon=True).start()
            # 微观数据包捕获线程
            threading.Thread(target=self._sniff_packets, daemon=True).start()
            logger.info("NetworkMonitor 已启动，抓包网卡: %s", SNIFF_IFACE or "默认(scapy conf.iface)")

    def _monitor_traffic(self):
        last_io = psutil.net_io_counters()  # 初始流量数据
        while self.running:
            time.sleep(1)
            curr_io = psutil.net_io_counters()  # 当前流量数据
            sent = curr_io.bytes_sent - last_io.bytes_sent  # 本秒上传（字节）
            recv = curr_io.bytes_recv - last_io.bytes_recv  # 本秒下载（字节）

            # 1. 实时数据处理
            timestamp = time.strftime("%H:%M:%S")
            traffic_data.append({'time': timestamp, 'sent': sent, 'recv': recv})

            # 2. 累积数据（用于历史存库）
            self.temp_up += sent
            self.temp_down += recv
            self.history_counter += 1

            # 3. 每 60 秒存一次数据库
            if self.history_counter >= 60:
                try:
                    avg_up = (self.temp_up / 60) / 1024    # 转换为 KB/s
                    avg_down = (self.temp_down / 60) / 1024

                    # A. 保存新数据
                    TrafficRecord.objects.create(
                        upload_speed=round(avg_up, 2),
                        download_speed=round(avg_down, 2)
                    )

                    # B. 数据清洗：删除 30 天前的记录
                    retention_limit = timezone.now() - timedelta(days=30)
                    TrafficRecord.objects.filter(timestamp__lt=retention_limit).delete()

                except Exception as e:
                    logger.error("数据存储/清理失败: %s", e)

                # 重置计数器
                self.history_counter = 0
                self.temp_up = 0
                self.temp_down = 0

            # 4. 阈值报警检测
            total_speed_mb = (sent + recv) / 1024 / 1024  # 转换为 MB/s
            if total_speed_mb > self.threshold_mb:
                alerts.append({
                    'time': timestamp,
                    'msg': f"高负载警报: {total_speed_mb:.2f} MB/s (阈值: {self.threshold_mb})"
                })

            last_io = curr_io

    def _sniff_packets(self):
        def process(pkt):
            if IP in pkt:
                # 功能 3：逻辑过滤 —— 基本协议分类
                proto = "TCP" if TCP in pkt else "UDP" if UDP in pkt else "IP"

                # 如果过滤器不是 ALL，且协议不匹配，则丢弃
                if self.packet_filter != 'ALL' and proto != self.packet_filter:
                    return

                packet_logs.append({
                    'time': time.strftime("%H:%M:%S"),
                    'src': pkt[IP].src,
                    'dst': pkt[IP].dst,
                    'proto': proto,
                    'len': len(pkt)
                })

        try:
            # store=False 避免内存溢出；iface 为 None 时由 scapy 选择默认网卡
            sniff(iface=SNIFF_IFACE, prn=process, store=False)
        except Exception as e:
            # 抓包通常需要 root/管理员权限；失败时记录日志而非中断整个服务
            logger.error("抓包启动失败（可能需要 root/管理员权限，或设置 NET_MONITOR_IFACE 指定网卡）: %s", e)


monitor = NetworkMonitor()
