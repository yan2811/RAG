# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基于 RAG 架构的企业多维度财报智能分析与深度问答知识库系统 —— 毕业设计项目。

## 技术栈

- **前端**: Vue3 + Vite + TypeScript + Element Plus + Pinia + ECharts
- **后端**: Python + FastAPI + Uvicorn
- **数据库**: MySQL 8.0 (端口3307) + ChromaDB (向量存储)
- **AI**: DeepSeek API (双协议支持: OpenAI 兼容 + Anthropic 兼容，通过 base_url 中是否含 "anthropic" 自动切换)
- **Embedding**: BAAI/bge-large-zh-v1.5 (sentence-transformers，懒加载)
- **文档解析**: PyMuPDF + Camelot-py + fpdf2

## 环境搭建

```bash
# 1. 创建虚拟环境
python -m venv .venv && source .venv/Scripts/activate  # Windows
python -m venv .venv && source .venv/bin/activate      # Linux/Mac

# 2. 安装依赖
cd backend && pip install -r requirements.txt
cd frontend && npm install

# 3. 配置环境变量（从模板创建）
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 DEEPSEEK_API_KEY 和数据库密码

# 4. 初始化数据库（创建表 + 默认角色 + admin 账号）
cd backend && python seed.py
```

默认管理员账号: `admin` / `admin123456`

## 启动方式

```bash
# 后端 (端口 8000, API docs: http://localhost:8000/docs)
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 前端 (端口 5173, Vite 代理 /api → localhost:8000)
cd frontend && npm run dev

# 前端构建
cd frontend && npm run build    # vue-tsc 类型检查 + vite build
```

## 数据库连接

- Host: localhost:3307, User: root, Password: 123456, Database: rag_financial, Charset: utf8mb4
- 初始化: `cd backend && python seed.py`（创建表 + 默认角色 + admin 账号）
- MySQL 使用 PyMySQL 驱动 + SQLAlchemy 2.0 ORM（同步引擎，非异步）

## RAG 核心流程

```
PDF上传 → PyMuPDF文本提取 → AI智能分节 → jieba分词分块
→ BGE向量化(1024维) → ChromaDB存储(HNSW,cosine相似度)
→ 用户提问 → 查询改写(HyDE) → 混合检索(向量+BM25+加权融合)
→ 拼接上下文 → DeepSeek流式生成 → SSE推送前端
```

### 混合检索策略 (`search_service.py`)

1. **向量检索**: BGE embedding → ChromaDB cosine 相似度 (默认权重 0.6)
2. **BM25 关键词检索**: jieba 分词 + 自实现 BM25 索引 (默认权重 0.4)
3. **加权融合**: 按来源权重直接加权求和（非标准 RRF），去重排序后取 top_k

### 问答双模式

- **未选文档**: AI 直接回答（不检索知识库）
- **选了文档**: RAG 检索增强 — 先检索相关 chunk，拼入上下文再生成

## API 路由（45+ 接口）

Swagger UI: `http://localhost:8000/docs` | ReDoc: `http://localhost:8000/redoc`

| 路由前缀 | 模块 | 主要接口 |
|---------|------|---------|
| `/api/v1/auth/*` | 认证 | register, login, me |
| `/api/v1/admin/*` | 系统管理 | users CRUD, roles, logs, settings |
| `/api/v1/documents/*` | 文档 | upload, list, detail, delete, fulltext, file(PDF), parse(AI重分节) |
| `/api/v1/knowledge/*` | 知识库 | overview, tags CRUD, index, reindex, stats |
| `/api/v1/chat/{id}` | 问答 | SSE流式问答, sessions CRUD, messages, export, feedback |
| `/api/v1/agent/*` | Agent | analyze(多步推理拆解+并行检索) |
| `/api/v1/dashboard/*` | 仪表盘 | 指标提取, ai-charts(AI图表生成), compare |
| `/api/v1/reports/*` | 报告 | generate(AI逐节生成), list, detail, download(PDF导出) |

## 认证与权限

- JWT Bearer Token（`python-jose` + `bcrypt`，非 passlib）
- 中间件: `get_current_user`（解析 Token） + `require_permission(permission)`（按角色鉴权）
- 角色: super_admin / admin / analyst / viewer（单选 radio）
- super_admin 拥有所有权限，其他角色按 `roles.permissions` JSON 字段判断
- 前端: Pinia 存储 token + Axios 拦截器自动注入 + 401 自动跳登录页

## 关键设计决策

- **LLM 调用双协议**: `llm_service.py` 根据 `DEEPSEEK_BASE_URL` 是否含 "anthropic" 自动选择 OpenAI SDK 或 Anthropic SDK。Anthropic 协议下 system prompt 作为独立参数，messages 只含 user/assistant
- **Embedding 懒加载**: BGE 模型在首次调用 `embed_texts()` 时加载，后续复用全局实例
- **ChromaDB 持久化**: 存储在 `backend/chroma_data/`，collection 名 `financial_reports`，使用 cosine 距离
- **PDF 查看**: 浏览器原生渲染原始 PDF（不做文本转换）
- **财务指标提取**: 优先 DeepSeek AI 智能提取，回退正则表达式
- **报告生成**: 7 章节固定结构，DeepSeek 逐节生成

## 系统模块

| 模块 | 名称 | 功能 |
|------|------|------|
| M1 | 文档智能解析引擎 | PDF上传、PyMuPDF文本提取、AI智能分节、原始PDF直接查看 |
| M2 | 知识库构建与管理 | 向量化、混合检索、标签分类、版本管理 |
| M3 | 智能问答与对话管理 | SSE流式、双模式、溯源标注、多轮对话 |
| M4 | 多步推理 Agent | LLM问题拆解、子任务并行检索、综合分析报告 |
| M5 | 财报分析仪表盘 | AI智能图表、六维雷达、跨公司对比 |
| M6 | AI 报告生成 | 7章节专业报告、Markdown预览、PDF导出 |
| M7 | 系统管理 | JWT认证、RBAC权限(4角色)、操作日志、系统配置、个人主页 |
| M8 | 数据可视化大屏 | 全屏实时数据概览、年度分布、公司覆盖、系统运行状态 |

## 数据库表

13 张表: users, roles, user_roles, documents, chunks, financial_metrics, document_versions, sessions, messages, feedbacks, tags, document_tags, operation_logs, system_settings, reports

## 项目文件结构

```
backend/
├── .env                      # 环境变量（含 DEEPSEEK_API_KEY，从 .env.example 创建）
├── .env.example              # 配置模板
├── seed.py                   # 数据库初始化脚本
├── generate_samples.py       # 示例财报生成+上传
├── uploads/                  # PDF 文件存储
├── chroma_data/              # ChromaDB 持久化
└── app/
    ├── main.py               # FastAPI 入口（8 个路由注册，startup 事件创建表）
    ├── core/                  # config(环境变量), database(SQLAlchemy引擎), security(JWT+bcrypt)
    ├── models/                # 7 个 ORM 模型文件
    ├── schemas/               # Pydantic 请求/响应模型
    ├── middleware/auth.py     # JWT 认证 + RBAC 权限校验
    ├── routers/               # 8 个路由模块 (auth, admin, document, knowledge, chat, agent, dashboard, report)
    └── services/              # 9 个服务层 (document, llm, embedding, vector_store, search, agent, dashboard, report, log)

frontend/
├── package.json, vite.config.ts, tsconfig.json
└── src/
    ├── main.ts, App.vue
    ├── router/index.ts        # 15+ 路由 + 登录守卫（token 检查 + 权限 meta）
    ├── stores/user.ts         # Pinia 用户状态
    ├── utils/request.ts       # Axios 封装（JWT 注入 + 401 跳转 + 错误统一处理）
    ├── api/                   # 按模块拆分的 API 调用（auth, admin, document, knowledge, chat, report）
    ├── components/layout/     # AppLayout（侧边栏 + 顶栏 + 内容区）
    └── views/                 # 页面视图（login, dashboard, documents, knowledge, chat, reports, analytics, admin）
```
