from app.rag.chunker import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []


def test_short_text_returns_single_chunk():
    chunks = chunk_text("Admins can create invoices.", chunk_size=1000)
    assert chunks == ["Admins can create invoices."]


def test_long_text_splits_on_sentence_boundaries():
    sentence = "The invoice must appear in the customer's ledger immediately. "
    text = sentence * 40
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 250  # allows for overlap slack


def test_chunks_have_overlap_continuity():
    sentence_a = "Admin creates an invoice."
    sentence_b = "The balance updates within one second."
    sentence_c = "An audit log entry is written for compliance."
    text = f"{sentence_a} {sentence_b} {sentence_c}"
    chunks = chunk_text(text, chunk_size=40, overlap=10)
    assert len(chunks) >= 2
