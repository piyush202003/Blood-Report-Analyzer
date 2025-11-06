from django import template
import re

register = template.Library()

@register.filter(name='clean_markdown')
def clean_markdown(text):
    """Remove markdown formatting and convert to clean HTML"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = text.strip()
    
    # Remove all markdown formatting
    text = re.sub(r'\*\*+([^*]+)\*\*+', r'\1', text)  # Remove bold
    text = re.sub(r'\*', '', text)  # Remove asterisks
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)  # Remove headers
    
    # Convert bullet points to list items
    text = re.sub(r'^\s*[-•*]\s+(.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    
    # Wrap consecutive <li> tags in <ul>
    text = re.sub(r'(<li>.*?</li>\s*)+', r'<ul class="simple-list">\g<0></ul>', text, flags=re.DOTALL)
    
    # Clean up multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text


@register.filter(name='simple_list')
def simple_list(text):
    """Format text as a simple, clean list with icons"""
    if not text:
        return '<p class="text-muted">No recommendations available.</p>'
    
    lines = text.split('\n')
    formatted_items = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Remove all markdown and formatting
        line = re.sub(r'\*\*', '', line)
        line = re.sub(r'^\d+\.\s*', '', line)  # Remove numbering
        line = re.sub(r'^[-•*]\s*', '', line)  # Remove bullet points
        line = re.sub(r'^#+\s*', '', line)  # Remove headers
        
        # Skip section headers
        if any(keyword in line.lower() for keyword in ['foods to', 'recommended', 'avoid these', 'daily habit', 'lifestyle', 'analysis']):
            continue
        
        # Split on colon to separate item from description
        if ':' in line:
            parts = line.split(':', 1)
            item = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ''
            formatted_items.append(f'<li><strong>{item}:</strong> {desc}</li>')
        else:
            formatted_items.append(f'<li>{line}</li>')
    
    if formatted_items:
        return f'<ul class="simple-list">{"".join(formatted_items)}</ul>'
    return '<p class="text-muted">No recommendations available.</p>'


@register.filter(name='count_items')
def count_items(text):
    """Count the number of bullet points in text"""
    if not text:
        return 0
    lines = [line.strip() for line in text.split('\n') if line.strip() and line.strip().startswith('-')]
    return len(lines)


@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get item from dictionary by key - used for template dict access"""
    if dictionary is None:
        return None
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)
