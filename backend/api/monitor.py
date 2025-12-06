import threading
import time
import psutil
from collections import deque
from scapy.all import sniff, IP, TCP, UDP

traffic_data = deque(maxlen=20)
packet_logs = deque(maxlen=50)
alerts = deque(maxlen=10)

class NetworkMonitor:
    def __init__(self):
        self.running = False
        # --- 功能 4: 动态阈值变量 (默认 2MB/s) ---
        self.threshold_mb = 2.0 
        # --- 功能 3: 动态过滤器变量 (默认全部) ---
        self.packet_filter = 'ALL' 

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
            
            timestamp = time.strftime("%H:%M:%S")
            traffic_data.append({'time': timestamp, 'sent': sent, 'recv': recv})
            
            # --- 功能 4 实现: 使用动态阈值进行判断 ---
            total_speed_mb = (sent + recv) / 1024 / 1024
            if total_speed_mb > self.threshold_mb:
                alerts.append({
                    'time': timestamp, 
                    'msg': f"高负载警报: 当前 {total_speed_mb:.2f} MB/s (阈值: {self.threshold_mb} MB)"
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