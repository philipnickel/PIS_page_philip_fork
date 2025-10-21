#!/usr/bin/env python3
"""
Latest News Module for Sphinx Documentation (LangChain loader version)

Uses langchain_community.document_loaders.UnstructuredRSTLoader to load .rst files.
Preserves your metadata/excerpt extraction and carousel generation.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from langchain_community.document_loaders import UnstructuredRSTLoader


def extract_metadata(content: str) -> Dict[str, str]:
    """Extract metadata from RST content."""
    metadata = {}
    lines = content.split("\n")

    for line in lines:
        if line.startswith(":"):
            if ":" in line[1:]:
                key, value = line[1:].split(":", 1)
                metadata[key.strip()] = value.strip()
    return metadata


def extract_excerpt(content: str, max_length: int = 200) -> str:
    """Extract an excerpt from RST content, preferring a 'Description' section."""
    lines = content.split("\n")
    content_lines: List[str] = []

    # Look for Description section
    in_description = False
    description_found = False

    for line in lines:
        line = line.strip()

        if line.lower() == "description" and not description_found:
            in_description = True
            description_found = True
            continue
        elif line == "-----------" and in_description:
            continue

        if in_description:
            if line.startswith("=") or line.startswith("-") or line.startswith("*"):
                break
            elif line:
                content_lines.append(line)
                if len(" ".join(content_lines)) > max_length * 1.5:
                    break

    if not description_found:
        skip_metadata = True
        title_found = False

        for line in lines:
            line = line.strip()

            if skip_metadata:
                if line.startswith(":"):
                    continue
                elif line and not line.startswith("=") and not title_found:
                    title_found = True
                    continue
                elif line.startswith("="):
                    continue
                elif line:
                    skip_metadata = False
                    content_lines.append(line)
            else:
                if line:
                    content_lines.append(line)
                    if len(" ".join(content_lines)) > max_length * 1.5:
                        break

    excerpt = " ".join(content_lines).strip()

    # Strip basic RST formatting
    excerpt = re.sub(r"\*\*(.*?)\*\*", r"\1", excerpt)  # **bold**
    excerpt = re.sub(r"\*(.*?)\*", r"\1", excerpt)  # *italic*
    excerpt = re.sub(r"`(.*?)`", r"\1", excerpt)  # `code`
    excerpt = re.sub(r":[\w-]+:`([^`]+)`", r"\1", excerpt)  # :role:`text`
    excerpt = re.sub(r"\n+", " ", excerpt)
    excerpt = re.sub(r"\s+", " ", excerpt)

    # Remove section headers and metadata
    excerpt = re.sub(r"\b\w+\s*[-=]{3,}\s*", "", excerpt)
    excerpt = re.sub(r":\w+:\s*[^s]+", "", excerpt)

    if len(excerpt) > max_length:
        excerpt = excerpt[:max_length].rsplit(" ", 1)[0] + "..."

    return excerpt


def _parse_date(s: str) -> Optional[datetime]:
    """Try a few common date formats; return None if unparseable."""
    if not s:
        return None
    fmts = ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y")
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _load_rst_with_langchain(rst_path: Path) -> Tuple[str, Dict[str, Any]]:
    """
    Load a single RST file via UnstructuredRSTLoader in 'single' mode.
    Returns (content, loader_metadata).
    """
    loader = UnstructuredRSTLoader(str(rst_path), mode="single")

    docs = loader.load()
    if not docs:
        return "", {}
    doc = docs[0]
    content = doc.page_content or ""
    lc_meta = dict(doc.metadata or {})
    return content, lc_meta


def get_latest_news_posts(
    news_dir_path: str,
    max_posts: Optional[int] = None,
    tag_filter: Optional[str] = None,
):
    """Get the latest news posts from the specified directory using LangChain loader."""
    news_dir = Path(news_dir_path)

    if not news_dir.exists():
        print(f"News directory {news_dir} does not exist")
        return []

    posts = []

    for rst_file in news_dir.glob("*.rst"):
        try:
            content, lc_meta = _load_rst_with_langchain(rst_file)
            if not content.strip():
                continue

            # Merge: prefer explicit in-file :key: value metadata; fall back to loader metadata
            file_meta = extract_metadata(content)
            merged_meta = {**lc_meta, **file_meta}

            excerpt = extract_excerpt(content)

            # Tags
            tags_str = merged_meta.get("tags", "") or merged_meta.get("Keywords", "")
            tags = [t.strip() for t in tags_str.split(",")] if tags_str else []

            # Optional filter
            if tag_filter and tag_filter != "all":
                if tag_filter not in tags:
                    continue

            # Title: prefer :title: then loader title, else filename prettified
            title = (
                merged_meta.get("title")
                or merged_meta.get("Title")
                or rst_file.stem.replace("_", " ").title()
            )

            date_raw = merged_meta.get("date") or merged_meta.get("Date") or ""
            date_obj = _parse_date(date_raw)

            post = {
                "filename": rst_file.stem,
                "title": title,
                "date": date_raw,  # keep original string for display
                "date_obj": date_obj,  # parsed for sorting
                "excerpt": excerpt,
                "tags": tags,
                "image": merged_meta.get("image", "") or merged_meta.get("Image", ""),
                "content": content,
            }
            posts.append(post)

        except Exception as e:
            print(f"Error reading {rst_file}: {e}")
            continue

    # Sort by parsed date desc, fallback to filename mtime if missing
    def _sort_key(p):
        if p.get("date_obj"):
            return (p["date_obj"], p["filename"])
        # fallback: file mtime (newest first)
        try:
            mtime = (news_dir / f"{p['filename']}.rst").stat().st_mtime
        except Exception:
            mtime = 0.0
        return (datetime.fromtimestamp(mtime), p["filename"])

    posts.sort(key=_sort_key, reverse=True)

    return posts[:max_posts] if max_posts else posts


def get_all_tags(news_dir_path: str):
    """Get all unique tags using the LangChain loader."""
    news_dir = Path(news_dir_path)
    all_tags = set()

    if not news_dir.exists():
        return []

    for rst_file in news_dir.glob("*.rst"):
        try:
            content, lc_meta = _load_rst_with_langchain(rst_file)
            if not content.strip():
                continue

            file_meta = extract_metadata(content)
            merged_meta = {**lc_meta, **file_meta}

            tags_str = merged_meta.get("tags", "") or merged_meta.get("Keywords", "")
            if tags_str:
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                all_tags.update(tags)

        except Exception as e:
            print(f"Error reading {rst_file}: {e}")
            continue

    return sorted(all_tags)


def _indent_content(content: str, level: int) -> str:
    return "\n".join(
        (" " * level + line if line.strip() else "") for line in content.splitlines()
    )


def generate_tabbed_carousel_rst(news_dir_path: str) -> str:
    all_tags = get_all_tags(news_dir_path)

    rst_content = """.. tab-set::
   :sync-group: news-filter

"""

    all_posts = get_latest_news_posts(news_dir_path, max_posts=10)
    carousel_content = generate_carousel_rst(all_posts)
    rst_content += f"""   .. tab-item:: All
      :sync: all

{_indent_content(carousel_content, 6)}

"""

    for tag in all_tags:
        tag_posts = get_latest_news_posts(news_dir_path, tag_filter=tag, max_posts=10)
        if tag_posts:
            carousel_content = generate_carousel_rst(tag_posts)
            rst_content += f"""   .. tab-item:: {tag.title()}
      :sync: {tag}

{_indent_content(carousel_content, 6)}

"""

    return rst_content


def generate_carousel_rst(posts, include_header: bool = False) -> str:
    if not posts:
        return ".. note::\n   No news posts available.\n\n"

    latest_posts = sorted(
        posts,
        key=lambda x: (x.get("date_obj") or datetime.min, x["title"]),
        reverse=True,
    )

    rst_content = ""
    if include_header:
        rst_content += """
:fas:`newspaper` Latest News
============================

"""

    rst_content += """.. card-carousel:: 3

"""

    for post in latest_posts:
        print(f"latest posts:{latest_posts} ")

        display_date = post["date"]
        if display_date:
            try:
                date_obj = _parse_date(display_date)
                if date_obj:
                    display_date = date_obj.strftime("%B %d, %Y")
            except Exception:
                pass

        read_more_link = f"latest_news/{post['filename']}"

        rst_content += f"""   .. card::
      :link: {read_more_link}
      :link-type: doc

      **{post['title']}**
      
      {post['excerpt']}
      
      :fas:`calendar-alt` {display_date}

"""
    return rst_content.rstrip()


def create_news_carousel(app):
    try:
        src_dir = Path(app.srcdir)
        news_dir = src_dir / "latest_news"
        output_file = news_dir / "generated_latest_news_carousel.rst"
        generated_content = generate_tabbed_carousel_rst(str(news_dir))
        output_file.write_text(generated_content, encoding="utf-8")
    except Exception as e:
        print(f"Error creating news carousel: {e}")


def setup_latest_news(app):
    app.connect("builder-inited", create_news_carousel)
    pass
