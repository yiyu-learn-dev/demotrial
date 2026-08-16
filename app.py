from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from openai import OpenAI
from pydantic import BaseModel, Field


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "demotrial.html"
logger = logging.getLogger("taoran.demo")

app = FastAPI(title="Taoran AI Demo API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    sender: Literal["user", "ai"]
    content: str = Field(..., min_length=1, max_length=4000)


class ImagePayload(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=1, max_length=100)
    data_url: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)
    latest_image: ImagePayload | None = None
    preferred_text_model: str | None = None
    preferred_vision_model: str | None = None
    preferred_ocr_model: str | None = None
    use_ocr_first: bool = True


class ModelMeta(BaseModel):
    route: Literal["demo", "text", "vision", "ocr_plus_vision"]
    provider: str
    text_model: str | None = None
    vision_model: str | None = None
    ocr_model: str | None = None
    used_demo_fallback: bool = False


class ChatResponse(BaseModel):
    reply: str
    meta: ModelMeta


class ModelSettings(BaseModel):
    provider_name: str = "dashscope-compatible"
    api_key: str | None = None
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    text_model: str = "qwen-flash"
    backup_text_model: str = "qwen-plus"
    vision_model: str = "qwen3-vl-flash"
    ocr_model: str = "qwen-vl-ocr-latest"

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)


@lru_cache(maxsize=1)
def get_model_settings() -> ModelSettings:
    return ModelSettings(
        api_key=os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        text_model=os.getenv("QWEN_TEXT_MODEL", "qwen-flash"),
        backup_text_model=os.getenv("QWEN_BACKUP_TEXT_MODEL", "qwen-plus"),
        vision_model=os.getenv("QWEN_VISION_MODEL", "qwen3-vl-flash"),
        ocr_model=os.getenv("QWEN_OCR_MODEL", "qwen-vl-ocr-latest"),
    )


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI | None:
    settings = get_model_settings()
    if not settings.enabled:
        return None
    return OpenAI(api_key=settings.api_key, base_url=settings.base_url)


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


def build_text_messages(message: str, history: list[ChatMessage]) -> list[dict]:
    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "你是陶然 AI 助教，专注高考英语辅导。回答要清晰、温和、结构化，"
                "优先帮助用户定位题干信息、分析答案依据，并给出下一步学习建议。"
            ),
        }
    ]
    for item in history[-10:]:
        role = "assistant" if item.sender == "ai" else "user"
        messages.append({"role": role, "content": item.content})
    messages.append({"role": "user", "content": message})
    return messages


def build_vision_messages(
    message: str,
    history: list[ChatMessage],
    image: ImagePayload,
    ocr_text: str | None = None,
) -> list[dict]:
    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "你是陶然 AI 助教，当前正在处理用户上传的题目图片。"
                "请结合图片内容、用户问题和已有上下文，输出适合学生阅读的分析。"
            ),
        }
    ]
    for item in history[-6:]:
        role = "assistant" if item.sender == "ai" else "user"
        messages.append({"role": role, "content": item.content})

    user_content: list[dict] = [{"type": "text", "text": message}]
    if ocr_text:
        user_content.append(
            {
                "type": "text",
                "text": f"下面是 OCR 识别出的参考文本，你可以结合图片一起判断：\n{ocr_text}",
            }
        )
    user_content.append({"type": "image_url", "image_url": {"url": image.data_url}})
    messages.append({"role": "user", "content": user_content})
    return messages


def extract_ocr_text(client: OpenAI, image: ImagePayload, model: str) -> str:
    completion = client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": "你是 OCR 识别助手。请只提取图片中的文字内容，保留换行，避免解释。",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请提取这张图片中的全部可识别文字。"},
                    {"type": "image_url", "image_url": {"url": image.data_url}},
                ],
            },
        ],
    )
    return completion.choices[0].message.content or ""


def generate_text_reply(client: OpenAI, message: str, history: list[ChatMessage], model: str) -> str:
    completion = client.chat.completions.create(
        model=model,
        temperature=0.4,
        messages=build_text_messages(message, history),
    )
    return completion.choices[0].message.content or ""


def generate_vision_reply(
    client: OpenAI,
    message: str,
    history: list[ChatMessage],
    image: ImagePayload,
    model: str,
    ocr_text: str | None = None,
) -> str:
    completion = client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=build_vision_messages(message, history, image, ocr_text=ocr_text),
    )
    return completion.choices[0].message.content or ""


def run_model_pipeline(request: ChatRequest) -> ChatResponse:
    settings = get_model_settings()
    client = get_openai_client()
    text_model = request.preferred_text_model or settings.text_model
    vision_model = request.preferred_vision_model or settings.vision_model
    ocr_model = request.preferred_ocr_model or settings.ocr_model

    if client is None:
        route = "ocr_plus_vision" if request.latest_image and request.use_ocr_first else "vision" if request.latest_image else "demo"
        return ChatResponse(
            reply=build_demo_reply(request.message, request.history, request.latest_image),
            meta=ModelMeta(
                route=route if route != "demo" else "demo",
                provider=settings.provider_name,
                text_model=text_model,
                vision_model=vision_model,
                ocr_model=ocr_model,
                used_demo_fallback=True,
            ),
        )

    try:
        if request.latest_image is not None:
            ocr_text = None
            route: Literal["vision", "ocr_plus_vision"] = "vision"
            if request.use_ocr_first:
                route = "ocr_plus_vision"
                ocr_text = extract_ocr_text(client, request.latest_image, ocr_model)
            reply = generate_vision_reply(
                client,
                request.message,
                request.history,
                request.latest_image,
                vision_model,
                ocr_text=ocr_text,
            )
            return ChatResponse(
                reply=reply,
                meta=ModelMeta(
                    route=route,
                    provider=settings.provider_name,
                    vision_model=vision_model,
                    ocr_model=ocr_model if route == "ocr_plus_vision" else None,
                ),
            )

        reply = generate_text_reply(client, request.message, request.history, text_model)
        return ChatResponse(
            reply=reply,
            meta=ModelMeta(
                route="text",
                provider=settings.provider_name,
                text_model=text_model,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Model pipeline failed, fallback to demo reply")
        return ChatResponse(
            reply=build_demo_reply(request.message, request.history, request.latest_image),
            meta=ModelMeta(
                route="demo",
                provider=settings.provider_name,
                text_model=text_model,
                vision_model=vision_model,
                ocr_model=ocr_model,
                used_demo_fallback=True,
            ),
        )


@app.get("/health")
async def health() -> dict[str, object]:
    settings = get_model_settings()
    return {
        "status": "ok",
        "models_enabled": settings.enabled,
        "provider": settings.provider_name,
        "text_model": settings.text_model,
        "backup_text_model": settings.backup_text_model,
        "vision_model": settings.vision_model,
        "ocr_model": settings.ocr_model,
    }


@app.get("/api/model-config")
async def model_config() -> dict[str, object]:
    settings = get_model_settings()
    return {
        "provider": settings.provider_name,
        "models_enabled": settings.enabled,
        "text_model": settings.text_model,
        "backup_text_model": settings.backup_text_model,
        "vision_model": settings.vision_model,
        "ocr_model": settings.ocr_model,
        "base_url": settings.base_url,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message 不能为空")
    return run_model_pipeline(request)


@app.get("/")
@app.get("/demotrial.html")
async def index() -> FileResponse:
    if not HTML_FILE.exists():
        raise HTTPException(status_code=404, detail="demotrial.html 不存在")
    return FileResponse(HTML_FILE)
