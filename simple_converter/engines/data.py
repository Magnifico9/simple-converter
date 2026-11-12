"""Tabular / text formats: csv, xlsx, json, markdown, html."""
import json
from pathlib import Path

from ..util import ConvertError, out_path, stem_of


def read_csv(src: Path):
    import pandas as pd
    last = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(src, sep=None, engine="python", encoding=enc)
        except UnicodeDecodeError as e:
            last = e
        except Exception as e:
            raise ConvertError(f"Can't read CSV: {e}")
    raise ConvertError(f"Can't read CSV: {last}")


def read_json(src: Path):
    import pandas as pd
    try:
        data = json.loads(src.read_text(encoding="utf-8-sig"))
    except Exception as e:
        raise ConvertError(f"Invalid JSON: {e}")
    if isinstance(data, dict):
        # {"rows": [...]} or {"a": [..], "b": [..]} or a single object
        lists = [v for v in data.values() if isinstance(v, list) and v and isinstance(v[0], dict)]
        if len(lists) == 1:
            data = lists[0]
        elif all(isinstance(v, list) for v in data.values()):
            return pd.DataFrame(data)
        else:
            data = [data]
    if not isinstance(data, list):
        raise ConvertError("JSON must be a list of objects to become a table")
    if data and not isinstance(data[0], dict):
        return pd.DataFrame({"value": data})
    return pd.json_normalize(data)


def read_sheets(src: Path) -> dict:
    import pandas as pd
    try:
        return pd.read_excel(src, sheet_name=None)
    except Exception as e:
        raise ConvertError(f"Can't read spreadsheet: {e}")


def _write(df, dst: Path, to: str):
    if to == "csv":
        df.to_csv(dst, index=False, encoding="utf-8-sig")
    elif to == "xlsx":
        df.to_excel(dst, index=False)
    elif to == "json":
        dst.write_text(df.to_json(orient="records", force_ascii=False, indent=2, date_format="iso"),
                       encoding="utf-8")
    else:
        raise ConvertError(f"Can't write {to}")


def convert(src: Path, to: str, outdir=None) -> list[Path]:
    ext = src.suffix.lower().lstrip(".")
    if ext == "csv":
        frames = {"": read_csv(src)}
    elif ext == "json":
        frames = {"": read_json(src)}
    else:
        frames = read_sheets(src)
    if to == "xlsx" and len(frames) > 1:
        import pandas as pd
        dst = out_path(src, outdir, "xlsx")
        with pd.ExcelWriter(dst) as w:
            for name, df in frames.items():
                df.to_excel(w, sheet_name=name[:31] or "Sheet1", index=False)
        return [dst]
    if to == "json" and len(frames) > 1:
        dst = out_path(src, outdir, "json")
        obj = {n: json.loads(df.to_json(orient="records", force_ascii=False, date_format="iso"))
               for n, df in frames.items()}
        dst.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        return [dst]
    outs = []
    for name, df in frames.items():
        suffix = f" - {name}" if len(frames) > 1 else ""
        dst = out_path(src, outdir, to, suffix)
        _write(df, dst, to)
        outs.append(dst)
    return outs


CSS = """body{font-family:Segoe UI,Arial,sans-serif;max-width:860px;margin:2em auto;padding:0 1em;
line-height:1.55;color:#222}pre,code{font-family:Consolas,monospace;background:#f4f4f4}
pre{padding:.8em;overflow:auto}table{border-collapse:collapse}td,th{border:1px solid #ccc;
padding:.3em .6em}img{max-width:100%}blockquote{border-left:4px solid #ddd;margin-left:0;
padding-left:1em;color:#555}"""


def md_to_html(src: Path) -> str:
    import markdown
    text = src.read_text(encoding="utf-8-sig", errors="replace")
    body = markdown.markdown(text, extensions=["extra", "sane_lists", "toc", "nl2br"])
    title = stem_of(src)
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>"
            f"<style>{CSS}</style></head><body>{body}</body></html>")


def md_convert(src: Path, to: str, outdir=None) -> list[Path]:
    html = md_to_html(src)
    if to == "html":
        dst = out_path(src, outdir, "html")
        dst.write_text(html, encoding="utf-8")
        return [dst]
    from . import office
    return office.from_html_text(html, src, to, outdir)


def html_to_md(src: Path, outdir=None) -> list[Path]:
    """Light HTML -> Markdown (headings, lists, links, emphasis, code)."""
    import re
    from html import unescape
    h = src.read_text(encoding="utf-8-sig", errors="replace")
    h = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", "", h)
    for n in range(6, 0, -1):
        h = re.sub(rf"(?is)<h{n}[^>]*>(.*?)</h{n}>", lambda m: "\n" + "#" * n + " " + m.group(1).strip() + "\n", h)
    h = re.sub(r"(?is)<pre[^>]*>(.*?)</pre>", lambda m: "\n```\n" + m.group(1) + "\n```\n", h)
    h = re.sub(r"(?is)<(b|strong)>(.*?)</\1>", r"**\2**", h)
    h = re.sub(r"(?is)<(i|em)>(.*?)</\1>", r"*\2*", h)
    h = re.sub(r"(?is)<code>(.*?)</code>", r"`\1`", h)
    h = re.sub(r'(?is)<a [^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", h)
    h = re.sub(r'(?is)<img [^>]*src="([^"]*)"[^>]*>', r"![](\1)", h)
    h = re.sub(r"(?is)<li[^>]*>", "\n- ", h)
    h = re.sub(r"(?is)<br\s*/?>", "  \n", h)
    h = re.sub(r"(?is)</(p|div|ul|ol|table|tr|blockquote)>", "\n\n", h)
    h = re.sub(r"(?is)<[^>]+>", "", h)
    h = unescape(h)
    h = re.sub(r"\n{3,}", "\n\n", h).strip() + "\n"
    dst = out_path(src, outdir, "md")
    dst.write_text(h, encoding="utf-8")
    return [dst]
