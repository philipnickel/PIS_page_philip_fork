from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import warnings
from textwrap import shorten

# -- minimal dependency: docutils only
from docutils import nodes
from docutils.core import publish_doctree


# ------------------------------ Models ----------------------------------------
@dataclass
class article:
    filename: str
    title: str
    date: datetime
    keywords: List[str]
    description: str

    @property
    def datef(self) -> str:
        return self.date.strftime("%d %b %Y")

    def summary(self, width: int = 140) -> str:
        placeholder = "..."
        return shorten(self.description, width=width, placeholder=placeholder)


def _meta_from_doctree(tree: nodes.document) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for m in tree.findall(nodes.meta):
        name = (m.get("name") or "").strip()
        value = (m.get("content") or "").strip()
        if name and value:
            meta[name.lower()] = value
    return meta


def _parse_article(path: Path) -> article:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # now publish the doctree
    tree = publish_doctree(text)

    meta = _meta_from_doctree(tree)

    title = meta.get("title")

    date_raw = meta.get("date", "")

    date = datetime.strptime(date_raw, "%d-%m-%Y")

    keywords_str = meta.get("keywords", "")
    keywords = [t.strip() for t in keywords_str.split(",") if t.strip()]

    p = tree.next_node(nodes.paragraph)
    description = p.astext().strip() if p else None

    return article(
        filename=path.stem,
        title=title,
        date=date,
        keywords=keywords,
        description=description,
    )


# ------------------------------ Collection ------------------------------------


def _all_keywords(dir_path: Path) -> List[str]:
    keywords_set = set()

    for rst_path in sorted(dir_path.glob("*.rst")):
        a = _parse_article(rst_path)

        for kw in a.keywords:
            keywords_set.add(kw)

    return sorted(keywords_set)


def _collect_articles(
    dir_path: Path,
    keyword_filter: Optional[str] = None,
) -> List[article]:
    results: List[article] = []

    for rst_path in sorted(dir_path.glob("*.rst")):
        try:
            a = _parse_article(rst_path)
        except Exception as e:
            warnings.warn(
                f"[Latest News] Skipping invalid or incomplete post: {rst_path}: {e}"
            )
            continue

        if keyword_filter:
            if keyword_filter in a.keywords:
                results.append(a)
        else:
            results.append(a)

    # show newest first
    results.sort(key=lambda x: x.date, reverse=True)
    return results


# ------------------------------ Rendering -------------------------------------
def _indent(text: str, n: int) -> str:
    pad = " " * n
    return "\n".join((pad + line) if line.strip() else "" for line in text.splitlines())


def _render_carousel(posts: List[article]) -> str:
    if not posts:
        return ".. note::\n   No news posts available.\n\n"

    # sphinx-design card carousel (3 columns)
    out = [".. card-carousel:: 3", ""]
    for p in posts:
        # link to the doc by name (assumes each file is a doc in latest_news/)
        link = f"latest_news/{p.filename}"
        date_disp = p.date

        card = f"""   .. card::
      :link: {link}
      :link-type: doc
      :shadow: none

      :fas:`calendar-alt` {date_disp.strftime('%d %b %Y')}

      **{p.title}**

      {p.description}

"""
        out.append(card.rstrip() + "\n")
    return "\n".join(out).rstrip() + "\n"


def _render_tabset(dir_path: Path) -> str:
    all_posts = _collect_articles(dir_path)
    all_carousel = _render_carousel(all_posts)

    rst = ".. tab-set::\n\n"
    rst += (
        "   .. tab-item:: All\n" "      :selected:\n\n" f"{_indent(all_carousel, 6)}\n"
    )

    for keyword in _all_keywords(dir_path):
        keyword_posts = _collect_articles(dir_path, keyword)
        carousel = _render_carousel(keyword_posts)
        rst += f"   .. tab-item:: {keyword.title()}\n\n" f"{_indent(carousel, 6)}\n"

    return rst


# ------------------------------ Sphinx hook -----------------------------------


def create_news_carousel(app):
    try:
        src_dir = Path(app.srcdir)

        news_dir = src_dir / "latest_news"
        out_dir = src_dir / "_rst_includes"

        out_file = out_dir / "latest_news.rst"

        content = _render_tabset(news_dir)

        with open(out_file, "w") as f:
            f.write(content)

    except Exception as e:
        warnings.warn(f"[Latest News] Failed to create news carousel: {e}")
