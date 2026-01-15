import re

def strip_markdown(text: str) -> str:
    """
    Remove markdown formatting from a string to produce plain text.
    Handles headers, bold/italic, links, and list markers.
    """
    if not text:
        return ""

    # Remove headers (e.g. # Title -> Title)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    
    # Remove bold/italic (e.g. **bold** -> bold, *italic* -> italic)
    # Matches pair of **, *, __, or _
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)
    
    # Remove links (e.g. [text](url) -> text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Remove images (e.g. ![alt](url) -> alt)
    text = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Remove code blocks (e.g. ```code``` -> code)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # Remove blockquotes
    text = re.sub(r'^>\s?', '', text, flags=re.MULTILINE)

    # Remove horizontal rules
    text = re.sub(r'^(-{3,}|_{3,}|\*{3,})$', '', text, flags=re.MULTILINE)
    
    # Normalize list markers (e.g. * Item -> Item, - Item -> Item)
    # Keeping the newline structure but removing the bullets for "plain text" summaries usually looks cleaner 
    # if it's for a meta description, but for a "plain text" view, keeping indentation might be hard.
    # Let's just remove the bullet point itself.
    text = re.sub(r'^[\*\-]\s+', '', text, flags=re.MULTILINE)
    
    # Remove extra newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
