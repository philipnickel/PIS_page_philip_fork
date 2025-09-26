# Latest News Display

This directory contains the latest news posts that will be displayed as cards on the homepage using native Sphinx directives.

## How to Add New News Posts

1. **Create a new RST file** in this directory with a descriptive filename (e.g., `workshop_announcement_2024.rst`)

2. **Use this template** for your news post:

```rst
Your News Title Here
====================

:date: YYYY-MM-DD
:author: DTU Python Support
:image: ../_static/DTU_logo_Coral_Red_CMYK.svg

Write your news post content here. The first paragraph will be automatically extracted as an excerpt for the news cards.

Section Heading
---------------

You can add more detailed content in sections like this. The cards will only show an excerpt, but clicking "Read More" will take users to the full post.

**Key points:**
- Use proper RST formatting
- Keep the first paragraph engaging as it becomes the excerpt
- Include relevant dates and author information
```

3. **Required metadata** (place at the top of the file):
   - `:date:` - Publication date in YYYY-MM-DD format
   - `:author:` - Author name (usually "DTU Python Support")
   - `:image:` - Optional image path relative to the docs directory

4. **Build the site** to see your changes:
   ```bash
   ./venv/bin/python -m sphinx -b html docs build/html
   ```

## How the News Display Works

- **Automatic Loading**: The system automatically finds all `.rst` files in this directory
- **Sorting**: Posts are sorted by date (newest first)
- **Display**: Shows up to 5 most recent posts as cards
- **Excerpt**: Automatically extracts the first paragraph(s) as excerpt
- **Native Sphinx**: Uses `sphinx-design` grid and card directives

## News Display Features

- **Responsive Design**: Cards adapt to screen size (1 column mobile, 2 tablet, 3 desktop)
- **Professional Styling**: Uses your site's existing theme and colors
- **Native Integration**: Pure Sphinx directives, no custom HTML/CSS/JS needed
- **Accessibility**: Proper semantic markup through sphinx-design
- **Easy Maintenance**: Just add RST files and rebuild

## File Naming Convention

Use descriptive filenames that reflect the content:
- `workshop_update_2024_09.rst`
- `python_installation_tips.rst`
- `discord_community_milestone.rst`
- `course_announcement_autumn_2024.rst`

## Technical Implementation

The news display is implemented using:
- **`sphinx-design`** grid and card directives for layout
- **Python extension** (`ps_modules/latest_news.py`) for automatic content loading
- **RST include** (`_rst_includes/latest_news_carousel.rst`) for generated content
- **Native Sphinx build process** - no external dependencies

This approach is much cleaner than custom HTML/CSS/JS and integrates perfectly with your existing Sphinx workflow!