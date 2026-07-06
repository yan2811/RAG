# 基于 RAG 架构的企业多维度财报智能分析与深度问答知识库系统

> 本科毕业设计项目 | 中国国际大学生创新大赛（2025）产业赛道（中联企业管理集团命题）

![Tech Stack](https://img.shields.io/badge/Python-3.10+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green) ![Vue3](https://img.shields.io/badge/Vue-3.x-brightgreen) ![MySQL](https://img.shields.io/badge/MySQL-8.0-orange) ![DeepSeek](https://img.shields.io/badge/AI-DeepSeek_V4_Pro-purple)

一个全栈 RAG 知识库系统，支持用户上传财报 PDF 进行智能问答与分析。核心创新点：混合检索（向量语义 + BM25 关键词加权融合）、AI Agent 多步推理、数据溯源标注。

---

## 系统架构

```
┌──────────────────────────────────────────────────┐
│              Vue3 + Element Plus                   │  前端
│         Pinia 状态管理 + ECharts 可视化            │
└────────────────────┬─────────────────────────────┘
                     │ REST API + SSE 流式
┌────────────────────┴─────────────────────────────┐
│              FastAPI + Uvicorn                    │  后端
│   JWT 认证 + RBAC 权限 + 图形验证码                │
│   ┌──────────┬──────────┬──────────┐             │
│   │ 文档解析  │ 混合检索  │ AI Agent │  9 个服务   │
│   │ PyMuPDF  │ 向量+BM25│ 多步推理  │             │
│   └──────────┴──────────┴──────────┘             │
└────────┬──────────────────────┬─────────────────┘
         │                      │
┌────────┴────────┐  ┌──────────┴──────────┐
│   MySQL 8.0     │  │  ChromaDB 向量库    │   数据层
│   (15 张表)     │  │  (HNSW, cosine)     │
└─────────────────┘  └─────────────────────┘
         │                      │
         └──────────┬───────────┘
                    │
          ┌─────────┴─────────┐
          │  DeepSeek-V4-Pro  │                  AI 引擎
          │  (双协议兼容)      │
          └───────────────────┘
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue3 + Vite + TypeScript + Element Plus + Pinia + ECharts |
| 后端 | Python + FastAPI + Uvicorn + SQLAlchemy 2.0 |
| 数据库 | MySQL 8.0（结构化数据）+ ChromaDB（向量存储） |
| AI | DeepSeek-V4-Pro（OpenAI/Anthropic 双协议自适应） |
| Embedding | BAAI/bge-large-zh-v1.5（sentence-transformers，懒加载） |
| 文档解析 | PyMuPDF + Camelot-py |
| 安全 | JWT + bcrypt + RBAC 四级权限 + 图形验证码 |

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0

### 1. 后端搭建

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/Scripts/activate  # Windows
source .venv/bin/activate      # Linux/Mac

# 安装依赖
cd backend
pip install -r requirements.txt

# 配置环境变量（从模板创建）
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 和数据库密码
```

### 2. 初始化数据库

```bash
cd backend
python seed.py
# 创建 15 张表 + 4 个角色 + 默认管理员账号

# 默认管理员：admin / admin123456
```

### 3. 启动服务

```bash
# 后端 (端口 8000, Swagger: http://localhost:8000/docs)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 前端 (端口 5173, Vite 代理 /api → localhost:8000)
cd frontend
npm install
npm run dev
```

---

## RAG 核心流程

```
PDF上传 → PyMuPDF文本提取 → 正则切分章节 + Camelot表格提取
→ BGE向量化(1024维) → ChromaDB存储(HNSW, cosine)
→ 用户提问 → 查询改写(规则+LLM双层)
→ 混合检索(向量0.6 + BM25 0.4) → 加权融合
→ 拼接上下文 → DeepSeek流式生成 → SSE推送前端
```

### 混合检索策略

1. **向量检索**：BGE embedding → ChromaDB cosine 相似度（权重 0.6）
2. **BM25 关键词检索**：jieba 分词 + 自实现 BM25 索引（权重 0.4）
3. **加权融合**：按 chunk_id 去重，分数加权叠加，排序取 top_k

### 问答双模式

- **未选文档**：纯 AI 模式，基于 LLM 自身知识直接回答
- **已选文档**：RAG 检索增强模式，先检索再生成，标注来源章节和页码

### AI Agent 多步推理

复杂问题自动拆解 → 子问题并行检索 → 交叉验证 → 综合报告生成

---

## 系统功能模块

| 编号 | 模块 | 核心功能 |
|------|------|---------|
| M1 | 文档智能解析引擎 | PDF上传、PyMuPDF文本提取、AI智能分节、表格提取 |
| M2 | 知识库构建与管理 | 向量化(BGE)、混合检索、标签分类、版本管理 |
| M3 | 智能问答与对话 | SSE流式、双模式、溯源标注、5轮多轮对话 |
| M4 | 多步推理 Agent | LLM问题拆解→子任务并行检索→综合报告 |
| M5 | 财报分析仪表盘 | AI智能图表生成、六维雷达图、跨公司对比 |
| M6 | AI 报告生成 | 7章节专业报告、逐节LLM生成、Markdown/PDF导出 |
| M7 | 系统管理 | JWT认证、RBAC四级权限、操作日志审计 |
| M8 | 数据可视化大屏 | 全屏实时监控、60秒自动刷新、KPI卡片 |

---

## API 接口（55+）

Swagger UI: `http://localhost:8000/docs`

| 路由前缀 | 模块 | 主要接口 |
|---------|------|---------|
| `/api/v1/auth/*` | 认证 | 验证码、注册、登录、个人信息 |
| `/api/v1/admin/*` | 系统管理 | 用户CRUD、角色管理、操作日志、系统配置 |
| `/api/v1/documents/*` | 文档管理 | 上传、列表、详情、删除、AI智能分节、PDF阅读 |
| `/api/v1/knowledge/*` | 知识库 | 概览、标签管理、向量索引、统计 |
| `/api/v1/chat/{id}` | 智能问答 | SSE流式问答、会话CRUD、历史导出、反馈 |
| `/api/v1/agent/*` | Agent | 多步推理分析 |
| `/api/v1/dashboard/*` | 仪表盘 | AI图表生成、跨公司对比、可视化大屏 |
| `/api/v1/reports/*` | 报告 | AI生成、列表、详情、PDF下载、批量导出 |

---

## 数据库设计（15 张表）

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| users | 用户 | id, username, password_hash, email, status |
| roles | 角色 | id, name, permissions(JSON) |
| user_roles | 用户-角色关联 | user_id, role_id |
| documents | 文档元数据 | id, file_name, company_code, fiscal_year, parse_status |
| chunks | 文档分块 | id, document_id, chunk_type, section_title, content, chroma_id |
| financial_metrics | 财务指标 | id, document_id, metric_name, metric_value, yoy_change |
| sessions | 对话会话 | id, user_id, session_title |
| messages | 对话消息 | id, session_id, role, content, sources(JSON) |
| feedbacks | 消息反馈 | id, message_id, rating, reason |
| tags | 标签 | id, name, color |
| document_tags | 文档-标签关联 | document_id, tag_id |
| operation_logs | 操作日志 | id, user_id, action, target_type, detail(JSON) |
| system_settings | 系统配置 | id, setting_key, setting_value |
| reports | 生成报告 | id, user_id, company_code, content_md, file_path |
| document_versions | 文档版本 | id, document_id, version_number, file_path |

---

## 关键设计决策

- **LLM 双协议**：`llm_service.py` 根据 base_url 自动选择 OpenAI SDK 或 Anthropic SDK
- **Embedding 懒加载**：BGE 模型 2GB，首次使用时加载，后续复用全局实例
- **ChromaDB 持久化**：向量数据存磁盘，服务重启不丢失
- **BM25 自实现**：80 行代码实现完整 BM25 算法，jieba 中文分词
- **双重错误处理**：异常时 rollback + 重查，状态不卡在中间态
- **图形验证码**：pillow 自生成，5 分钟过期，一次性校验，防暴力破解

---

## 项目结构

```
backend/
├── .env.example              # 环境变量模板
├── requirements.txt          # Python 依赖
├── seed.py                   # 数据库初始化
├── uploads/                  # PDF 文件存储
├── chroma_data/              # ChromaDB 向量数据
└── app/
    ├── main.py               # FastAPI 入口
    ├── core/                  # config, database, security
    ├── models/                # 7 个 ORM 模型文件
    ├── schemas/               # Pydantic 校验
    ├── middleware/auth.py     # JWT + RBAC
    ├── utils/captcha.py       # 图形验证码
    ├── routers/               # 8 个路由模块
    └── services/              # 9 个服务模块

frontend/
└── src/
    ├── router/               # 20+ 路由 + 登录守卫
    ├── stores/user.ts        # Pinia 状态
    ├── utils/request.ts      # Axios 封装
    ├── api/                  # 6 个 API 模块
    ├── components/layout/    # 主布局
    └── views/                # 15 个页面视图
```

---

## 涉及算法

| # | 算法 | 应用位置 |
|---|------|---------|
| 1 | BM25 | 关键词检索排序 |
| 2 | 加权融合排序 | 混合检索结果合并 |
| 3 | 余弦相似度 | ChromaDB 向量检索 |
| 4 | HNSW | ChromaDB 近似最近邻搜索 |
| 5 | jieba 中文分词 | BM25 索引构建 |
| 6 | RAG 检索增强生成 | 问答核心流程 |
| 7 | 查询改写（Query Expansion） | 规则词典 + LLM 改写 |
| 8 | Agent 多步推理 | 问题拆解→并行检索→综合 |
| 9 | Bcrypt 密码哈希 | 用户密码存储 |
| 10 | JWT HS256 | 身份认证 |
| 11 | SHA256 | 文件去重 |
| 12 | 正则表达式匹配 | 财务指标提取、章节切分 |
| 13 | 雷达图归一化 | 六维财务健康度评估 |

---

## 许可证

本项目为本科毕业设计作品，仅供学习参考。
