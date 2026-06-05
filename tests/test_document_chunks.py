from deepagent.multiagent.legal_assistant.task_execution.document_chunks import (
    all_required_filled,
    is_chunk_complete,
    map_fields_to_chunk_indices,
    split_markdown_into_chunks,
)


def test_split_markdown_respects_paragraphs():
    md = "A" * 1000 + "\n\n" + "B" * 1000 + "\n\n" + "C" * 1000
    chunks = split_markdown_into_chunks(md, max_chars=1500)
    assert len(chunks) >= 2
    assert all(len(c) <= 1600 for c in chunks)


def test_map_fields_by_anchor_position():
    md = "Phần đầu\n\n" + "x" * 500 + "\n\nPhần cuối có {{ten}}"
    schema = [
        {"id": "ten", "label": "Tên", "required": True, "anchor_text": "{{ten}}"},
        {"id": "other", "label": "Khác", "required": True, "anchor_text": ""},
    ]
    chunks = split_markdown_into_chunks(md, max_chars=400)
    mapping = map_fields_to_chunk_indices(schema, md, chunks)
    assert mapping["ten"] == len(chunks) - 1
    assert 0 <= mapping["other"] < len(chunks)


def test_chunk_complete_and_all_required():
    schema = [
        {"id": "a", "required": True},
        {"id": "b", "required": True},
    ]
    field_map = {"a": 0, "b": 1}
    filled = {"a": "ok"}
    assert not is_chunk_complete(schema, field_map, 0, filled)
    assert is_chunk_complete(schema, field_map, 0, {"a": "ok"})
    assert not all_required_filled(schema, {"a": "ok"})
    assert all_required_filled(schema, {"a": "ok", "b": "ok"})
