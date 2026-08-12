from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "demotrial.html"

app = FastAPI(title="Taoran AI Demo API", version="0.1.0")


class ChatMessage(BaseModel):
    sender: Literal["user", "ai"]
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)
    latest_image: "ImagePayload | None" = None


class ImagePayload(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=1, max_length=100)
    data_url: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str


def build_demo_reply(message: str, history: list[ChatMessage], latest_image: ImagePayload | None = None) -> str:
    text = message.strip()
    lowered = text.lower()
    history_size = len(history)

    if not text:
        raise HTTPException(status_code=400, detail="message 不能为空")

    if latest_image is not None:
        suffix = "你可以继续补一句你最想让我看哪一部分，比如题干、选项、还是整段文章。"
        if any(keyword in text for keyword in ["阅读", "图片", "截图", "题目", "分析"]):
            return f"我已经收到你上传的图片 `{latest_image.file_name}` 了。当前后端还没接真正的 OCR/视觉模型，不过链路已经打通。{suffix}"
        return f"图片我已经收到了，文件名是 `{latest_image.file_name}`。当前演示版会先把图片作为附件收下，下一步就可以接 OCR 或多模态模型做识别。{suffix}"

    if any(keyword in text for keyword in ["阅读", "细节题", "主旨", "七选五"]):
        return (
            "这道题我们可以按“题干定位 -> 原文同义替换 -> 排除干扰项”来拆。"
            f"你刚才这轮问题里最值得先抓的是关键词定位。先把题干里的核心词圈出来，"
            "再回原文找对应句，我也可以继续陪你逐句分析。"
        )

    if any(keyword in text for keyword in ["语法", "非谓语", "时态", "从句"]):
        return (
            "这类语法题先不要急着选答案，先判断句子主干，再看空格在句中充当什么成分。"
            "如果你愿意，我们下一步可以把这句拆成“主谓宾 / 从句 / 非谓语”三个层次来讲。"
        )

    if any(keyword in text for keyword in ["作文", "写作", "续写", "表达"]):
        return (
            "写作题最稳的做法是先保结构，再升级表达。"
            "你这句可以先确保意思清楚，然后把普通表达替换成更自然的高分句式，我可以直接帮你润色成高考风格。"
        )

    if "hello" in lowered or "hi" in lowered or "你好" in text:
        return "你好呀，我已经通过 FastAPI 接口接上前端了。你现在发来的内容，已经是在走真实请求链路。"

    return (
        f"我收到你的问题了：{text}。"
        f" 这是第 {max(history_size // 2, 0) + 1} 轮练习，我们可以先从关键信息定位入手，"
        "再把答案依据和易错点讲清楚。你也可以继续补充题干或截图内容。"
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    reply = build_demo_reply(request.message, request.history, request.latest_image)
    return ChatResponse(reply=reply)


@app.get("/")
@app.get("/demotrial.html")
async def index() -> FileResponse:
    if not HTML_FILE.exists():
        raise HTTPException(status_code=404, detail="demotrial.html 不存在")
    return FileResponse(HTML_FILE)
