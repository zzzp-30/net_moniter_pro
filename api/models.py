from django.db import models

class TrafficRecord(models.Model):
    # 记录时间
    timestamp = models.DateTimeField(auto_now_add=True)
    # 上传速度 (KB/s)
    upload_speed = models.FloatField()
    # 下载速度 (KB/s)
    download_speed = models.FloatField()

    def __str__(self):
        return f"{self.timestamp}: Up {self.upload_speed} / Down {self.download_speed}"