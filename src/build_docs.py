"""Small, escaped documentation renderer for this repository's Markdown subset."""

from html import escape
import re


def inline(text):
    text = escape(text)

    def link(m):
        href = m[2]
        if not (href.startswith(("https://", "http://")) or re.fullmatch(r"[A-Za-z0-9_.-]+", href)):
            return m[1]
        if href.endswith(".md"):
            href = href[:-3] + ".html"
        return f'<a href="{href}">{m[1]}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


def render(source):
    out = []
    code = []
    in_code = False
    table = False
    listing = False
    for line in source.splitlines() + [""]:
        if line.startswith("```"):
            if in_code:
                out.append("<pre><code>" + escape("\n".join(code)) + "</code></pre>")
                code = []
            in_code = not in_code
            continue
        if in_code:
            code.append(line)
            continue
        if table and not line.startswith("|"):
            out.append("</tbody></table></div>")
            table = False
        if listing and not line.startswith("- "):
            out.append("</ul>")
            listing = False
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.fullmatch(r"[-: ]+", c) for c in cells):
                continue
            tag = "td" if table else "th"
            if not table:
                out.append('<div class="table-scroll"><table>')
            out.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>")
            if not table:
                out.append("<tbody>")
                table = True
        elif line.startswith("#"):
            n = len(line) - len(line.lstrip("#"))
            out.append(f"<h{min(n,6)}>{inline(line[n:].strip())}</h{min(n,6)}>")
        elif line.startswith("- "):
            if not listing:
                out.append("<ul>")
                listing = True
            out.append("<li>" + inline(line[2:]) + "</li>")
        elif line.strip():
            out.append("<p>" + inline(line) + "</p>")
    return "\n".join(out)


def build(root, site):
    style = """body{margin:0;background:#f4f5f0;color:#172620;font:16px/1.7 system-ui,sans-serif}nav{background:#13281d;padding:20px 6%;color:white}nav a{color:#c6f36b}article{max-width:1000px;margin:35px auto;padding:30px;background:white;border-radius:16px}h1{font-size:36px;line-height:1.2;letter-spacing:-1px}h2{margin-top:32px}h3{margin-top:24px}a{color:#256345}p,li{overflow-wrap:anywhere}pre{overflow:auto;padding:18px;background:#edf2e7;border-radius:8px;font-size:13px}code{font-size:.9em}.table-scroll{overflow:auto}table{border-collapse:collapse;font-size:13px;width:100%}td,th{padding:13px;text-align:left;border-bottom:1px solid #dae3d4;min-width:150px}th{background:#eaf0e3}@media(max-width:700px){article{margin:15px;padding:20px}h1{font-size:27px}}"""
    for path in (root / "docs").glob("*.md"):
        title = re.sub(r"[–—-]", " ", path.read_text(encoding="utf8").splitlines()[0].lstrip("# "))
        html = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} | Footlyzer</title><meta name="description" content="{escape(title)}. Football research methods and portfolio evidence from Footlyzer."><link rel="canonical" href="https://sabin901.github.io/Football-Analyzer-/docs/{path.stem}.html"><style>{style}</style></head><body><nav><a href="../index.html#view=portfolio">← Footlyzer · Analyst portfolio</a></nav><article>{render(path.read_text(encoding="utf8"))}</article></body></html>'
        (site / "docs" / path.with_suffix(".html").name).write_text(html, encoding="utf8")
