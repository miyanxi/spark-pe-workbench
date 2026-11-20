"""
SPARK 备课工作台启动脚本
"""
import uvicorn
import os
import sys

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("="*50)
    print("SPARK 备课工作台 启动中...")
    print("="*50)
    print()
    print("访问地址：http://localhost:8000")
    print("API文档：http://localhost:8000/docs")
    print()
    print("按 Ctrl+C 停止服务")
    print("="*50)
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False
    )
