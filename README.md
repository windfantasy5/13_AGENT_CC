# 智能问答系统

基于 RAG（检索增强生成）和 AI Agent 的企业级知识库问答系统。

## 主要功能

- **用户认证** - 安全的登录和注册系统
- **知识库管理** - 文档上传、分段预览、参数调整
- **智能问答** - 基于知识库的上下文感知对话
- **文档分段预览** - 实时预览文档分段效果并调整参数
- **向量检索** - 使用 ChromaDB 进行高效的语义搜索
- **现代化界面** - 美观、响应式的用户界面

## 技术栈

### 后端
- FastAPI - Web 框架
- MySQL + Redis - 数据存储
- ChromaDB - 向量数据库
- LangChain - LLM 框架
- PaddleOCR - 文档 OCR 识别
- Python 3.12

### 前端
- React 19 + TypeScript
- Vite 8 - 构建工具
- Tailwind CSS 4 - 样式框架
- Axios - HTTP 客户端
- React Router - 路由管理

## 快速开始

### 1. 系统测试

运行系统完整性测试：
```bash
test_system.bat
```

### 2. 启动服务

#### 方式一：使用启动脚本

后端：
```bash
start_backend.bat
```

前端：
```bash
start_frontend.bat
```

#### 方式二：手动启动

后端：
```bash
cd backend
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

前端：
```bash
cd frontend
npm run dev
```

### 3. 访问系统

- 前端界面: http://localhost:5173
- 后端 API: http://127.0.0.1:8000
- API 文档: http://127.0.0.1:8000/docs

## 使用说明

### 首次使用

1. 访问 http://localhost:5173
2. 点击"立即注册"创建账户
3. 输入用户名、邮箱和密码完成注册

### 知识库管理

1. 登录后点击顶部"知识库管理"
2. 选择文档文件（支持 PDF、TXT、DOC、DOCX）
3. 调整分段参数：
   - **最大分段大小**：200-2000 字符
   - **最小分段大小**：10-200 字符
   - **重叠大小**：0-200 字符
4. 点击"预览分段"查看分段效果
5. 确认后点击"确认上传"保存到向量数据库

### 智能问答

1. 点击顶部"智能问答"
2. 点击"+ 新建对话"创建新对话
3. 在输入框输入问题
4. 系统基于知识库内容智能回答
5. 支持多轮对话和历史记录

## 配置说明

编辑 `backend/.env` 配置文件：

```env
# 数据库配置
DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/ai_agent
REDIS_URL=redis://localhost:6379/0

# LLM 配置
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

# 文件上传
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=52428800
```

## 项目结构

```
.
├── backend/              # 后端代码
│   ├── app/
│   │   ├── api/         # API 路由
│   │   ├── core/        # 核心功能（文本分段、向量存储等）
│   │   ├── models/      # 数据模型
│   │   ├── services/    # 业务逻辑
│   │   └── main.py      # 入口文件
│   ├── requirements.txt
│   └── .env
├── frontend/            # 前端代码
│   ├── src/
│   │   ├── pages/       # 页面组件（登录、问答、知识库）
│   │   ├── services/    # API 服务
│   │   └── types/       # TypeScript 类型定义
│   └── package.json
├── start_backend.bat    # 后端启动脚本
├── start_frontend.bat   # 前端启动脚本
└── test_system.bat      # 系统测试脚本
```

## 开发说明

详细的开发进度和实现说明请查看 `开发进度.md`。

## 更新日志

### v1.0.0 (2026-04-15)

- ✅ 用户认证系统
- ✅ 智能问答功能
- ✅ 知识库管理
- ✅ 文档分段预览
- ✅ 自定义分段参数
- ✅ 向量化存储
- ✅ 全中文界面
- ✅ Tailwind CSS 4 支持

## 许可证

MIT License
