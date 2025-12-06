"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from api.views import RegisterView,LoginView, DashboardDataView, HistoryReportView 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/login/', LoginView.as_view()),           #登录路由
    path('api/register/', RegisterView.as_view()),     #注册路由
    path('api/dashboard/', DashboardDataView.as_view()), # 仪表盘数据路由
    path('api/history/', HistoryReportView.as_view()), # 历史记录路由
]