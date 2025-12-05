import re
from typing import Optional

def generate_excerpt(
    content: str, 
    max_length: int = 200,
    min_length: int = 50,
    preserve_paragraphs: bool = False
) -> str:
    """
    Generate a readable excerpt from HTML or plain text content
    
    Args:
        content: The full content (HTML or plain text)
        max_length: Maximum excerpt length
        min_length: Minimum excerpt length before adding ellipsis
        preserve_paragraphs: Try to keep paragraph structure
    
    Returns:
        Generated excerpt string
    """
    if not content:
        return ""
    
    # 1. Clean HTML tags
    clean_content = re.sub(r'<[^>]+>', ' ', content)
    
    # 2. Remove excessive whitespace
    clean_content = re.sub(r'\s+', ' ', clean_content).strip()
    
    # 3. If content is already short enough, return as is
    if len(clean_content) <= max_length:
        return clean_content
    
    # 4. Try to find a good sentence boundary
    truncated = clean_content[:max_length]
    
    # Look for sentence boundaries
    sentence_indicators = [
        ('. ', 1),    # Period with space
        ('! ', 1),    # Exclamation with space  
        ('? ', 1),    # Question with space
        ('.', 0),     # Just period
        ('!', 0),     # Just exclamation
        ('?', 0),     # Just question
        (', ', 1),    # Comma with space (fallback)
        ('; ', 1),    # Semicolon with space
    ]
    
    for indicator, offset in sentence_indicators:
        last_pos = truncated.rfind(indicator)
        if last_pos > min_length:  # Ensure we have meaningful content
            end_pos = last_pos + offset + 1 if offset > 0 else last_pos + 1
            excerpt = truncated[:end_pos]
            
            # Don't end with just "Mr.", "Dr.", etc.
            if not re.search(r'\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr)\.$', excerpt):
                return excerpt
    
    # 5. Fallback: Cut at word boundary
    last_space = truncated.rfind(' ')
    if last_space > min_length:
        return truncated[:last_space] + '...'
    
    # 6. Final fallback: Hard truncate
    return truncated + '...'

def generate_excerpt_from_html(
    html_content: str,
    max_length: int = 200,
    preserve_first_paragraph: bool = True
) -> str:
    """Specialized generator for HTML content"""
    if preserve_first_paragraph:
        # Extract first paragraph
        first_p_match = re.search(r'<p[^>]*>(.*?)</p>', html_content, re.DOTALL)
        if first_p_match:
            first_p = first_p_match.group(1)
            # Remove inner HTML tags from the paragraph
            clean_p = re.sub(r'<[^>]+>', '', first_p)
            clean_p = re.sub(r'\s+', ' ', clean_p).strip()
            
            if len(clean_p) <= max_length:
                return clean_p
            return generate_excerpt(clean_p, max_length)
    
    # Fallback to regular generation
    return generate_excerpt(html_content, max_length)