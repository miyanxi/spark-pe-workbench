"""
SPARK 备课工作台 - FastAPI主程序
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

# 创建FastAPI应用
app = FastAPI(
    title="SPARK 备课工作台",
    description="面向中小学体育教师的智能备课与学情分析演示平台",
    version="1.0.0"
)

# 配置CORS（跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入路由
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from routers import classes, students, analysis, knowledge, training, lesson, reports
from deepseek_client import DeepSeekAPIError

# 注册路由
app.include_router(classes.router, prefix="/api/classes", tags=["班级管理"])
app.include_router(students.router, prefix="/api/students", tags=["学生档案"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["学情分析"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
app.include_router(training.router, prefix="/api/training", tags=["训练方案"])
app.include_router(lesson.router, prefix="/api/lesson", tags=["智能备课"])
app.include_router(reports.router, prefix="/api/reports", tags=["报告生成"])


@app.exception_handler(DeepSeekAPIError)
async def deepseek_error_handler(_request, exc: DeepSeekAPIError):
    """把模型服务错误转换成前端可理解的提示。"""
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    from database import init_db
    from config import UPLOAD_PATH, EXPORT_PATH

    init_db()
    os.makedirs(UPLOAD_PATH, exist_ok=True)
    os.makedirs(EXPORT_PATH, exist_ok=True)
    print("[OK] SPARK 备课工作台已启动")


@app.get("/api/init-demo")
async def init_demo_data():
    """初始化演示数据"""
    from init_demo_data import load_demo_data
    result = load_demo_data()
    return result


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


# ---- 静态前端服务 ----

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# 挂载静态资源目录（CSS/JS/图片等）
assets_dir = os.path.join(FRONTEND_DIR, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
async def serve_index():
    """返回前端首页"""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """
    SPA回退：所有非API路径返回index.html
    （API路径以 /api 开头，不会被匹配到这里）
    """
    # 如果是已注册的API路径，交给FastAPI处理
    if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")

    # 尝试返回静态文件
    frontend_root = os.path.abspath(FRONTEND_DIR)
    file_path = os.path.abspath(os.path.join(frontend_root, full_path))
    is_inside_frontend = file_path.startswith(frontend_root + os.sep)
    if is_inside_frontend and os.path.isfile(file_path):
        return FileResponse(file_path)

    # 回退到index.html
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)

    return {"message": "欢迎使用 SPARK 备课工作台", "version": "1.0.0", "docs": "/docs"}
