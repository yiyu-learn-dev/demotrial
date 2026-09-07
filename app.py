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
    parsed = parse_structured_reply(reply)
    if not parsed:
        return reply
    parsed["question_type"] = classify_question_type(message, parsed, image_context)
    return json.dumps(parsed, ensure_ascii=False)


def classify_question_type(
    message: str,
    parsed: dict[str, object],
    image_context: str | None = None,
) -> str:
    claimed = str(parsed.get("question_type") or "").strip()
    subtype = str(parsed.get("subtype") or "")
    stem = str(parsed.get("stem_understanding") or "")
    answer = str(parsed.get("answer") or "")
    combined = "\n".join(part for part in (message, image_context, claimed, subtype, stem, answer) if part)

    has_options = has_explicit_options(combined)
    grammar_fill = looks_like_grammar_fill(combined) or bool(
        re.search(r"语法填空|无提示词|有提示词|词性转换", combined)
    )
    numbered_blanks = bool(re.search(r"\(\s*\d{1,2}\s*\)|第\s*\d+\s*[空题]", combined))

    if re.search(r"七选五", combined):
        return "七选五"
    if has_options and not grammar_fill:
        return "完型"
    if grammar_fill or (numbered_blanks and not has_options):
        return "语法"
    if re.search(r"阅读理解|细节题|主旨", combined) and not numbered_blanks:
        return "阅读"
    if re.search(r"完型|完形", claimed) and not has_options:
        return "语法"
    if re.search(r"语法", claimed):
        return "语法"
    if re.search(r"完型|完形", claimed):
        return "完型"
    if re.search(r"阅读", claimed):
        return "阅读"
    if re.search(r"改错", claimed):
        return "改错"
    if re.search(r"翻译", claimed):
        return "翻译"
    return claimed or "语法"


CONVERSATION_RULES = """思考时只用自然语言分析题目：看哪一句、哪个空、为什么排除、填什么。
禁止在思考中出现 JSON、字段名、schema、输出格式、Markdown、代码块，以及 supported、reasoning_steps、knowledge_methodology、distractor_analysis、stem_understanding 这些词。想清楚后再输出 JSON。

对话记忆：
- 上文已有题干、原文、图片或已讲空格时，后续追问必须接着用，不得装作没看到。
- 学生只发空号或题号（如 13、第12空）时，视为同一套题继续讲，need_more_context 必须为 false。
- 材料里有多个空时，answer 按空号一次列全，例如 (11) a；(12) struggled；(13) to。
- knowledge_methodology 最多 3 条，写成“什么条件 → 填/用什么”，禁止“与理解能力相关”这类空话。
- 没有 A/B/C/D 的带空短文判为语法，不要判成完型。"""

BLANK_FOLLOWUP_RE = re.compile(
    r"^\s*(那|然后|接着|还有|再看|继续|再讲|那再看|那再讲)?"
    r"\s*(第\s*)?[（(]?\s*\d{1,3}\s*[)）]?\s*(空|题|小题)?"
    r"\s*[。.?？!！～~]*\s*$",
    re.IGNORECASE,
)


def is_blank_followup(message: str) -> bool:
    text = (message or "").strip()
    if not text or len(text) > 16:
        return False
    return bool(BLANK_FOLLOWUP_RE.match(text))


def is_greeting_history_item(item: ChatMessage) -> bool:
    if item.sender != "ai":
        return False
    text = (item.content or "").strip()
    return text.startswith("你好，我是陶然") or "阅读、完形、语法填空都可以直接问" in text


def compact_assistant_content(content: str) -> str:
    parsed = parse_structured_reply(content)
    if not parsed:
        return (content or "").strip()[:3000]

    parts: list[str] = []
    qtype = str(parsed.get("question_type") or "").strip()
    subtype = str(parsed.get("subtype") or "").strip()
    header = " / ".join(part for part in (qtype, subtype) if part)
    if header:
        parts.append(f"题型：{header}")
    stem = str(parsed.get("stem_understanding") or "").strip()
    if stem:
        parts.append(f"题意：{stem}")
    answer = str(parsed.get("answer") or "").strip()
    if answer:
        parts.append(f"已给答案：{answer}")
    steps = parsed.get("reasoning_steps")
    briefs: list[str] = []
    if isinstance(steps, list):
        for step in steps[:5]:
            if not isinstance(step, dict):
                continue
            line = str(step.get("conclusion") or step.get("basis") or "").strip()
            if line and line not in briefs:
                briefs.append(line)
    if briefs:
        parts.append("已讲要点：" + "；".join(briefs[:4]))
    follow = str(parsed.get("follow_up") or "").strip()
    if follow:
        parts.append(f"收尾：{follow}")
    return "\n".join(parts) if parts else str(content)[:1500]


def decorate_current_user_message(message: str) -> str:
    text = (message or "").strip()
    if is_blank_followup(text):
        return (
            "这是对上一题的追问。必须结合上文已有题干、原文、图片和已给答案继续讲当前这个空，"
            "不要说只看到了当前这几个字，也不要让学生重发材料。need_more_context 必须为 false。\n\n"
            f"学生追问：{text}"
        )
    return text


def prior_chat_history(history: list[ChatMessage], message: str, *, limit: int) -> list[ChatMessage]:
    prior = list(history)
    if prior and prior[-1].sender == "user" and prior[-1].content.strip() == message.strip():
        prior = prior[:-1]
    return prior[-limit:]


def iter_compacted_history(history: list[ChatMessage], message: str, *, limit: int) -> list[tuple[str, str]]:
    prior = prior_chat_history(history, message, limit=max(limit * 3, 18))
    compacted: list[tuple[str, str]] = []
    for item in prior:
        if is_greeting_history_item(item):
            continue
        content = compact_assistant_content(item.content) if item.sender == "ai" else (item.content or "")
        content = content.strip()
        if not content:
            continue
        role = "assistant" if item.sender == "ai" else "user"
        compacted.append((role, content[:4000]))
    return compacted[-limit:]


def build_text_messages(message: str, history: list[ChatMessage]) -> list[dict]:
    messages: list[dict] = [
        {"role": "system", "content": get_teaching_prompt()},
        {"role": "system", "content": CONVERSATION_RULES},
    ]
    for role, content in iter_compacted_history(history, message, limit=12):
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": decorate_current_user_message(message)})
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
                f"{CONVERSATION_RULES}\n\n"
                "当前用户上传了题目图片。结合图片、用户问题和已有上下文作答即可。"
            ),
        }
    ]
    for role, content in iter_compacted_history(history, message, limit=8):
        messages.append({"role": role, "content": content})

    user_content: list[dict] = [{"type": "text", "text": decorate_current_user_message(message)}]
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
    source_message: str = "",
    image_context: str | None = None,
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

    reply = normalize_structured_reply(reply, message=source_message, image_context=image_context)
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
                source_message=request.message,
                image_context=ocr_text,
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
            source_message=request.message,
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
            reply = normalize_structured_reply(
                reply,
                message=request.message,
                image_context=ocr_text,
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
        reply = normalize_structured_reply(reply, message=request.message)
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
