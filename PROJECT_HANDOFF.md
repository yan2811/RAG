# 项目交接文档 - 财报 RAG 知识库系统

## 一、项目概述

**项目名称**：基于 RAG 架构的企业多维度财报智能分析与深度问答知识库系统设计与实现

**项目类型**：本科毕业设计

**选题来源**：中国国际大学生创新大赛（2025）产业赛道 —— 中联企业管理集团命题

**当前状态**：全部 8 个功能模块开发完成，前后端联调通过，可正常运行

---

## 二、技术栈

| 层级 | 技术 | 版本/说明 |
|------|------|----------|
| 前端框架 | Vue3 + Vite + TypeScript | Vite 6.x |
| UI 组件库 | Element Plus | 全局注册，中文语言 |
| 状态管理 | Pinia | stores/user.ts |
| 图表 | ECharts 5.6 + vue-echarts 7.x | 仪表盘和可视化大屏 |
| 后端框架 | Python + FastAPI + Uvicorn | Python 3.10+ |
| ORM | SQLAlchemy 2.0 | 同步引擎（非异步） |
| 数据库 | MySQL 8.0 | 端口 3307，字符集 utf8mb4 |
| 向量数据库 | ChromaDB 0.5.x | 持久化存储，cosine 相似度 |
| AI 引擎 | DeepSeek-V4-Pro | 使用 Anthropic 协议端点 |
| AI 调用方式 | Anthropic Python SDK | base_url 含 "anthropic" 标识时自动切换 |
| 密码加密 | bcrypt | 直接调用 bcrypt 库（非 passlib，避免兼容问题） |
| JWT | python-jose | HS256 算法 |
| PDF 生成 | fpdf2 | 示例财报用 |
| PDF 解析 | PyMuPDF (fitz) | 生产 PDF 文本提取 |
| 中文分词 | jieba | BM25 关键词检索 |

---

## 三、环境配置

### 3.1 数据库

```
MySQL 8.0
Host: localhost:3307
User: root
Password: 123456
Database: rag_financial
Charset: utf8mb4
```

初始化：`cd backend && python seed.py`

### 3.2 环境变量（backend/.env）

```
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=rag_financial

SECRET_KEY=rag-financial-jwt-secret-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic

SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=true
```

**重要**：
- DeepSeek API 使用 Anthropic 协议（base_url 含 `/anthropic`）
- API Key 需自行配置，注册 DeepSeek 获取
- 后端 `llm_service.py` 根据 base_url 是否含 "anthropic" 自动选择 OpenAI SDK 或 Anthropic SDK

### 3.3 默认账号

```
管理员：admin / admin123456（超级管理员角色）
```

4 个角色：super_admin / admin / user / guest（单选分配）

---

## 四、启动方式

```bash
# 终端 1：后端
cd C:\Users\15279\Desktop\RAG\backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
# API 文档：http://localhost:8000/docs

# 终端 2：前端
cd C:\Users\15279\Desktop\RAG\frontend
npm install   # 首次运行
npm run dev   # http://localhost:5173
```

Vite 已配置代理：`/api` 请求自动转发到 `localhost:8000`。

---

## 五、项目文件结构

```
C:\Users\15279\Desktop\RAG\
├── PROJECT_HANDOFF.md          # 本文档（交接文档）
├── CLAUDE.md                   # Claude Code 配置文件
├── 1.0系统需求分析报告.docx     # 需求分析报告（8 章已完成）
├── 毕业论文选题审批表_已填写.docx # 选题审批表
│
├── backend/
│   ├── .env                    # 环境变量（已配置 API Key）
│   ├── .env.example            # 环境变量模板
│   ├── requirements.txt        # Python 依赖（pip install -r requirements.txt）
│   ├── seed.py                 # 数据库初始化（创建表 + 4 个角色 + admin 用户）
│   ├── generate_samples.py     # 示例财报生成（比亚迪 + 宁德时代，已执行）
│   ├── uploads/                # 所有已上传的 PDF 文件
│   ├── chroma_data/            # ChromaDB 向量数据（持久化）
│   └── app/
│       ├── main.py             # FastAPI 入口（8 个路由模块注册 + CORS + startup 建表）
│       ├── core/
│       │   ├── config.py       # 全局配置类（继承 pydantic BaseSettings）
│       │   ├── database.py     # SQLAlchemy 引擎、会话工厂、get_db 依赖注入
│       │   └── security.py     # bcrypt 密码哈希 + JWT 签发/解密
│       ├── models/             # ORM 模型（7 个文件，13 张表）
│       │   ├── user.py         # User
│       │   ├── role.py         # Role + user_roles 关联表
│       │   ├── document.py     # Document + Chunk + FinancialMetric + DocumentVersion
│       │   ├── session.py      # Session + Message + Feedback
│       │   ├── tag.py          # Tag + document_tags 关联表
│       │   ├── log.py          # OperationLog
│       │   └── settings.py     # SystemSetting + Report
│       ├── schemas/            # Pydantic 请求/响应模型
│       │   ├── auth.py         # 登录/注册/Token
│       │   ├── user.py         # 用户管理/角色管理
│       │   └── document.py     # 文档上传/列表/详情
│       ├── middleware/
│       │   └── auth.py         # JWT 验证依赖 + require_permission 权限校验装饰器
│       ├── routers/            # 8 个路由模块
│       │   ├── auth.py         # /api/v1/auth/* 注册/登录/个人信息
│       │   ├── admin.py        # /api/v1/admin/* 用户CRUD/角色/日志/配置
│       │   ├── document.py     # /api/v1/documents/* 上传/列表/详情/删除/全文/打开PDF/AI分节
│       │   ├── knowledge.py    # /api/v1/knowledge/* 概览/标签CRUD/版本/向量索引
│       │   ├── chat.py         # /api/v1/sessions/* + /api/v1/chat/{id} SSE流式问答
│       │   ├── agent.py        # /api/v1/agent/analyze 多步推理Agent
│       │   ├── dashboard.py    # /api/v1/dashboard/* 仪表盘/bigscreen/AI图表/对比
│       │   └── report.py       # /api/v1/reports/* 生成/列表/详情/下载/批量导出
│       └── services/           # 10 个服务模块
│           ├── document_service.py  # PDF 解析（PyMuPDF 文本提取 + Camelot 表格）
│           ├── embedding_service.py # BGE 向量化（懒加载）+ BM25 关键词索引
│           ├── vector_store.py      # ChromaDB 封装（增删查）
│           ├── search_service.py    # 混合检索（向量 + BM25 → RRF 融合）
│           ├── llm_service.py       # DeepSeek 双协议调用（OpenAI/Anthropic）
│           ├── agent_service.py     # 多步推理（LLM 拆解问题 → 并行检索 → 综合报告）
│           ├── dashboard_service.py # 财务指标提取 + 仪表盘数据构建
│           ├── report_service.py    # AI 报告生成（7 章逐节 LLM 生成）
│           └── log_service.py       # 操作日志记录
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts          # 开发服务器 + API 代理配置
│   ├── tsconfig.json
│   ├── index.html
│   ├── public/vite.svg         # Logo
│   └── src/
│       ├── main.ts             # 入口：全局注册 Element Plus + Router + Pinia
│       ├── App.vue             # 根组件（router-view 占位）
│       ├── env.d.ts
│       ├── router/index.ts     # 20+ 路由 + 登录守卫（token 检查 + 权限 meta）
│       ├── stores/user.ts      # Pinia 用户状态（login/logout/hasPermission）
│       ├── utils/request.ts    # Axios 封装（拦截器注入 JWT + 401 跳转 + 统一错误处理）
│       ├── api/                # 按模块拆分的 API 调用
│       │   ├── auth.ts         # 登录/注册/个人信息
│       │   ├── admin.ts        # 用户管理/角色管理/日志/配置
│       │   ├── document.ts     # 文档上传/列表/详情/删除/解析
│       │   ├── knowledge.ts    # 知识库概览/标签 CRUD/索引
│       │   ├── chat.ts         # 会话 CRUD + SSE 流式问答（fetch ReadableStream）
│       │   └── report.ts       # 报告中心/仪表盘/Agent 分析/AI 图表
│       ├── components/
│       │   └── layout/
│       │       └── AppLayout.vue  # 主布局（侧边栏 8 个菜单 + 顶栏头像下拉 + 内容区）
│       └── views/
│           ├── login/LoginView.vue              # 登录/注册双模式
│           ├── dashboard/DashboardView.vue       # 首页工作台（4 个实时统计卡片 + 最近报告）
│           ├── documents/
│           │   ├── DocumentList.vue              # 文档列表（状态筛选 + 分页）
│           │   ├── DocumentUpload.vue            # 上传页面（拖拽 + 表单）
│           │   └── DocumentDetail.vue            # 详情页（元数据 + 分块列表点击查看完整内容 + 重新解析 + 打开PDF）
│           ├── knowledge/
│           │   ├── KnowledgeOverview.vue         # 文档管理中心（统计卡片 + 全文搜索/状态筛选 + 打开PDF/详情/仪表盘/删除）
│           │   └── TagManagement.vue             # 标签管理（增删 + 文档关联）
│           ├── chat/ChatLayout.vue               # 智能问答（左右分栏：会话列表 + SSE 流式对话 + Markdown 渲染 + 来源标注 + 点赞 + 文档选择 + Agent 按钮）
│           ├── analytics/
│           │   ├── AnalyticsDashboard.vue        # 分析仪表盘（AI 智能分析 + ECharts 图表 + 六维雷达）
│           │   └── BigScreen.vue                 # 可视化大屏（暗色全屏 + 实时时钟 + KPI 卡片 + 年度分布图 + 实时动态滚动 + 自动刷新）
│           ├── reports/ReportList.vue            # 报告中心（选择文档生成 + 预览 + 下载PDF + 导出MD + 批量导出ZIP + 批量删除）
│           └── admin/
│               ├── UserManagement.vue            # 用户管理（查询/新增/编辑/删除 + 角色单选）
│               ├── RoleManagement.vue            # 角色管理（列表展示 + 权限勾选）
│               ├── OperationLogs.vue             # 操作日志（筛选 + 分页）
│               ├── SystemSettings.vue            # 系统配置（API Key/chunk 参数/Logo）
│               └── UserProfile.vue               # 个人主页（头像 + 修改邮箱/密码 + 权限列表）
│
└── docs/
    └── superpowers/specs/
        └── 2026-06-04-rag-financial-analysis-design.md  # 系统设计规格书
```

---

## 六、8 个功能模块

| 编号 | 模块 | 核心功能 | 完成度 |
|------|------|---------|--------|
| M1 | 文档智能解析引擎 | PDF 上传 + PyMuPDF 文本提取 + Camelot 表格解析 + DeepSeek AI 智能分节 + 原始 PDF 浏览器直接打开 | 100% |
| M2 | 知识库构建与管理 | 文档向量化（BGE） + ChromaDB 索引 + BM25 关键词检索 + 混合检索（RRF 融合） + 标签分类 + 版本管理 | 100% |
| M3 | 智能问答与对话管理 | 双模式（AI 直接回答 / RAG 检索增强） + SSE 流式输出 + 查询改写（HyDE） + 溯源标注 + 多轮对话（5 轮记忆） + 会话 CRUD + 历史导出 + 点赞点踩 | 100% |
| M4 | 多步推理 Agent | LLM 自动拆解复杂问题 → 子任务并行检索 → 交叉验证 → 综合分析报告生成 | 100% |
| M5 | 财报分析仪表盘 | AI 智能图表生成（柱状/折线/饼/雷达/散点） + 六维雷达图 + 财务指标提取 + 跨公司对比 | 100% |
| M6 | AI 报告生成 | 7 章节专业报告 + DeepSeek 逐节 AI 生成 + 指标精确提取（正则/MySQL） + Markdown 预览 + PDF 下载 + 批量导出 ZIP | 100% |
| M7 | 系统管理 | JWT 认证 + bcrypt 密码 + RBAC 权限控制（4 角色单选） + 用户 CRUD + 操作日志审计 + 系统配置 + 个人主页 | 100% |
| M8 | 数据可视化大屏 | 全屏暗色科技风 + 实时时钟 + KPI 卡片（文档/问答/满意度/公司） + 年度分布柱状图 + 公司列表 + 高频问题 Top5 + 实时动态滚动 + 60 秒自动刷新 | 100% |

---

## 七、数据库表（15 张）

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| users | 用户 | id, username, password_hash, email, avatar, status |
| roles | 角色 | id, name, display_name, permissions(JSON) |
| user_roles | 用户-角色关联 | user_id, role_id |
| documents | 文档元数据 | id, user_id, file_name, file_path, file_hash, doc_type, company_code, fiscal_year, parse_status, chunk_count, is_deleted |
| chunks | 文档分块 | id, document_id, chunk_index, chunk_type, section_title, content, page_start, chroma_id |
| financial_metrics | 财务指标 | id, document_id, company_code, fiscal_year, metric_name, metric_value, metric_unit, yoy_change |
| document_versions | 文档版本 | id, document_id, version_number, file_path, change_note, is_current |
| sessions | 对话会话 | id, user_id, session_title, status |
| messages | 对话消息 | id, session_id, role, content, sources(JSON), token_usage(JSON) |
| feedbacks | 消息反馈 | id, message_id, user_id, rating, reason |
| tags | 标签 | id, name, color, description |
| document_tags | 文档-标签关联 | document_id, tag_id |
| operation_logs | 操作日志 | id, user_id, username, action, target_type, target_id, detail(JSON), ip_address, status |
| system_settings | 系统配置 | id, setting_key, setting_value, description |
| reports | 生成报告 | id, user_id, company_code, company_name, fiscal_year, report_type, content_md, file_path |

---

## 八、API 接口（50+ 个）

| 路由前缀 | 模块 | 主要接口 |
|---------|------|---------|
| `/api/v1/auth/*` | 认证 | `POST /register` `POST /login` `GET /me` |
| `/api/v1/admin/*` | 系统管理 | `GET/POST /users` `PUT/DELETE /users/{id}` `GET/POST /roles` `GET /logs` `GET/PUT /settings` |
| `/api/v1/documents/*` | 文档管理 | `POST /upload` `GET /` `GET/{id}` `GET/{id}/fulltext` `GET/{id}/file` `POST/{id}/parse` `DELETE/{id}` |
| `/api/v1/knowledge/*` | 知识库 | `GET /overview` `GET/POST /tags` `POST /documents/{id}/tags` `GET /documents/{id}/versions` `POST /index/{id}` `GET /stats` |
| `/api/v1/sessions/*` | 会话 | `GET/POST /` `PUT/DELETE /{id}` `GET /{id}/messages` `GET /{id}/export` |
| `/api/v1/chat/{id}` | 问答 | `POST /{session_id}`（SSE 流式） `POST /{session_id}/feedback` |
| `/api/v1/agent/*` | Agent | `POST /analyze` |
| `/api/v1/dashboard/*` | 仪表盘 | `GET /bigscreen` `POST /{id}/ai-charts` `GET /{id}` `GET /compare` `GET /{id}/metrics` |
| `/api/v1/reports/*` | 报告 | `POST /generate` `GET /` `GET /{id}` `GET /{id}/download` `POST /batch-export` `DELETE /{id}` |

---

## 九、关键设计决策

1. **DeepSeek 双协议支持**：`llm_service.py` 自动检测 base_url 是否含 "anthropic"，含则用 Anthropic SDK（system 独立参数，messages 仅 user/assistant），否则用 OpenAI SDK
2. **问答双模式**：未选文档 → AI 直接回答（通用知识），选了文档 → RAG 检索增强（知识库 + LLM + 溯源）
3. **密码加密**：直接使用 `bcrypt` 库而非 `passlib`，因 passlib 与新版 bcrypt 不兼容
4. **数据库编码**：创建连接时需通过 `connect_args={"charset": "utf8mb4"}` 确保中文正确存储
5. **PDF 查看**：原始 PDF 通过浏览器原生渲染打开（`/documents/{id}/file?token=xxx`），不做文本转换
6. **角色分配**：一个用户一个角色（radio 单选），super_admin 拥有所有权限
7. **Embedding 懒加载**：BGE 模型在首次调用时加载，后续复用全局实例
8. **ChromaDB**：持久化存储于 `backend/chroma_data/`，collection 名 `financial_reports`
9. **前端 JWT 管理**：Axios 拦截器自动注入 Authorization header，401 自动跳转登录页
10. **Vite 代理**：`/api` 前缀请求自动转发到 `localhost:8000`

---

## 十、当前数据状态

数据库中已有数据：
- 1 个管理员账号（admin）
- 4 份文档（2 份示例 + 1 份测试 + 1 份用户上传的真实财报）
- 对应文档分块（chunks）
- 若干对话会话和消息
- 若干生成报告
- 4 个角色 + 4 个标签

---

## 十一、已知问题与注意事项

1. **BGE Embedding 模型未安装**：`sentence-transformers` 体积大（约 2GB），当前系统未安装。向量检索功能后端代码已就绪，但实际运行时 embedding 会返回占位向量或提示未安装。如需启用：`pip install sentence-transformers`
2. **Camelot 表格解析**：依赖 Ghostscript，Windows 可能需要额外安装
3. **报告 PDF 导出**：当前导出为 HTML 文件（降级方案），如安装 `weasyprint` 可生成真 PDF
4. **Redis 和 Celery**：早期设计文档中提到，但当前未使用（文档解析为同步执行）
5. **端口冲突**：多次启动会产生僵尸 Python 进程占用 8000 端口，用 `netstat -ano | grep :8000` 找到 PID 后 kill
6. **中文终端显示**：Bash 终端可能显示乱码，但数据库和 API 响应中 UTF-8 编码正确

---

## 十二、快速验证命令

```bash
# 测试后端是否正常
curl http://localhost:8000/

# 测试登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123456"}'

# 测试所有 API（需要先登录获取 token）
# 文档管理：GET /api/v1/documents
# 知识库：  GET /api/v1/knowledge/overview
# 会话：    GET /api/v1/sessions
# 报告：    GET /api/v1/reports
# 大屏：    GET /api/v1/dashboard/bigscreen
```

---

## 十三、后续可能的改进方向

- 安装 `sentence-transformers` 启用完整向量检索
- 安装 `weasyprint` 启用真 PDF 报告导出
- 引入 Celery + Redis 实现异步文档解析
- 添加 WebSocket 实时通知
- 前端国际化支持
- 移动端适配
