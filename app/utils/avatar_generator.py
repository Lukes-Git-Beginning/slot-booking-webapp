# -*- coding: utf-8 -*-
"""
Avatar Generator - DiceBear API Integration
Generates avatar URLs for cosmetic shop avatars
"""

def get_avatar_url(avatar_id, category="default", size=128):
    """
    Generate DiceBear avatar URL based on avatar ID and category

    Args:
        avatar_id: Unique identifier for the avatar (e.g., "ninja", "robot")
        category: Avatar category determining style
        size: Image size in pixels (default: 128)

    Returns:
        str: DiceBear API URL for the avatar image

    Styles:
    - professional/academic: avataaars (human-like professional avatars)
    - tech: bottts (robot-style avatars)
    - fun/adventure: adventurer (cartoon characters)
    - mystical/heroic: lorelei (fantasy characters)
    - space: shapes (abstract geometric)
    - luxury: initials (elegant letter-based)
    """

    # Map categories to DiceBear styles
    style_map = {
        "professional": "avataaars",
        "academic": "avataaars",
        "tech": "bottts",
        "fun": "adventurer",
        "adventure": "adventurer",
        "mystical": "lorelei",
        "heroic": "lorelei",
        "space": "shapes",
        "luxury": "initials"
    }

    # Default style for unknown categories
    style = style_map.get(category, "avataaars")

    # Generate URL
    base_url = "https://api.dicebear.com/7.x"
    avatar_url = f"{base_url}/{style}/svg?seed={avatar_id}&size={size}"

    # Add style-specific customizations
    if style == "avataaars":
        # Professional human avatars with various options
        avatar_url += "&backgroundColor=b6e3f4,c0aede,d1d4f9"
    elif style == "bottts":
        # Robot avatars
        avatar_url += "&backgroundColor=transparent"
    elif style == "adventurer":
        # Fun cartoon characters
        avatar_url += "&backgroundColor=ffdfbf,ffd5dc,d1d4f9"
    elif style == "lorelei":
        # Fantasy/mystical characters
        avatar_url += "&backgroundColor=65c9ff,b6e3f4,ffd5dc"
    elif style == "shapes":
        # Abstract geometric for aliens/space
        avatar_url += "&backgroundColor=000000"
    elif style == "initials":
        # Elegant letter-based for luxury
        avatar_url += "&backgroundColor=ffdfbf&fontSize=45"

    return avatar_url


def get_avatar_style_for_category(category):
    """
    Get the DiceBear style name for a given category

    Args:
        category: Avatar category string

    Returns:
        str: DiceBear style name
    """
    style_map = {
        "professional": "avataaars",
        "academic": "avataaars",
        "tech": "bottts",
        "fun": "adventurer",
        "adventure": "adventurer",
        "mystical": "lorelei",
        "heroic": "lorelei",
        "space": "shapes",
        "luxury": "initials"
    }

    return style_map.get(category, "avataaars")


# Jinja2 filter function for templates
def avatar_url_filter(avatar_id, category="default", size=128):
    """Template filter for generating avatar URLs"""
    return get_avatar_url(avatar_id, category, size)
