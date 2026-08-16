# 陶然 AI 助教 Demo

这是一个最小可运行版本：

- 前端：`demotrial.html`
- 后端：`FastAPI`
- 接口：`POST /api/chat`
- 模型接入框架：`Qwen 文本 / 视觉 / OCR`

## 启动方式

1. 创建虚拟环境

```powershell
python -m venv .venv
```

2. 安装依赖

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

3. 配置环境变量

先复制一份环境变量模板：

```powershell
Copy-Item .env.example .env
```

当前已预留这些模型：

- 视觉模型：`qwen3-vl-flash`
- 纯 OCR 模型：`qwen-vl-ocr-latest`
- 文本模型：`qwen-flash`
- 文本增强模型：`qwen-plus`

主要环境变量：

- `QWEN_API_KEY`
- `QWEN_BASE_URL`
- `QWEN_TEXT_MODEL`
- `QWEN_BACKUP_TEXT_MODEL`
- `QWEN_VISION_MODEL`
- `QWEN_OCR_MODEL`

4. 启动服务

```powershell
.\.venv\Scripts\python -m uvicorn app:app --reload
```

5. 打开页面

访问 `http://127.0.0.1:8000`

## 接口说明

### `POST /api/chat`

请求体示例：

```json
{
  "session_id": "demo-session-id",
  "message": "帮我分析这道阅读理解",
  "history": [
    { "sender": "user", "content": "你好" },
    { "sender": "ai", "content": "你好呀" }
  ],
  "preferred_text_model": "qwen-flash",
  "preferred_vision_model": "qwen3-vl-flash",
  "preferred_ocr_model": "qwen-vl-ocr-latest",
  "use_ocr_first": true
}
```

响应体示例：

```json
{
  "reply": "这道题我们可以按题干定位来拆解。",
  "meta": {
    "route": "text",
    "provider": "dashscope-compatible",
    "text_model": "qwen-flash",
    "vision_model": null,
    "ocr_model": null,
    "used_demo_fallback": false
  }
}
```

## 当前模型路由

- 纯文本问题：走 `qwen-flash`
- 图片问题：默认先走 `qwen-vl-ocr-latest`，再把 OCR 结果和图片一起交给 `qwen3-vl-flash`
- 如果没配置 API Key，或者模型调用失败：自动回退到当前 demo 回复逻辑

## 额外接口

- `GET /health`：查看服务状态和当前模型配置
- `GET /api/model-config`：查看当前后端模型框架配置

## Vercel 临时部署

这个项目现在可以直接部署到 Vercel，适合先做在线 demo。

### 1. 导入仓库

把 GitHub 仓库导入 Vercel，新建 Project 即可。

仓库里已经补了：

- `vercel.json`
- `pyproject.toml`

Vercel 会直接识别根目录的 `app.py` 作为 FastAPI 入口。

### 2. 配置环境变量

在 Vercel Project Settings -> Environment Variables 中填写：

- `QWEN_API_KEY`
- `QWEN_BASE_URL`
- `QWEN_TEXT_MODEL`
- `QWEN_BACKUP_TEXT_MODEL`
- `QWEN_VISION_MODEL`
- `QWEN_OCR_MODEL`

建议值与本地 `.env` 保持一致。

### 3. 部署后验证

部署成功后先访问：

- `/health`
- `/api/model-config`

如果这两个地址正常，再打开首页测试聊天。

### 4. 当前已知限制

- Vercel 适合先顶 demo，但本质上仍是函数式部署
- 图片目前通过 `data_url` 走 JSON 请求体上传
- 为了更稳地适配 Vercel，前端已把单张图片限制收紧到 `3MB`

如果后面要长期稳定跑图片识别，建议明天迁到正式后端服务器后，再改成更适合生产的图片上传链路。
