"""文档摄取（document_ingest）单测：切块器 / HTML 提取 / 格式分发 / URL 抓取，全部离线。"""
import pytest

from app.services import document_ingest


# ---------- chunk_text ----------

def test_chunk_short_text_single_chunk():
    text = "拙政园位于苏州市姑苏区东北街178号，是江南古典园林的代表作品。"
    chunks = document_ingest.chunk_text(text, size=400, overlap=80)
    assert chunks == [text.strip()]


def test_chunk_empty_returns_empty():
    assert document_ingest.chunk_text("   \n  ") == []


def test_chunk_invalid_overlap_raises():
    with pytest.raises(ValueError, match="overlap"):
        document_ingest.chunk_text("内容", size=100, overlap=100)


def test_chunk_all_within_size_and_overlap_continuous():
    # 单个超长段落：滑动窗口硬切，窗口间应带 overlap，且所有块 ≤ size
    text = "苏州园林甲天下。" * 200  # 1200 字无换行
    chunks = document_ingest.chunk_text(text, size=400, overlap=80)
    assert len(chunks) >= 3
    assert all(len(c) <= 400 for c in chunks)
    for prev, nxt in zip(chunks, chunks[1:]):
        tail = prev[-80:]
        assert nxt.startswith(tail), "相邻块应以上一块尾部 overlap 衔接"


def test_chunk_paragraph_integrity():
    # 短段落应整块聚合，不被切碎；空白行分隔
    paras = [f"第{i}段：" + "园林知识" * 10 for i in range(8)]  # 每段约 50 字
    chunks = document_ingest.chunk_text("\n\n".join(paras), size=400, overlap=80)
    joined = "\n".join(chunks)
    for para in paras:
        assert para in joined, "段落必须整块出现"


def test_chunk_tiny_tail_merged():
    text = "字" * 395 + "\n" + "尾" * 10  # 395 + 10：按 400 切会留下 10 字尾巴
    chunks = document_ingest.chunk_text(text, size=400, overlap=80)
    assert len(chunks) == 1 or all(len(c) >= document_ingest.MIN_CHUNK_CHARS for c in chunks)
    assert all("尾" in c or "字" in c for c in chunks)
    joined = "".join(chunks)
    assert joined.count("尾") == 10


# ---------- parse_html ----------

def test_parse_html_strips_script_and_blocks():
    html = """
    <html><head><title>拙政园参观须知</title><style>.x{color:red}</style></head>
    <body>
    <script>var tracking = 1;</script>
    <h1>开放时间</h1><p>旺季 7:30-17:30</p>
    <p>淡季 7:30-17:00</p>
    <div>禁止携带宠物入园</div>
    </body></html>
    """
    title, text = document_ingest.parse_html(html)
    assert title == "拙政园参观须知"
    assert "tracking" not in text and "color:red" not in text
    assert "旺季 7:30-17:30" in text
    assert "禁止携带宠物入园" in text
    assert "\n" in text  # 块级标签已转换为行


def test_parse_html_malformed_no_raise():
    title, text = document_ingest.parse_html("<p>未闭合的段落 <b>加粗")
    assert "未闭合的段落" in text


# ---------- extract_document 分发 ----------

def test_extract_txt_and_md(tmp_path):
    txt = tmp_path / "notice.txt"
    txt.write_text("景区公告：明日闭园。", encoding="utf-8")
    title, text = document_ingest.extract_document(txt)
    assert title == "notice" and "明日闭园" in text

    md = tmp_path / "guide.md"
    md.write_text("# 游览攻略\n\n带娃建议上午入园。", encoding="utf-8")
    title, text = document_ingest.extract_document(md)
    assert "游览攻略" in text


def test_extract_gbk_txt(tmp_path):
    txt = tmp_path / "gbk.txt"
    txt.write_bytes("景区公告：临时闭园。".encode("gbk"))
    _, text = document_ingest.extract_document(txt)
    assert "临时闭园" in text


def test_extract_html_file_strips_markup(tmp_path):
    page = tmp_path / "page.html"
    page.write_text("<html><head><title>T</title></head><body><p>正文内容</p></body></html>", encoding="utf-8")
    title, text = document_ingest.extract_document(page)
    assert title == "T" and text == "正文内容"


def test_extract_unsupported_type_raises(tmp_path):
    file = tmp_path / "pic.png"
    file.write_bytes(b"\x89PNG")
    with pytest.raises(ValueError, match="不支持"):
        document_ingest.extract_document(file)


def test_extract_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        document_ingest.extract_document(tmp_path / "nope.pdf")


def test_extract_docx_real(tmp_path):
    docx = pytest.importorskip("docx")
    path = tmp_path / "manual.docx"
    document = docx.Document()
    document.add_heading("参观须知", level=1)
    document.add_paragraph("每周一闭馆（法定节假日除外）。")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "旺季门票"
    table.rows[0].cells[1].text = "80元"
    document.save(str(path))
    title, text = document_ingest.extract_document(path)
    assert title == "manual"
    assert "每周一闭馆" in text
    assert "旺季门票；80元" in text  # 表格行拼接


def test_extract_pdf_real(tmp_path):
    pytest.importorskip("pypdf")
    # pypdf 只能写空白页（无文本写入能力），此处验证 PDF 链路不抛错且返回标题回退
    from pypdf import PdfWriter
    path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with open(path, "wb") as f:
        writer.write(f)
    title, text = document_ingest.extract_document(path)
    assert title == "blank"  # 无元数据标题时回退文件名
    assert isinstance(text, str)


# ---------- fetch_document ----------

def test_fetch_document_uses_utf8_and_title(monkeypatch):
    html = "<html><head><title>门票政策</title></head><body><p>成人票80元</p></body></html>".encode("utf-8")
    monkeypatch.setattr(document_ingest, "_fetch_bytes", lambda url, timeout=30.0: html)
    title, text = document_ingest.fetch_document("https://example.gov.cn/ticket")
    assert title == "门票政策" and "成人票80元" in text


def test_fetch_document_gbk_fallback(monkeypatch):
    html = "<html><head><title>公告</title></head><body><p>临时闭园</p></body></html>".encode("gb18030")
    monkeypatch.setattr(document_ingest, "_fetch_bytes", lambda url, timeout=30.0: html)
    title, text = document_ingest.fetch_document("https://example.gov.cn/notice")
    assert title == "公告" and "临时闭园" in text


def test_fetch_document_title_fallback_to_domain(monkeypatch):
    html = b"<html><body><p>no title</p></body></html>"
    monkeypatch.setattr(document_ingest, "_fetch_bytes", lambda url, timeout=30.0: html)
    title, _ = document_ingest.fetch_document("https://www.szzzy.cn/visit")
    assert title == "www.szzzy.cn"
