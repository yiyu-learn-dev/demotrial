from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from openai import OpenAI
from pydantic import BaseModel, Field


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "demotrial.html"
NOTES_DATA_FILE = BASE_DIR / "notes-data.js"
PROMPT_FILE = BASE_DIR / "prompt_1.md"
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
    content: str = Field(..., min_length=1, max_length=12000)


class ImagePayload(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=1, max_length=100)
    data_url: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=12000)
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


def get_teaching_prompt() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8").strip()
    logger.warning("Teaching prompt file not found: %s", PROMPT_FILE)
    return (
        "你是陶然，高考英语老师。讲题、答疑、陪学生练英语。听懂用户在说什么，再自然作答。"
        "阅读、完形、语法、七选五都直接讲。有材料就给答案和依据；材料不够就说明还缺什么。不要说“不支持这种题”。"
    )


def build_demo_reply(message: str, history: list[ChatMessage], latest_image: ImagePayload | None = None) -> str:
    text = message.strip()
    history_size = len(history)

    if not text:
        raise HTTPException(status_code=400, detail="message 不能为空")

    if latest_image is not None:
        return (
            f"图片 `{latest_image.file_name}` 已收到，但当前没连上模型，所以还不能讲这道题。"
            "请检查接口密钥后再发一次。"
        )

    preview = text if len(text) <= 80 else f"{text[:80]}…"
    return (
        f"我收到了：{preview} 当前没连上模型，所以还不能具体讲题。"
        f"这是第 {max(history_size // 2, 0) + 1} 轮，连上之后把原文和题目一起发过来即可。"
    )


def build_structured_reply_json(
    *,
    supported: bool,
    question_type: str,
    subtype: str,
    answer: str,
    confidence: str,
    need_more_context: bool,
    unsupported_reason: str,
    stem_understanding: str,
    reasoning_steps: list[dict[str, object]],
    distractor_analysis: dict[str, str] | None = None,
    knowledge_methodology: list[str] | None = None,
    knowledge_cards: list[str] | None = None,
    follow_up: str = "",
) -> str:
    payload = {
        "supported": supported,
        "question_type": question_type,
        "subtype": subtype,
        "answer": answer,
        "confidence": confidence,
        "need_more_context": need_more_context,
        "unsupported_reason": unsupported_reason,
        "stem_understanding": stem_understanding,
        "reasoning_steps": reasoning_steps,
        "distractor_analysis": distractor_analysis or {"A": "", "B": "", "C": "", "D": ""},
        "knowledge_methodology": knowledge_methodology or [],
        "knowledge_cards": knowledge_cards or [],
        "follow_up": follow_up,
    }
    return json.dumps(payload, ensure_ascii=False)


def has_multiple_question_targets(*segments: str | None) -> bool:
    combined = "\n".join(segment for segment in segments if segment).strip()
    if not combined:
        return False

    explicit_refs = re.findall(r"第\s*\d+\s*[空题]", combined)
    if len(set(explicit_refs)) >= 2:
        return True

    if re.search(r"第\s*\d+\s*[空题]\s*(和|及|与|、|,|，|/)\s*第?\s*\d+\s*[空题]?", combined):
        return True

    if re.search(r"(两道题|两题|两个空|两空|多道题|多个空|都讲|一起讲|分别讲|挨个讲)", combined):
        if explicit_refs or re.search(r"\d+\s*(和|及|与|、|,|，|/)\s*\d+", combined):
            return True

    if re.search(r"(第\s*\d+\s*[空题].*第\s*\d+\s*[空题])", combined):
        return True

    return False


def build_multi_question_focus_reply() -> str:
    return build_structured_reply_json(
        supported=True,
        question_type="综合",
        subtype="多题待选择",
        answer="需要确认",
        confidence="high",
        need_more_context=True,
        unsupported_reason="",
        stem_understanding="这条消息里有不止一道待讲的题。为了讲清楚，需要先确定先看哪一道。",
        reasoning_steps=[
            {
                "step": 1,
                "focus": "先选定一题",
                "basis": "同时展开几道独立的题，容易把题号、空格和依据混在一起。",
                "conclusion": "请先指定要讲的题号、空格、截图位置或段落。"
            },
        ],
        knowledge_cards=[],
        follow_up="你说一下先讲哪一题就行，比如“先讲第12空”或“先看图片里第二题”。",
    )


def extract_json_object(text: str) -> str:
    start = -1
    depth = 0
    for index, char in enumerate(text):
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start != -1:
                    candidate = text[start : index + 1].strip()
                    if candidate.startswith("{") and candidate.endswith("}"):
                        return candidate
                    start = -1
    return ""


def repair_json_candidate(candidate: str) -> str:
    repaired = candidate
    repaired = re.sub(r'(:\s*\d+)"(?=\s*[,}])', r"\1", repaired)
    repaired = re.sub(r'(:\s*true|:\s*false)"(?=\s*[,}])', r"\1", repaired, flags=re.IGNORECASE)
    return repaired


def parse_structured_reply(reply: str) -> dict[str, object] | None:
    candidates = [reply.strip()]
    extracted = extract_json_object(reply)
    if extracted and extracted not in candidates:
        candidates.append(extracted)

    for candidate in candidates:
        if not candidate:
            continue
        for attempt in [candidate, repair_json_candidate(candidate)]:
            try:
                payload = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and "supported" in payload:
                return payload
    return None


def has_explicit_options(*segments: str | None) -> bool:
    combined = "\n".join(segment for segment in segments if segment).strip()
    if not combined:
        return False

    option_markers = [
        r"\bA[\.\)．、:：]\s*",
        r"\bB[\.\)．、:：]\s*",
        r"\bC[\.\)．、:：]\s*",
        r"\bD[\.\)．、:：]\s*",
    ]
    return all(re.search(marker, combined) for marker in option_markers)


def looks_like_grammar_fill(*segments: str | None) -> bool:
    combined = "\n".join(segment for segment in segments if segment).strip()
    if not combined:
        return False
    return bool(re.search(r"_{2,}|\([A-Za-z][A-Za-z\s\-']*\)|（[A-Za-z][A-Za-z\s\-']*）", combined))


def extract_candidate_challenge(message: str) -> str:
    patterns = [
        r"为什么不能填\s*[\"“'`]?([^，。；！？\s\"”'`]+)",
        r"为什么不是\s*[\"“'`]?([^，。；！？\s\"”'`]+)",
        r"为什么不选\s*[\"“'`]?([^，。；！？\s\"”'`]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_candidate_explanation(reasoning_steps: object, candidate: str) -> str:
    if not isinstance(reasoning_steps, list):
        return ""

    prioritized_signals = [candidate.lower()] if candidate else []
    fallback_signals = ["不能填", "不成立", "不符合", "缺少", "句子不完整", "非谓语", "不能单独作谓语"]

    for step in reasoning_steps:
        if not isinstance(step, dict):
            continue
        basis = str(step.get("basis", "")).strip()
        conclusion = str(step.get("conclusion", "")).strip()
        focus = str(step.get("focus", "")).strip()
        combined = " ".join(part for part in [focus, basis, conclusion] if part).strip()
        lowered = combined.lower()
        if prioritized_signals and any(signal in lowered for signal in prioritized_signals):
            return conclusion or basis or combined

    for step in reasoning_steps:
        if not isinstance(step, dict):
            continue
        basis = str(step.get("basis", "")).strip()
        conclusion = str(step.get("conclusion", "")).strip()
        focus = str(step.get("focus", "")).strip()
        combined = " ".join(part for part in [focus, basis, conclusion] if part).strip()
        if any(signal in combined for signal in fallback_signals):
            return conclusion or basis or combined
    return ""


def normalize_structured_reply(
    reply: str,
    *,
    message: str,
    image_context: str | None = None,
) -> str:
    del message, image_context
    return reply


def prior_chat_history(history: list[ChatMessage], message: str, *, limit: int) -> list[ChatMessage]:
    prior = list(history)
    if prior and prior[-1].sender == "user" and prior[-1].content.strip() == message.strip():
        prior = prior[:-1]
    return prior[-limit:]


def build_text_messages(message: str, history: list[ChatMessage]) -> list[dict]:
    messages: list[dict] = [
        {
            "role": "system",
            "content": get_teaching_prompt(),
        }
    ]
    for item in prior_chat_history(history, message, limit=10):
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
                f"{get_teaching_prompt()}\n\n"
                "当前用户上传了题目图片。结合图片、用户问题和已有上下文作答即可。"
            ),
        }
    ]
    for item in prior_chat_history(history, message, limit=6):
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
        temperature=0.85,
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
        temperature=0.7,
        messages=build_vision_messages(message, history, image, ocr_text=ocr_text),
    )
    return completion.choices[0].message.content or ""


def sse_event(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def model_supports_thinking(model: str) -> bool:
    name = (model or "").lower()
    return any(token in name for token in ("qwen3", "qwen-plus", "qwen-flash", "qwen-turbo", "qwq"))


def extract_stream_delta_text(delta: object) -> tuple[str, str]:
    content = getattr(delta, "content", None) or ""
    reasoning = getattr(delta, "reasoning_content", None) or ""
    if not reasoning:
        extra = getattr(delta, "model_extra", None)
        if isinstance(extra, dict):
            reasoning = extra.get("reasoning_content") or extra.get("reasoning") or ""
    if not isinstance(content, str):
        content = ""
    if not isinstance(reasoning, str):
        reasoning = ""
    return reasoning, content


def iter_completion_deltas(
    client: OpenAI,
    *,
    model: str,
    messages: list[dict],
    temperature: float,
    enable_thinking: bool = False,
):
    kwargs: dict[str, object] = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
        "stream": True,
    }
    if enable_thinking:
        kwargs["extra_body"] = {"enable_thinking": True}

    try:
        stream = client.chat.completions.create(**kwargs)
    except Exception:
        if not enable_thinking:
            raise
        kwargs.pop("extra_body", None)
        stream = client.chat.completions.create(**kwargs)

    for chunk in stream:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        if delta is None:
            continue
        reasoning, content = extract_stream_delta_text(delta)
        if reasoning or content:
            yield reasoning, content


def iter_streamed_reply_events(
    client: OpenAI,
    *,
    model: str,
    messages: list[dict],
    temperature: float,
    enable_thinking: bool,
    meta: ModelMeta,
    non_stream_fallback,
):
    content_parts: list[str] = []
    for reasoning, content in iter_completion_deltas(
        client,
        model=model,
        messages=messages,
        temperature=temperature,
        enable_thinking=enable_thinking,
    ):
        if reasoning:
            yield sse_event({"type": "thinking", "text": reasoning})
        if content:
            content_parts.append(content)
            yield sse_event({"type": "content", "text": content})

    reply = "".join(content_parts)
    if not reply.strip():
        logger.warning("Streamed completion was empty, retrying without stream")
        reply = non_stream_fallback()
        if reply:
            yield sse_event({"type": "content", "text": reply})

    yield sse_event({"type": "done", "reply": reply, "meta": meta.model_dump()})


def iter_chat_sse(request: ChatRequest):
    settings = get_model_settings()
    client = get_openai_client()
    text_model = request.preferred_text_model or settings.text_model
    vision_model = request.preferred_vision_model or settings.vision_model
    ocr_model = request.preferred_ocr_model or settings.ocr_model

    def demo_done() -> str:
        meta = ModelMeta(
            route="ocr_plus_vision" if request.latest_image and request.use_ocr_first else "vision" if request.latest_image else "demo",
            provider=settings.provider_name,
            text_model=text_model,
            vision_model=vision_model,
            ocr_model=ocr_model,
            used_demo_fallback=True,
        )
        reply = build_demo_reply(request.message, request.history, request.latest_image)
        return sse_event({"type": "done", "reply": reply, "meta": meta.model_dump()})

    if client is None:
        yield sse_event({"type": "status", "stage": "analyze", "text": "正在思考"})
        yield demo_done()
        return

    try:
        if request.latest_image is not None:
            ocr_text = None
            route: Literal["vision", "ocr_plus_vision"] = "vision"
            if request.use_ocr_first:
                route = "ocr_plus_vision"
                yield sse_event({"type": "status", "stage": "ocr", "text": "先把图片里的字认出来"})
                ocr_text = extract_ocr_text(client, request.latest_image, ocr_model)
            yield sse_event({"type": "status", "stage": "analyze", "text": "先把图里的题目看清楚"})
            meta = ModelMeta(
                route=route,
                provider=settings.provider_name,
                vision_model=vision_model,
                ocr_model=ocr_model if route == "ocr_plus_vision" else None,
            )
            yield from iter_streamed_reply_events(
                client,
                model=vision_model,
                messages=build_vision_messages(
                    request.message,
                    request.history,
                    request.latest_image,
                    ocr_text=ocr_text,
                ),
                temperature=0.7,
                enable_thinking=False,
                meta=meta,
                non_stream_fallback=lambda: generate_vision_reply(
                    client,
                    request.message,
                    request.history,
                    request.latest_image,
                    vision_model,
                    ocr_text=ocr_text,
                ),
            )
            return

        yield sse_event({"type": "status", "stage": "analyze", "text": "正在思考"})
        meta = ModelMeta(
            route="text",
            provider=settings.provider_name,
            text_model=text_model,
        )
        yield from iter_streamed_reply_events(
            client,
            model=text_model,
            messages=build_text_messages(request.message, request.history),
            temperature=0.85,
            enable_thinking=model_supports_thinking(text_model),
            meta=meta,
            non_stream_fallback=lambda: generate_text_reply(client, request.message, request.history, text_model),
        )
    except Exception:  # noqa: BLE001
        logger.exception("Streaming model pipeline failed, fallback to demo reply")
        yield sse_event({"type": "status", "stage": "fallback", "text": "换个方式继续想这道题"})
        yield demo_done()


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


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message 不能为空")
    return StreamingResponse(
        iter_chat_sse(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/")
@app.get("/demotrial.html")
async def index() -> FileResponse:
    if not HTML_FILE.exists():
        raise HTTPException(status_code=404, detail="demotrial.html 不存在")
    return FileResponse(HTML_FILE)


@app.get("/notes-data.js")
async def notes_data() -> FileResponse:
    if not NOTES_DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="notes-data.js 不存在")
    return FileResponse(NOTES_DATA_FILE, media_type="application/javascript")
