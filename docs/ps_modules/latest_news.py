#!/usr/bin/env python3
"""
Latest News Module for Sphinx Documentation

This module provides functionality to dynamically generate a latest news carousel
for the Sphinx documentation site. It reads RST files from the latest_news directory,
extracts metadata, and generates a Bootstrap carousel with styled blog post cards.
"""

import os
import re
from datetime import datetime
from pathlib import Path


def extract_metadata(content):
    """Extract metadata from RST content."""
    metadata = {}
    lines = content.split("\n")

    for line in lines:
        if line.startswith(":"):
            if ":" in line[1:]:
                key, value = line[1:].split(":", 1)
                metadata[key.strip()] = value.strip()

    return metadata


def extract_excerpt(content, max_length=200):
    """Extract an excerpt from RST content, looking for a Description section."""
    lines = content.split("\n")
    content_lines = []

    # Look for Description section
    in_description = False
    description_found = False

    for line in lines:
        line = line.strip()

        # Check if this is a Description section header
        if line.lower() == "description" and not description_found:
            in_description = True
            description_found = True
            continue
        elif line == "-----------" and in_description:
            # Skip the underline after Description
            continue

        # If we're in description section, collect content until next section
        if in_description:
            if line.startswith("=") or line.startswith("-") or line.startswith("*"):
                # Found next section header, stop collecting
                break
            elif line:  # Non-empty line in description
                content_lines.append(line)
                # Stop collecting if we have enough content
                if len(" ".join(content_lines)) > max_length * 1.5:
                    break

    # If no Description section found, fall back to first paragraph
    if not description_found:
        skip_metadata = True
        title_found = False

        for line in lines:
            line = line.strip()

            if skip_metadata:
                if line.startswith(":"):
                    continue  # Skip metadata
                elif line and not line.startswith("=") and not title_found:
                    # First non-metadata line is the title
                    title_found = True
                    continue  # Skip the title
                elif line.startswith("="):
                    continue  # Skip title underlines
                elif line:  # Found first content line
                    skip_metadata = False
                    content_lines.append(line)
            else:
                if line:
                    content_lines.append(line)
                    # Stop collecting if we have enough content
                    if len(" ".join(content_lines)) > max_length * 1.5:
                        break

    # Join and clean up the content
    excerpt = " ".join(content_lines).strip()

    # Remove RST formatting
    excerpt = re.sub(r"\*\*(.*?)\*\*", r"\1", excerpt)  # **bold**
    excerpt = re.sub(r"\*(.*?)\*", r"\1", excerpt)  # *italic*
    excerpt = re.sub(r"`(.*?)`", r"\1", excerpt)  # `code`
    excerpt = re.sub(r":[\w-]+:`([^`]+)`", r"\1", excerpt)  # :role:`text`
    excerpt = re.sub(r"\n+", " ", excerpt)  # Multiple newlines
    excerpt = re.sub(r"\s+", " ", excerpt)  # Multiple spaces

    # Remove section headers
    excerpt = re.sub(r"\b\w+\s*[-=]{3,}\s*", "", excerpt)

    # Remove any remaining metadata
    excerpt = re.sub(r":\w+:\s*[^s]+", "", excerpt)

    # Truncate if too long
    if len(excerpt) > max_length:
        excerpt = excerpt[:max_length].rsplit(" ", 1)[0] + "..."

    return excerpt


def get_latest_news_posts(news_dir_path, max_posts=None, tag_filter=None):
    """Get the latest news posts from the specified directory."""
    news_dir = Path(news_dir_path)

    if not news_dir.exists():
        print(f"News directory {news_dir} does not exist")
        return []

    posts = []

    # Get all RST files in the news directory
    for rst_file in news_dir.glob("*.rst"):
        try:
            with open(rst_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract metadata
            metadata = extract_metadata(content)

            # Extract excerpt
            excerpt = extract_excerpt(content)

            # Get tags
            tags_str = metadata.get("tags", "")
            tags = (
                [tag.strip() for tag in tags_str.split(",") if tag.strip()]
                if tags_str
                else []
            )

            # Apply tag filter if specified
            if tag_filter and tag_filter != "all":
                if tag_filter not in tags:
                    continue

            # Create post dictionary
            post = {
                "filename": rst_file.stem,
                "title": metadata.get("title", rst_file.stem.replace("_", " ").title()),
                "date": metadata.get("date", ""),
                "excerpt": excerpt,
                "tags": tags,
                "image": metadata.get("image", ""),
                "content": content,
            }

            posts.append(post)

        except Exception as e:
            print(f"Error reading {rst_file}: {e}")
            continue

    # Sort by date (newest first)
    posts.sort(key=lambda x: x["date"], reverse=True)

    # Return only the requested number of posts
    if max_posts:
        return posts[:max_posts]
    return posts


def get_all_tags(news_dir_path):
    """Get all unique tags from all news posts."""
    news_dir = Path(news_dir_path)
    all_tags = set()

    if not news_dir.exists():
        return []

    for rst_file in news_dir.glob("*.rst"):
        try:
            with open(rst_file, "r", encoding="utf-8") as f:
                content = f.read()

            metadata = extract_metadata(content)
            tags_str = metadata.get("tags", "")
            if tags_str:
                tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
                all_tags.update(tags)

        except Exception as e:
            print(f"Error reading {rst_file}: {e}")
            continue

    # Sort tags alphabetically
    return sorted(list(all_tags))


def generate_tabbed_carousel_rst(news_dir_path):
    """Generate RST content for a tabbed carousel interface."""
    # Get all tags
    all_tags = get_all_tags(news_dir_path)

    # Generate the tabbed interface
    rst_content = """.. tab-set::
   :sync-group: news-filter

"""

    # Add "All" tab first
    all_posts = get_latest_news_posts(news_dir_path, max_posts=10)
    carousel_content = generate_carousel_rst(all_posts)
    rst_content += f"""   .. tab-item:: All
      :sync: all

{carousel_content}

"""

    # Add individual tag tabs
    for tag in all_tags:
        tag_posts = get_latest_news_posts(news_dir_path, tag_filter=tag, max_posts=10)
        if tag_posts:  # Only add tab if there are posts with this tag
            carousel_content = generate_carousel_rst(tag_posts)
            rst_content += f"""   .. tab-item:: {tag.title()}
      :sync: {tag}

{carousel_content}

"""

    return rst_content


def generate_carousel_rst(posts, include_header=False):
    """Generate RST content for the latest news carousel using sphinx-design card carousel."""
    if not posts:
        return ".. note::\n   No news posts available.\n\n"

    # Ensure we always show the latest posts (sorted by date, newest first)
    latest_posts = sorted(posts, key=lambda x: x["date"], reverse=True)

    # Generate RST with sphinx-design card carousel
    rst_content = ""

    if include_header:
        rst_content += """
:fas:`newspaper` Latest News
============================

"""

    rst_content += """
.. card-carousel:: 3

"""

    # Generate carousel cards
    for post in latest_posts:
        # Format date for display
        display_date = post["date"]
        if display_date:
            try:
                date_obj = datetime.strptime(display_date, "%Y-%m-%d")
                display_date = date_obj.strftime("%B %d, %Y")
            except:
                pass

        # Create a simple link based on filename
        read_more_link = f"latest_news/{post['filename']}"

        # Add card to carousel
        rst_content += f"""   .. card::
      :link: {read_more_link}
      :link-type: doc
      :shadow: none
      :width: 50%

      **{post['title']}**
      
      {post['excerpt']}
      
      :fas:`calendar-alt` {display_date}

"""

    return rst_content.rstrip()


def create_news_carousel(app):
    """Create the news carousel RST file during Sphinx build."""
    try:
        # Get the source directory
        src_dir = Path(app.srcdir)
        news_dir = src_dir / "latest_news"

    except Exception as e:
        print(f"Error creating news carousel: {e}")


def setup_latest_news(app):
    """Setup the latest news carousel for Sphinx."""
    app.connect("builder-inited", create_news_carousel)

