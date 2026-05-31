from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_text_splitters.base import TextSplitter

from api.utils.logger import logger
from api.utils.llm_client import LLMProvider, config
from deepagent.core.prompts.prompt import EXTRACT_ENFORCEMENT_PROMPT


def _clean_legal_text(raw_text: str) -> str:
    text = (raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    m = re.search(r"(?im)^\s*chương\s+[ivxlcdm0-9]+\b", text)
    return text[m.start() :].strip() if m else text.strip()


def _roman_to_int(roman: str) -> int | None:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    s = (roman or "").upper().strip()
    if not s or any(ch not in values for ch in s):
        return None
    total = 0
    prev = 0
    for ch in reversed(s):
        cur = values[ch]
        total = total - cur if cur < prev else total + cur
        prev = cur
    return total


def _extract_doc_type_and_name(raw_text: str) -> tuple[str, str]:
    upper = (raw_text or "").upper()
    if "NGHỊ ĐỊNH" in upper:
        doc_type = "nghi_dinh"
    elif "THÔNG TƯ" in upper:
        doc_type = "thong_tu"
    else:
        doc_type = "luat"

    first_content_line = ""
    for line in (raw_text or "").splitlines():
        t = line.strip()
        if t and len(t) > 3:
            first_content_line = t
            break
    return doc_type, first_content_line or "van_ban_phap_luat"


def _extract_doc_id(raw_text: str, doc_type: str) -> str:
    m = re.search(r"\b(\d+)\s*/\s*(\d{4})\s*/\s*([A-ZĐ\-]+)\b", (raw_text or "").upper())
    if m:
        return f"{doc_type[:2]}_{m.group(1)}_{m.group(2)}"
    return f"{doc_type}_unknown"




def _split_markdown_preface_and_body(text_md: str) -> tuple[str, str]:
    """
    Tách markdown thành:
    - preface: từ đầu tới trước khi gặp **Chương 1 / I** hoặc **Điều 1 / I**
    - body: phần còn lại
    """
    text = text_md or ""
    start_pattern = re.compile(
        r"(?im)^\s*\*\*(?:chương|điều)\s+(?:1|[ivxlcdm]+)\b.*?\*\*"
    )

    m = start_pattern.search(text)
    if not m:
        return text.strip(), text.strip()

    print(f"MATCH: {text[m.start():m.end()]}")
    return text[: m.start()].strip(), text[m.start() :].strip()


_ENFORCEMENT_CLAUSE_PATTERN = re.compile(
    r"(?is)(?:\*\*\s*)?điều\s+khoản\s+thi\s+hành(?:\s*\*\*)?"
)


def _split_enforcement_clause(section: str) -> tuple[str, str]:
    """Tách phần trước và từ marker 'điều khoản thi hành' trở đi."""
    text = (section or "").strip()
    if not text:
        return "", ""
    match = _ENFORCEMENT_CLAUSE_PATTERN.search(text)
    if not match:
        return text, ""
    return text[: match.start()].strip(), text[match.start() :].strip()


def _split_markdown_body_and_footer(text_md: str, doc_type: str) -> tuple[str, str, str]:
    """
    Tách markdown thành:
    - body: phần nội dung chính (trước điều khoản thi hành).
    - footer: phần cuối văn bản (layout tùy doc_type).
    - enforcement_clause: từ "điều khoản thi hành" đến trước footer.

    Rule:
    - nghị định/nghị định sửa đổi: tìm marker **Nơi nhận:
    - luật/luật sửa đổi: tìm marker **CHỦ TỊCH QUỐC HỘI**
    - thông tư/thông tư sửa đổi: tìm marker **Nơi nhận:
    - Với nghị định/thông tư: footer bắt đầu từ **Nơi nhận: và kết thúc ở
      cụm tên in đậm dạng viết hoa chữ đầu (ví dụ: **Trần Văn A**).
    - Với luật: footer là vùng quanh marker (+/-50 ký tự).
    """

    text = (text_md or "").strip()
    normalized_doc_type = (doc_type or "").strip().lower()

    luat_types = {"luat", "luat_sua_doi"}
    nghi_dinh_types = {"nghi_dinh", "nghi_dinh_sua_doi"}
    thong_tu_types = {"thong_tu", "thong_tu_sua_doi"}

    if normalized_doc_type in luat_types:
        footer_pattern = re.compile(r"(?is)\*\*\s*chủ\s+tịch\s+quốc\s+hội\s*\*\*")
    elif normalized_doc_type in nghi_dinh_types or normalized_doc_type in thong_tu_types:
        footer_start_pattern = re.compile(r"(?is)\*\*\s*nơi\s+nhận\s*:")
        footer_end_pattern = re.compile(
            r"(?is)(?:\*\*\s*[A-ZÀ-ỸĐ0-9\.\-\s]+\s*\*\*\s*)*"
            r"\*\*\s*[A-ZÀ-ỸĐ][a-zà-ỹđ]+(?:\s+[A-ZÀ-ỸĐ][a-zà-ỹđ]+)+\s*\*\*"
        )

        start_match = footer_start_pattern.search(text)
        if not start_match:
            body, enforcement_clause = _split_enforcement_clause(text)
            return body, "", enforcement_clause

        start_idx = start_match.start()
        end_match = footer_end_pattern.search(text, pos=start_idx)
        body_part = text[:start_idx].strip()
        footer = (
            text[start_idx:end_match.end()].strip()
            if end_match
            else text[start_idx:].strip()
        )
        body, enforcement_clause = _split_enforcement_clause(body_part)
        return body, footer, enforcement_clause
    else:
        body, enforcement_clause = _split_enforcement_clause(text)
        return body, "", enforcement_clause

    m = footer_pattern.search(text)
    if not m:
        body, enforcement_clause = _split_enforcement_clause(text)
        return body, "", enforcement_clause

    marker_start, marker_end = m.start(), m.end()
    footer_start = max(0, marker_start - 50)
    footer_end = min(len(text), marker_end + 50)

    body_part = text[:marker_start].strip()
    footer = text[footer_start:footer_end].strip()
    body, enforcement_clause = _split_enforcement_clause(body_part)
    return body, footer, enforcement_clause


_VALID_RELATION_TYPES = frozenset({"based_on", "implements"})
_VALID_REPLACEMENT_TYPES = frozenset({"full_replacement", "partial_replacement"})


class LLMResponseValidationError(ValueError):
    """Raised when LLM output does not match the expected prompt schema."""


def _parse_llm_json_array(raw: str) -> dict[str, Any]:
    """
    Parse and validate LLM JSON against EXTRACT_ENFORCEMENT_PROMPT output schema.

    Expected shape:
    {
      "relations": [{"relation_type": "based_on"|"implements", "relation_to": str}, ...],
      "enforcement": {
        "effective_time": str | null,
        "replacement_relations": [
          {"replacement_type": "full_replacement"|"partial_replacement", "relation_to": str}, ...
        ]
      }
    }
    """
    text = (raw or "").strip()
    if not text:
        raise LLMResponseValidationError("LLM response is empty")

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMResponseValidationError(
            f"LLM response is not valid JSON: {exc.msg}"
        ) from exc

    if not isinstance(parsed, dict):
        raise LLMResponseValidationError("LLM response must be a JSON object")

    relations = parsed.get("relations")
    if relations is None:
        raise LLMResponseValidationError("Missing required field: relations")
    if not isinstance(relations, list):
        raise LLMResponseValidationError("Field 'relations' must be a list")

    for index, item in enumerate(relations):
        if not isinstance(item, dict):
            raise LLMResponseValidationError(f"relations[{index}] must be an object")
        rel_type = item.get("relation_type")
        if rel_type not in _VALID_RELATION_TYPES:
            raise LLMResponseValidationError(
                f"relations[{index}].relation_type must be one of "
                f"{sorted(_VALID_RELATION_TYPES)}, got {rel_type!r}"
            )
        rel_to = item.get("relation_to")
        if not isinstance(rel_to, str) or not rel_to.strip():
            raise LLMResponseValidationError(
                f"relations[{index}].relation_to must be a non-empty string"
            )

    enforcement = parsed.get("enforcement")
    if enforcement is None:
        raise LLMResponseValidationError("Missing required field: enforcement")
    if not isinstance(enforcement, dict):
        raise LLMResponseValidationError("Field 'enforcement' must be an object")

    effective_time = enforcement.get("effective_time")
    if effective_time is not None and not isinstance(effective_time, str):
        raise LLMResponseValidationError(
            "enforcement.effective_time must be a string or null"
        )

    replacement_relations = enforcement.get("replacement_relations")
    if replacement_relations is None:
        raise LLMResponseValidationError(
            "Missing required field: enforcement.replacement_relations"
        )
    if not isinstance(replacement_relations, list):
        raise LLMResponseValidationError(
            "Field 'enforcement.replacement_relations' must be a list"
        )

    for index, item in enumerate(replacement_relations):
        if not isinstance(item, dict):
            raise LLMResponseValidationError(
                f"enforcement.replacement_relations[{index}] must be an object"
            )
        replacement_type = item.get("replacement_type")
        if replacement_type not in _VALID_REPLACEMENT_TYPES:
            raise LLMResponseValidationError(
                f"enforcement.replacement_relations[{index}].replacement_type must be one of "
                f"{sorted(_VALID_REPLACEMENT_TYPES)}, got {replacement_type!r}"
            )
        rel_to = item.get("relation_to")
        if not isinstance(rel_to, str) or not rel_to.strip():
            raise LLMResponseValidationError(
                f"enforcement.replacement_relations[{index}].relation_to "
                "must be a non-empty string"
            )

    return parsed


def _load_existing_documents() -> list[str]:
    from api.db.models import Document, LexDocumentChunk, db

    names: list[str] = []
    try:
        with db.connection_context():
            for row in (
                Document.select(Document.law_name)
                .where(Document.law_name.is_null(False))
                .distinct()
            ):
                name = (row.law_name or "").strip()
                if name:
                    names.append(name)
            for row in LexDocumentChunk.select(
                LexDocumentChunk.doc_name, LexDocumentChunk.law_name
            ).distinct():
                for field in (row.doc_name, row.law_name):
                    name = (field or "").strip()
                    if name:
                        names.append(name)
    except Exception:
        logger.exception("Failed to load existing documents for relation extraction")
    return list(dict.fromkeys(names))


def resolve_document_relation(
    extract_llm: BaseChatModel | None,
    preface_text_md: str,
    enforcement_clause_md: str,
) -> dict[str, list[str]]:
    """Extract document-level based_on / implements relations from preface via LLM."""
    empty = {"based_on": [], "implements": []}
    preface = (preface_text_md or "").strip()
    if not preface or extract_llm is None:
        return empty

    existing_documents = _load_existing_documents()
    prompt = (
        EXTRACT_ENFORCEMENT_PROMPT.replace(
            "{{EXISTING_DOCUMENTS_JSON}}",
            json.dumps(existing_documents, ensure_ascii=False),
        )
        .replace("{{INPUT_TEXT}}", preface)
        .replace("{{ENFORCEMENT_CLAUSE}}", enforcement_clause_md or "")
    )

    response = extract_llm.invoke([HumanMessage(content=prompt)])
    raw = getattr(response, "content", str(response))
    parsed = _parse_llm_json_array(raw)

    based_on: list[str] = []
    implements: list[str] = []
    for item in parsed["relations"]:
        rel_type = (item.get("relation_type") or "").strip().lower()
        rel_to = (item.get("relation_to") or "").strip()
        if rel_type == "based_on":
            based_on.append(rel_to)
        elif rel_type == "implements":
            implements.append(rel_to)

    return {
        "based_on": list(dict.fromkeys(based_on)),
        "implements": list(dict.fromkeys(implements)),
    }


class LawTextSplitter(TextSplitter):

    """Split Vietnamese legal text to JSON-per-clause chunks."""

    def __init__(self, extract_llm: BaseChatModel | None = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.extract_llm = extract_llm

    def split_text(self, text_md: str) -> list[str]:
        preface_text_md, body_text_md = _split_markdown_preface_and_body(text_md)

        # In ra để debug nhanh cơ chế split 2 phần có đúng không.
        print(f"[LawTextSplitter] preface_len={len(preface_text_md)} body_len={len(body_text_md)}")
        print("[LawTextSplitter] preface_preview=", preface_text_md)
        print("[LawTextSplitter] body_preview=", body_text_md[:300])
        llm_client = LLMProvider(self.extract_llm)
        response_doc_type = llm_client.response(dialogue=[{"role": "user", "content": body_text_md}], prompt_template_number=1)
        llm_doc_type = (response_doc_type or {}).get("doc_type")

        fallback_doc_type, doc_name = _extract_doc_type_and_name(text_md)
        doc_type = (llm_doc_type or fallback_doc_type or "luat").strip().lower()
        doc_id = _extract_doc_id(text_md, doc_type)

        body_text_md, footer_text_md, enforcement_clause_md = _split_markdown_body_and_footer(
            body_text_md, doc_type
        )
        response_signer_role = llm_client.response(dialogue=[{"role": "user", "content": footer_text_md}], prompt_template_number=2)
        print(f"[LawTextSplitter] response_signer_role={response_signer_role}")
        print(f"[LawTextSplitter] footer_text_md={footer_text_md}...")
        print(f"[LawTextSplitter] enforcement_clause_md={enforcement_clause_md[:300]}...")
        print(f"[LawTextSplitter] body_text_md={body_text_md[-300:]}...")
        logger.debug(
            "[LawTextSplitter] doc_type={} body_len={} footer_len={} enforcement_len={}",
            doc_type,
            len(body_text_md),
            len(footer_text_md),
            len(enforcement_clause_md),
        )

        if doc_type == "luat":
            return self._split_strategy_luat(
                text_md=text_md,
                body_text_md=body_text_md,
                preface_text_md=preface_text_md,
                enforcement_clause_md=enforcement_clause_md,
                doc_type=doc_type,
                doc_name=doc_name,
                doc_id=doc_id,
                extract_llm=self.extract_llm,
            )
        if doc_type == "luat_sua_doi":
            return self._split_strategy_luat_sua_doi(
                text_md=text_md,
                body_text_md=body_text_md,
                preface_text_md=preface_text_md,
                enforcement_clause_md=enforcement_clause_md,
                doc_type=doc_type,
                doc_name=doc_name,
                doc_id=doc_id,
                extract_llm=self.extract_llm,
            )
        if doc_type == "nghi_dinh":
            return self._split_strategy_nghi_dinh(
                text_md=text_md,
                body_text_md=body_text_md,
                preface_text_md=preface_text_md,
                enforcement_clause_md=enforcement_clause_md,
                doc_type=doc_type,
                doc_name=doc_name,
                doc_id=doc_id,
                extract_llm=self.extract_llm,
            )
        if doc_type == "nghi_dinh_sua_doi":
            return self._split_strategy_nghi_dinh_sua_doi(
                text_md=text_md,
                body_text_md=body_text_md,
                preface_text_md=preface_text_md,
                enforcement_clause_md=enforcement_clause_md,
                doc_type=doc_type,
                doc_name=doc_name,
                doc_id=doc_id,
                extract_llm=self.extract_llm,
            )
        if doc_type == "thong_tu":
            return self._split_strategy_thong_tu(
                text_md=text_md,
                body_text_md=body_text_md,
                preface_text_md=preface_text_md,
                enforcement_clause_md=enforcement_clause_md,
                doc_type=doc_type,
                doc_name=doc_name,
                doc_id=doc_id,
                extract_llm=self.extract_llm,
            )
        if doc_type == "thong_tu_sua_doi":
            return self._split_strategy_thong_tu_sua_doi(
                text_md=text_md,
                body_text_md=body_text_md,
                preface_text_md=preface_text_md,
                enforcement_clause_md=enforcement_clause_md,
                doc_type=doc_type,
                doc_name=doc_name,
                doc_id=doc_id,
                extract_llm=self.extract_llm,
            )
        return self._split_strategy_default(
            text_md=text_md,
            body_text_md=body_text_md,
            preface_text_md=preface_text_md,
            enforcement_clause_md=enforcement_clause_md,
            doc_type=doc_type,
            doc_name=doc_name,
            doc_id=doc_id,
            extract_llm=self.extract_llm,
        )

    def _split_strategy_luat(
        self,
        text_md: str,
        body_text_md: str,
        preface_text_md: str,
        enforcement_clause_md: str,
        doc_type: str,
        doc_name: str,
        doc_id: str,
        extract_llm: BaseChatModel,
    ) -> list[str]:
        doc_relations = resolve_document_relation(extract_llm, preface_text_md, enforcement_clause_md)
        logger.debug("[LawTextSplitter] doc_relations=%s", doc_relations)
        legal_text = _clean_legal_text(body_text_md.replace("**", ""))
        if not legal_text:
            return []

        chapter_pattern = re.compile(
            r"(?ims)^\s*chương\s+([ivxlcdm0-9]+)\s*[\.:-]?\s*(.*?)\n(.*?)(?=^\s*chương\s+[ivxlcdm0-9]+\b|\Z)"
        )
        article_pattern = re.compile(
            r"(?ims)^\s*điều\s+(\d+)[\.:]?\s*(.*?)\n(.*?)(?=^\s*điều\s+\d+\b|\Z)"
        )
        clause_pattern = re.compile(
            r"(?ims)^\s*(\d+)\.\s*(.*?)(?=^\s*\d+\.\s+|^\s*điều\s+\d+\b|\Z)"
        )
        point_pattern = re.compile(
            r"(?ims)^\s*([a-z])\)\s*(.*?)(?=^\s*[a-z]\)\s+|^\s*\d+\.\s+|^\s*điều\s+\d+\b|\Z)"
        )

        chunks: list[str] = []
        found_chapter = False
        for ch_match in chapter_pattern.finditer(legal_text):
            found_chapter = True
            chapter_raw = ch_match.group(1).strip()
            chapter_title = (ch_match.group(2) or "").strip() or None
            chapter_num = int(chapter_raw) if chapter_raw.isdigit() else _roman_to_int(chapter_raw)
            chapter_body = (ch_match.group(3) or "").strip()

            for art in article_pattern.finditer(chapter_body):
                article_num = int(art.group(1))
                article_title = (art.group(2) or "").strip()
                article_body = (art.group(3) or "").strip()
                clause_matches = list(clause_pattern.finditer(article_body))

                if not clause_matches:
                    content = article_body.strip()
                    if not content:
                        continue
                    item = {
                        "doc_id": doc_id,
                        "chunk_id": f"{doc_id}_dieu_{article_num}_khoan_1",
                        "doc_type": doc_type,
                        "doc_name": doc_name,
                        "chapter": chapter_num,
                        "chapter_text": chapter_title,
                        "article": article_num,
                        "article_text": article_title,
                        "clause": 1,
                        "point": None,
                        "content": content,
                        "full_path": f"{doc_name} > Chương {chapter_raw} > Điều {article_num} > Khoản 1",
                    }
                    chunks.append(json.dumps(item, ensure_ascii=False))
                    continue

                for clause_match in clause_matches:
                    clause_num = int(clause_match.group(1))
                    clause_content = (clause_match.group(2) or "").strip()
                    if not clause_content:
                        continue

                    point_matches = list(point_pattern.finditer(clause_content))
                    if point_matches:
                        for point_match in point_matches:
                            point_code = (point_match.group(1) or "").strip().lower()
                            point_content = (point_match.group(2) or "").strip()
                            if not point_content:
                                continue
                            item = {
                                "doc_id": doc_id,
                                "chunk_id": (
                                    f"{doc_id}_dieu_{article_num}_khoan_{clause_num}_diem_{point_code}"
                                ),
                                "doc_type": doc_type,
                                "doc_name": doc_name,
                                "chapter": chapter_num,
                                "chapter_text": chapter_title,
                                "article": article_num,
                                "article_text": article_title,
                                "clause": clause_num,
                                "point": point_code,
                                "content": point_content,
                                "full_path": (
                                    f"{doc_name} > Chương {chapter_raw} > Điều {article_num} > "
                                    f"Khoản {clause_num} > Điểm {point_code}"
                                ),
                            }
                            chunks.append(json.dumps(item, ensure_ascii=False))
                    else:
                        item = {
                            "doc_id": doc_id,
                            "chunk_id": f"{doc_id}_dieu_{article_num}_khoan_{clause_num}",
                            "doc_type": doc_type,
                            "doc_name": doc_name,
                            "chapter": chapter_num,
                            "chapter_text": chapter_title,
                            "article": article_num,
                            "article_text": article_title,
                            "clause": clause_num,
                            "point": None,
                            "content": clause_content,
                            "full_path": (
                                f"{doc_name} > Chương {chapter_raw} > Điều {article_num} > Khoản {clause_num}"
                            ),
                        }
                        chunks.append(json.dumps(item, ensure_ascii=False))

        if found_chapter:
            return chunks
        return self._split_common_article_clause(
            body_text_md=body_text_md,
            doc_type=doc_type,
            doc_name=doc_name,
            doc_id=doc_id,
            extract_llm=extract_llm,
        )

    def _split_strategy_luat_sua_doi(
        self,
        text_md: str,
        body_text_md: str,
        preface_text_md: str,
        enforcement_clause_md: str,
        doc_type: str,
        doc_name: str,
        doc_id: str,
        extract_llm: BaseChatModel,
    ) -> list[str]:
        doc_relations = resolve_document_relation(extract_llm, preface_text_md, enforcement_clause_md)
        logger.debug("[LawTextSplitter] doc_relations=%s", doc_relations)
        return self._split_common_article_clause(
            body_text_md=body_text_md,
            doc_type=doc_type,
            doc_name=doc_name,
            doc_id=doc_id,
            extract_llm=extract_llm,
        )

    def _split_strategy_nghi_dinh(
        self,
        text_md: str,
        body_text_md: str,
        preface_text_md: str,
        enforcement_clause_md: str,
        doc_type: str,
        doc_name: str,
        doc_id: str,
        extract_llm: BaseChatModel,
    ) -> list[str]:
        doc_relations = resolve_document_relation(extract_llm, preface_text_md, enforcement_clause_md)
        logger.debug("[LawTextSplitter] doc_relations=%s", doc_relations)
        legal_text = _clean_legal_text(body_text_md.replace("**", ""))
        if not legal_text:
            return []

        chapter_pattern = re.compile(
            r"(?ims)^\s*chương\s+([ivxlcdm0-9]+)\s*[\.:-]?\s*(.*?)\n(.*?)(?=^\s*chương\s+[ivxlcdm0-9]+\b|\Z)"
        )
        article_pattern = re.compile(
            r"(?ims)^\s*điều\s+(\d+)[\.:]?\s*(.*?)\n(.*?)(?=^\s*điều\s+\d+\b|\Z)"
        )
        clause_pattern = re.compile(
            r"(?ims)^\s*(\d+)\.\s*(.*?)(?=^\s*\d+\.\s+|^\s*điều\s+\d+\b|\Z)"
        )
        point_pattern = re.compile(
            r"(?ims)^\s*([a-z])\)\s*(.*?)(?=^\s*[a-z]\)\s+|^\s*\d+\.\s+|^\s*điều\s+\d+\b|\Z)"
        )

        chunks: list[str] = []
        found_chapter = False
        for ch_match in chapter_pattern.finditer(legal_text):
            found_chapter = True
            chapter_raw = ch_match.group(1).strip()
            chapter_title = (ch_match.group(2) or "").strip() or None
            chapter_num = int(chapter_raw) if chapter_raw.isdigit() else _roman_to_int(chapter_raw)
            chapter_body = (ch_match.group(3) or "").strip()

            for art in article_pattern.finditer(chapter_body):
                article_num = int(art.group(1))
                article_title = (art.group(2) or "").strip()
                article_body = (art.group(3) or "").strip()
                clause_matches = list(clause_pattern.finditer(article_body))

                if not clause_matches:
                    content = article_body.strip()
                    if not content:
                        continue
                    item = {
                        "doc_id": doc_id,
                        "chunk_id": f"{doc_id}_dieu_{article_num}_khoan_1",
                        "doc_type": doc_type,
                        "doc_name": doc_name,
                        "chapter": chapter_num,
                        "chapter_text": chapter_title,
                        "article": article_num,
                        "article_text": article_title,
                        "clause": 1,
                        "point": None,
                        "content": content,
                        "full_path": f"{doc_name} > Chương {chapter_raw} > Điều {article_num} > Khoản 1",
                    }
                    chunks.append(json.dumps(item, ensure_ascii=False))
                    continue

                for clause_match in clause_matches:
                    clause_num = int(clause_match.group(1))
                    clause_content = (clause_match.group(2) or "").strip()
                    if not clause_content:
                        continue

                    point_matches = list(point_pattern.finditer(clause_content))
                    if point_matches:
                        for point_match in point_matches:
                            point_code = (point_match.group(1) or "").strip().lower()
                            point_content = (point_match.group(2) or "").strip()
                            if not point_content:
                                continue
                            item = {
                                "doc_id": doc_id,
                                "chunk_id": (
                                    f"{doc_id}_dieu_{article_num}_khoan_{clause_num}_diem_{point_code}"
                                ),
                                "doc_type": doc_type,
                                "doc_name": doc_name,
                                "chapter": chapter_num,
                                "chapter_text": chapter_title,
                                "article": article_num,
                                "article_text": article_title,
                                "clause": clause_num,
                                "point": point_code,
                                "content": point_content,
                                "full_path": (
                                    f"{doc_name} > Chương {chapter_raw} > Điều {article_num} > "
                                    f"Khoản {clause_num} > Điểm {point_code}"
                                ),
                            }
                            chunks.append(json.dumps(item, ensure_ascii=False))
                    else:
                        item = {
                            "doc_id": doc_id,
                            "chunk_id": f"{doc_id}_dieu_{article_num}_khoan_{clause_num}",
                            "doc_type": doc_type,
                            "doc_name": doc_name,
                            "chapter": chapter_num,
                            "chapter_text": chapter_title,
                            "article": article_num,
                            "article_text": article_title,
                            "clause": clause_num,
                            "point": None,
                            "content": clause_content,
                            "full_path": (
                                f"{doc_name} > Chương {chapter_raw} > Điều {article_num} > Khoản {clause_num}"
                            ),
                        }
                        chunks.append(json.dumps(item, ensure_ascii=False))

        if found_chapter:
            return chunks
        return self._split_common_article_clause(
            body_text_md=body_text_md,
            doc_type=doc_type,
            doc_name=doc_name,
            doc_id=doc_id,
            extract_llm=extract_llm,
        )

    def _split_strategy_nghi_dinh_sua_doi(
        self,
        text_md: str,
        body_text_md: str,
        preface_text_md: str,
        enforcement_clause_md: str,
        doc_type: str,
        doc_name: str,
        doc_id: str,
        extract_llm: BaseChatModel,
    ) -> list[str]:
        doc_relations = resolve_document_relation(extract_llm, preface_text_md, enforcement_clause_md)
        logger.debug("[LawTextSplitter] doc_relations=%s", doc_relations)
        return self._split_common_article_clause(
            body_text_md=body_text_md,
            doc_type=doc_type,
            doc_name=doc_name,
            doc_id=doc_id,
            extract_llm=extract_llm,
        )

    def _split_strategy_thong_tu(
        self,
        text_md: str,
        body_text_md: str,
        preface_text_md: str,
        enforcement_clause_md: str,
        doc_type: str,
        doc_name: str,
        doc_id: str,
        extract_llm: BaseChatModel,
    ) -> list[str]:
        doc_relations = resolve_document_relation(extract_llm, preface_text_md, enforcement_clause_md)
        logger.debug("[LawTextSplitter] doc_relations=%s", doc_relations)
        return self._split_common_article_clause(
            body_text_md=body_text_md,
            doc_type=doc_type,
            doc_name=doc_name,
            doc_id=doc_id,
            extract_llm=extract_llm,
        )

    def _split_strategy_thong_tu_sua_doi(
        self,
        text_md: str,
        body_text_md: str,
        preface_text_md: str,
        enforcement_clause_md: str,
        doc_type: str,
        doc_name: str,
        doc_id: str,
        extract_llm: BaseChatModel,
    ) -> list[str]:
        doc_relations = resolve_document_relation(extract_llm, preface_text_md, enforcement_clause_md)
        logger.debug("[LawTextSplitter] doc_relations=%s", doc_relations)
        return self._split_common_article_clause(
            body_text_md=body_text_md,
            doc_type=doc_type,
            doc_name=doc_name,
            doc_id=doc_id,
            extract_llm=extract_llm,
        )

    def _split_strategy_default(
        self,
        text_md: str,
        body_text_md: str,
        preface_text_md: str,
        enforcement_clause_md: str,
        doc_type: str,
        doc_name: str,
        doc_id: str,
    ) -> list[str]:
        return self._split_common_article_clause(
            body_text_md=body_text_md,
            doc_type=doc_type,
            doc_name=doc_name,
            doc_id=doc_id,
        )

    def _split_common_article_clause(
        self,
        body_text_md: str,
        doc_type: str,
        doc_name: str,
        doc_id: str,
        extract_llm: BaseChatModel,
    ) -> list[str]:
        llm_client = LLMProvider(extract_llm)
        legal_text = _clean_legal_text(body_text_md.replace("**", ""))
        if not legal_text:
            return []

        chapter_pattern = re.compile(
            r"(?ims)^\s*chương\s+([ivxlcdm0-9]+)\s*\n?(.*?)(?=^\s*chương\s+[ivxlcdm0-9]+\b|\Z)"
        )
        article_pattern = re.compile(
            r"(?ims)^\s*điều\s+(\d+)[\.:]?\s*(.*?)\n(.*?)(?=^\s*điều\s+\d+\b|\Z)"
        )
        clause_pattern = re.compile(
            r"(?ims)^\s*(\d+)\.\s*(.*?)(?=^\s*\d+\.\s+|\Z)"
        )

        chunks: list[str] = []
        found_chapter = False
        for ch_match in chapter_pattern.finditer(legal_text):
            found_chapter = True
            ch_raw = ch_match.group(1).strip()
            chapter_text = (ch_match.group(2) or "").strip() or None
            chapter_num = int(ch_raw) if ch_raw.isdigit() else _roman_to_int(ch_raw)
            chapter_body = ch_match.group(0)

            for art in article_pattern.finditer(chapter_body):
                article_num = int(art.group(1))
                article_title = (art.group(2) or "").strip()
                article_body = (art.group(3) or "").strip()

                clause_matches = list(clause_pattern.finditer(article_body))
                if not clause_matches:
                    clause_matches = [None]

                for clause_match in clause_matches:
                    if clause_match is None:
                        clause_num = 1
                        content = article_body.strip()
                    else:
                        clause_num = int(clause_match.group(1))
                        content = (clause_match.group(2) or "").strip()

                    if not content:
                        continue

                    item = {
                        "doc_id": doc_id,
                        "chunk_id": f"{doc_id}_dieu_{article_num}_khoan_{clause_num}",
                        "doc_type": doc_type,
                        "doc_name": doc_name,
                        "chapter": chapter_num,
                        "chapter_text": chapter_text,
                        "article": article_num,
                        "article_text": article_title,
                        "clause": clause_num,
                        "content": content,
                        "full_path": (
                            f"{doc_name} > Chương {ch_raw} > Điều {article_num} > Khoản {clause_num}"
                        ),
                    }
                    chunks.append(json.dumps(item, ensure_ascii=False))

        if found_chapter:
            return chunks

        # Fallback: no chapter -> split directly by article
        for art in article_pattern.finditer(legal_text):
            article_num = int(art.group(1))
            article_title = (art.group(2) or "").strip()
            article_body = (art.group(3) or "").strip()
            clause_matches = list(clause_pattern.finditer(article_body))
            if not clause_matches:
                clause_matches = [None]
            for clause_match in clause_matches:
                if clause_match is None:
                    clause_num = 1
                    content = article_body.strip()
                else:
                    clause_num = int(clause_match.group(1))
                    content = (clause_match.group(2) or "").strip()
                if not content:
                    continue
                item = {
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_dieu_{article_num}_khoan_{clause_num}",
                    "doc_type": doc_type,
                    "doc_name": doc_name,
                    "chapter": None,
                    "chapter_text": None,
                    "article": article_num,
                    "article_text": article_title,
                    "clause": clause_num,
                    "content": content,
                    "full_path": f"{doc_name} > Điều {article_num} > Khoản {clause_num}",
                }
                chunks.append(json.dumps(item, ensure_ascii=False))
        return chunks
