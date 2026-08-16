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
