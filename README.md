# 陶然 AI 助教 Demo

这是一个最小可运行版本：

- 前端：`demotrial.html`
- 后端：`FastAPI`
- 接口：`POST /api/chat`

## 启动方式

1. 创建虚拟环境

```powershell
python -m venv .venv
```

2. 安装依赖

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

3. 启动服务

```powershell
.\.venv\Scripts\python -m uvicorn app:app --reload
```

4. 打开页面

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
  ]
}
```

响应体示例：

```json
{
  "reply": "这道题我们可以按题干定位来拆解。"
}
```

目前后端回复是演示用规则逻辑，后续可以直接替换成真实模型调用。
