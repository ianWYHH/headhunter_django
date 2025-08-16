from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter
def highlight_keywords(text, keywords):
    """
    Highlight search keywords in text using <mark> tags.
    Supports both string and list of strings for text (for JSON fields).
    """
    if not text or not keywords:
        return text
    
    # Handle JSON fields (lists)
    if isinstance(text, list):
        # Join list items with commas for display
        text = ', '.join(str(item) for item in text if item)
    
    # Convert to string if needed
    text = str(text)
    
    # Split keywords by spaces to handle multiple words
    keyword_list = keywords.split()
    
    # Escape special regex characters in keywords
    escaped_keywords = [re.escape(keyword) for keyword in keyword_list if keyword.strip()]
    
    if not escaped_keywords:
        return text
    
    # Create regex pattern for case-insensitive matching
    pattern = '|'.join(escaped_keywords)
    
    def replace_match(match):
        return f'<mark class="search-highlight">{match.group(0)}</mark>'
    
    # Apply highlighting
    highlighted_text = re.sub(f'({pattern})', replace_match, text, flags=re.IGNORECASE)
    
    return mark_safe(highlighted_text)

@register.filter
def truncate_and_highlight(text, length_and_keywords):
    """
    Truncate text and then highlight keywords.
    Usage: {{ text|truncate_and_highlight:"60,search_term" }}
    """
    if not text:
        return text
    
    # Split arguments
    try:
        if ',' in str(length_and_keywords):
            length, keywords = str(length_and_keywords).split(',', 1)
            length = int(length.strip())
            keywords = keywords.strip()
        else:
            length = int(length_and_keywords)
            keywords = ''
    except (ValueError, AttributeError):
        return text
    
    # Handle JSON fields (lists)
    if isinstance(text, list):
        text = ', '.join(str(item) for item in text if item)
    
    # Convert to string and truncate
    text = str(text)
    if len(text) > length:
        text = text[:length] + '...'
    
    # Apply highlighting if keywords provided
    if keywords:
        return highlight_keywords(text, keywords)
    else:
        return text

@register.simple_tag
def highlight_keywords_tag(text, keywords):
    """
    Template tag version of highlight_keywords for more complex usage
    """
    # Handle JSON fields (lists) and truncate
    if isinstance(text, list):
        text = ', '.join(str(item) for item in text if item)
    
    text = str(text)
    if len(text) > 60:
        text = text[:60] + '...'
    
    return highlight_keywords(text, keywords)