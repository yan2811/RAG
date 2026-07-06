"""
FastAPI 应用入口
启动命令: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db, SessionLocal
from app.routers import auth, admin, document, knowledge, chat, agent, dashboard, report
from app.services.search_service import rebuild_bm25_from_db

# ===== 创建 FastAPI 应用实例 =====
app = FastAPI(
    title="财报 RAG 知识库系统 API",
    description="基于 RAG 架构的企业多维度财报智能分析与深度问答知识库系统",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI 文档地址
    redoc_url="/redoc",     # ReDoc 文档地址
)

# ===== CORS 跨域配置 =====
# 开发阶段允许所有来源，生产环境应限制具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                    # 生产环境改为具体域名
    allow_credentials=True,
    allow_methods=["*"],                    # 允许所有 HTTP 方法
    allow_headers=["*"],                    # 允许所有请求头
)

# ===== 注册路由 =====
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(document.router)
app.include_router(knowledge.router)
app.include_router(chat.router)
app.include_router(agent.router)
app.include_router(dashboard.router)
app.include_router(report.router)


@app.on_event("startup")
def startup_event():
    """
    应用启动事件：初始化数据库表结构
    仅在表不存在时创建，不会修改已有表
    """
    try:
        init_db()
        print("[INFO] 数据库表初始化完成")
    except Exception as e:
        print(f"[ERROR] 数据库初始化失败: {e}")

    # 启动时从数据库重建 BM25 索引（重试 2 次）
    for attempt in range(2):
        db = None
        try:
            db = SessionLocal()
            # 先做一次简单查询确认数据库连接正常
            from app.models.document import Document
            doc_count = db.query(Document).filter(Document.is_deleted == 0).count()
            print(f"[INFO] 检测到 {doc_count} 份文档，开始重建 BM25 索引...")
            count = rebuild_bm25_from_db(db)
            print(f"[INFO] BM25 索引重建完成：{count} 个分块已加载")
            break  # 成功就退出重试循环
        except Exception as e:
            import traceback
            print(f"[WARN] BM25 索引构建失败(第{attempt+1}次): {e}")
            traceback.print_exc()
            if attempt == 1:
                print("[ERROR] BM25 索引重建彻底失败，RAG 检索将不可用。请检查数据库连接和文档解析状态。")
        finally:
            if db:
                db.close()


@app.get("/", summary="健康检查")
def root():
    """系统健康检查接口"""
    return {
        "code": 0,
        "msg": "财报 RAG 知识库系统运行中",
        "version": "1.0.0",
    }


@app.get("/api/v1/health", summary="系统健康检查")
def health_check():
    """返回系统运行状态"""
    return {
        "code": 0,
        "status": "healthy",
        "service": "rag-financial-analysis",
    }
