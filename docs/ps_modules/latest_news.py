from __future__ import annotations

import sys
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

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


def _meta_from_doctree(tree: nodes.document) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for m in tree.findall(nodes.meta):
        name = (m.get("name") or "").strip()
        value = (m.get("content") or "").strip()
        if name and value:
            meta[name.lower()] = value
    return meta


def _first_paragraph(tree: nodes.document) -> Optional[str]:
    p = tree.next_node(nodes.paragraph)
    return p.astext().strip() if p else None


def _parse_post(app: object, path: Path) -> Optional[article]:

    env = app.env
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # get the directory of the path
    dir = os.path.dirname(path)
    # change the working directory
    cwd = os.getcwd()
    os.chdir(dir)
    # now publish the doctree
    tree = publish_doctree(text, settings_overrides={"env": env})
    # and change back the working directory
    os.chdir(cwd)

    meta = _meta_from_doctree(tree)

    title = meta.get("title")

    date_raw = meta.get("date", "")
    if not date_raw:
        return None
    date = datetime.strptime(date_raw, "%d-%m-%Y")

    keywords_str = meta.get("keywords", "")
    keywords = [t.strip() for t in keywords_str.split(",") if t.strip()]

    description = _first_paragraph(tree)

    return article(
        filename=path.stem,
        title=title,
        date=date,
        keywords=keywords,
        description=description,
    )


# ------------------------------ Collection ------------------------------------
def _collect_posts(
    app: object,
    dir_path: Path,
    tag_filter: Optional[str] = None,
    max_posts: Optional[int] = None,
) -> List[article]:
    if not dir_path.exists():
        print(f"[warn] directory not found: {dir_path}", file=sys.stderr)
        return []

    tag_filter_norm = (tag_filter or "").strip().lower()
    posts: List[article] = []

    for p in sorted(dir_path.glob("*.rst")):
        # skip non-posts or templates
        # if p.name.startswith("template"):
        post = _parse_post(app, p)
        if not post:
            continue

        if tag_filter_norm and tag_filter_norm != "all":
            if tag_filter_norm not in [t.lower() for t in post.keywords]:
                continue

        posts.append(post)

    return posts[:max_posts] if max_posts else posts


def _all_keywords(app: object, dir_path: Path) -> List[str]:
    tags = set()
    for p in dir_path.glob("*.rst"):
        post = _parse_post(app, p)
        if post:
            tags.update(post.keywords)
    return sorted(tags, key=str.lower)


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

      **{p.title}**
      
      {p.description}
      
      :fas:`calendar-alt` {date_disp}
"""
        out.append(card.rstrip() + "\n")
    return "\n".join(out).rstrip() + "\n"


def _render_tabset(app: object, dir_path: Path, max_posts: int = 10) -> str:
    # "All" tab
    all_posts = _collect_posts(app, dir_path, max_posts=max_posts)
    all_carousel = _render_carousel(all_posts)

    rst = """.. tab-set::
   :sync-group: news-filter

"""
    rst += f"""   .. tab-item:: All
      :sync: all

{_indent(all_carousel, 6)}

"""

    # Per-tag tabs
    for keyword in _all_keywords(app, dir_path):
        keyword_posts = _collect_posts(
            app, dir_path, tag_filter=keyword, max_posts=max_posts
        )
        if not keyword_posts:
            continue
        carousel = _render_carousel(keyword_posts)
        rst += f"""   .. tab-item:: {keyword.title()}
      :sync: {keyword}

{_indent(carousel, 6)}

"""
    return rst


# ------------------------------ Sphinx hook -----------------------------------
def create_news_carousel(app):
    try:
        src_dir = Path(app.srcdir)
        news_dir = src_dir / "latest_news"
        out_file = news_dir / "generated_latest_news_carousel.rst"
        out_file.write_text(
            _render_tabset(app, news_dir, max_posts=10), encoding="utf-8"
        )
    except Exception as e:
        print(f"[error] create_news_carousel: {e}", file=sys.stderr)
