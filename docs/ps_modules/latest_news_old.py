"""
Latest News Carousel Module

This module automatically loads blog posts from the latest_news directory
and generates HTML for the carousel display.
"""

import os
from pathlib import Path
import re
from datetime import datetime
from docutils.core import publish_parts


def parse_rst_metadata(content):
    """Parse metadata from RST file content."""
    metadata = {}
    lines = content.split('\n')

    # Look for metadata in the first few lines
    for i, line in enumerate(lines[:10]):  # Check first 10 lines
        if line.startswith(':date:'):
            metadata['date'] = line.replace(':date:', '').strip()
        elif line.startswith(':author:'):
            metadata['author'] = line.replace(':author:', '').strip()
        elif line.startswith(':image:'):
            metadata['image'] = line.replace(':image:', '').strip()
        elif line.strip() and not line.startswith(':') and not line.startswith('='):
            # First non-metadata line is likely the title
            if 'title' not in metadata:
                metadata['title'] = line.strip()

    return metadata


def extract_excerpt(content, max_length=200):
    """Extract an excerpt from RST content, prioritizing the first substantial paragraph."""
    lines = content.split('\n')
    content_lines = []
    
    # Skip metadata and title, then collect content
    skip_metadata = True
    title_found = False
    
    for line in lines:
        line = line.strip()
        
        if skip_metadata:
            if line.startswith(':'):
                continue  # Skip metadata
            elif line and not line.startswith('=') and not title_found:
                # First non-metadata line is the title
                title_found = True
                continue  # Skip the title
            elif line.startswith('='):
                continue  # Skip title underlines
            elif line:  # Found first content line
                skip_metadata = False
                content_lines.append(line)
        else:
            if line:
                content_lines.append(line)
                # Stop collecting if we have enough content
                if len(' '.join(content_lines)) > max_length * 1.5:
                    break
    
    # Join and clean up the content
    excerpt = ' '.join(content_lines).strip()
    
    # Remove RST formatting
    excerpt = re.sub(r'\*\*(.*?)\*\*', r'\1', excerpt)  # **bold**
    excerpt = re.sub(r'\*(.*?)\*', r'\1', excerpt)      # *italic*
    excerpt = re.sub(r'`(.*?)`', r'\1', excerpt)        # `code`
    excerpt = re.sub(r':[\w-]+:`([^`]+)`', r'\1', excerpt)  # :role:`text`
    excerpt = re.sub(r'\n+', ' ', excerpt)               # Multiple newlines
    excerpt = re.sub(r'\s+', ' ', excerpt)               # Multiple spaces
    
    # Remove section headers (words followed by many dashes/equals)
    excerpt = re.sub(r'\b\w+\s*[-=]{3,}\s*', '', excerpt)
    
    # Remove any remaining metadata patterns
    excerpt = re.sub(r':\w+:\s*[^\s]+', '', excerpt)
    
    # Truncate if too long
    if len(excerpt) > max_length:
        excerpt = excerpt[:max_length].rsplit(' ', 1)[0] + '...'
    
    return excerpt


def get_latest_news_posts(news_dir_path, max_posts=5):
    """Load and parse news posts from the latest_news directory."""
    news_dir = Path(news_dir_path)

    if not news_dir.exists():
        print(f"Warning: latest_news directory not found at {news_dir}")
        return []

    posts = []

    # Find all RST files in the directory
    for rst_file in news_dir.glob('*.rst'):
        try:
            with open(rst_file, 'r', encoding='utf-8') as f:
                content = f.read()

            metadata = parse_rst_metadata(content)
            excerpt = extract_excerpt(content)

            # Create post data
            post = {
                'title': metadata.get('title', rst_file.stem.replace('_', ' ').title()),
                'author': metadata.get('author', 'DTU Python Support'),
                'date': metadata.get('date', ''),
                'excerpt': excerpt,
                'filename': rst_file.stem,
                'file_path': str(rst_file),
                'image': metadata.get('image', '')
            }

            posts.append(post)

        except Exception as e:
            print(f"Error processing {rst_file}: {e}")
            continue

    # Sort by date (newest first) if dates are available
    def sort_key(post):
        date_str = post.get('date', '')
        if date_str:
            try:
                # Try to parse the date
                return datetime.strptime(date_str, '%Y-%m-%d')
            except:
                pass
        return datetime.min

    posts.sort(key=sort_key, reverse=True)

    # Return only the requested number of posts
    return posts[:max_posts]


def generate_carousel_rst(posts):
    """Generate RST content for the latest news carousel using Bootstrap carousel with styled cards."""
    if not posts:
        return '.. note::\n   No news posts available.\n\n'

    # Ensure we always show the latest 3 posts (sorted by date, newest first)
    latest_posts = sorted(posts, key=lambda x: x['date'], reverse=True)[:3]

    # Generate RST using native Sphinx directives
    rst_content = '''
:fas:`newspaper` Latest News
============================

'''

    # Generate native RST content for each blog post
    for i, post in enumerate(latest_posts):
        # Format date for display
        display_date = post['date']
        if display_date:
            try:
                date_obj = datetime.strptime(display_date, '%Y-%m-%d')
                display_date = date_obj.strftime('%B %d, %Y')
            except:
                pass

        # Create a simple link based on filename
        read_more_link = f"latest_news/{post['filename']}"

        # Use post image if available, otherwise use DTU logo
        image_path = post.get('image', '../_static/DTU_logo_Coral_Red_CMYK.svg')

        # Add blog post using native RST directives
        rst_content += f'''
.. container:: blog-post-card

   .. container:: blog-post-header

      .. container:: blog-post-meta

         :fas:`calendar-alt` {display_date}
         
         :fas:`user` {post['author']}

      .. container:: blog-post-badge

         Latest

   .. container:: blog-post-body

      .. container:: blog-post-content

         .. container:: blog-post-text

            .. container:: blog-post-title

               {post['title']}

            .. container:: blog-post-excerpt

               {post['excerpt']}

            .. container:: blog-post-actions

               :doc:`Read Full Post <{read_more_link}>`

         .. container:: blog-post-image

            .. image:: {image_path}
               :alt: {post['title']}
               :width: 200px
'''

    return rst_content


def create_news_carousel(app):
    """Create the news carousel RST file during Sphinx build."""
    try:
        # Get the source directory
        src_dir = Path(app.srcdir)
        news_dir = src_dir / 'latest_news'

        # Load news posts
        posts = get_latest_news_posts(news_dir)

        # Generate carousel RST
        carousel_rst = generate_carousel_rst(posts)

        # Write to RST include file
        carousel_file = src_dir / '_rst_includes' / 'latest_news_carousel.rst'
        carousel_file.parent.mkdir(exist_ok=True)

        with open(carousel_file, 'w', encoding='utf-8') as f:
            f.write(carousel_rst)

        print(f"Generated news carousel RST with {len(posts)} posts")

    except Exception as e:
        print(f"Error creating news carousel: {e}")


def setup_latest_news(app):
    """Setup function for the latest news extension."""
    app.connect('builder-inited', create_news_carousel)