# -*- coding: utf-8 -*-
"""md -> HTML (水墨风, 左侧目录) 转换脚本"""
import sys, re
import markdown

CSS = open(r"D:\Desktop\WL项目\md2html_style.css", encoding="utf-8").read()

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__TITLE__</title>
<style>__CSS__</style>
</head>
<body>
<div class="layout">
  <nav class="toc">
    <div class="brand">多 Agent 文旅系统</div>
    <div class="brand-sub">文档导航</div>
    <h3>目录</h3>
    __TOC__
  </nav>
  <main>
    <div class="hero">
      <h1>__TITLE__</h1>
      <p>基于 backend/app 实际代码核实整理</p>
    </div>
    __BODY__
  </main>
</div>
<script>
const links=[...document.querySelectorAll('.toc a')];
const heads=[...document.querySelectorAll('main h2,h3')].filter(h=>h.id);
window.addEventListener('scroll',()=>{
  let cur=null;
  for(const h of heads){ if(h.getBoundingClientRect().top<=90) cur=h.id; }
  links.forEach(a=>a.classList.toggle('active', a.getAttribute('href')==='#'+(cur||'')));
});
</script>
</body>
</html>"""


def convert(path):
    text = open(path, encoding="utf-8").read()
    m0 = re.search(r"^#\s+(.+)$", text, re.M)
    title = m0.group(1).strip() if m0 else "文档"
    body_src = re.sub(r"^#\s+.+$", "", text, count=1, flags=re.M)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc"])
    body = md.convert(body_src)
    toc = getattr(md, "toc", "") or ""
    html = (TEMPLATE
            .replace("__TITLE__", title)
            .replace("__CSS__", CSS)
            .replace("__TOC__", toc)
            .replace("__BODY__", body))
    out = path.rsplit(".", 1)[0] + ".html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("OK", out, len(html))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        convert(p)
