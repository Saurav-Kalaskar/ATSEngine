import re
from typing import Dict, Tuple

def extract_and_templatize_bullets(latex_code: str) -> Tuple[Dict[str, str], str]:
    """
    Extracts bullet points (\\item ...) from the 'Professional Experience' 
    and 'Projects' sections ONLY. 
    
    Returns:
    - bullets_map: A dictionary mapping bullet IDs to their original text.
      e.g., {"bullet_0": "Built financial POCs...", "bullet_1": "..."}
    - templated_latex: The original LaTeX code with the text of those 
      bullets replaced by Jinja-style placeholders like {{bullet_0}}.
    """
    templated_latex = latex_code
    bullets_map = {}
    bullet_counter = 0

    # 1. Isolate the target sections to avoid touching Skills or Education
    # We look for \section{Professional Experience} ... down to \section{Publications
    # or just find all \begin{itemize} ... \end{itemize} after those sections.
    
    # Let's split by \section 
    section_pattern = re.compile(r'(\\section\{.*?\})', re.DOTALL | re.IGNORECASE)
    parts = section_pattern.split(templated_latex)
    
    # We will iterate through parts and if the previous part was one of our targets, we template its items
    target_sections = ['professional experience', 'projects', 'experience']
    
    is_target_section = False
    
    for i in range(len(parts)):
        part = parts[i]
        
        # Check if this part is a section header
        if part.startswith(r'\section'):
            lower_header = part.lower()
            is_target_section = any(target in lower_header for target in target_sections)
            continue
            
        # If it's the content following a target section header
        if is_target_section:
            # Find all \begin{itemize} ... \end{itemize} blocks
            itemize_pattern = re.compile(r'(\\begin\{itemize\})(.*?)(\\end\{itemize\})', re.DOTALL)
            
            def itemize_replacer(match):
                nonlocal bullet_counter
                prefix = match.group(1)
                content = match.group(2)
                suffix = match.group(3)
                
                # Now find all \item inside the content
                # Match \item followed by anything until the next \item or end of string
                item_pattern = re.compile(r'(\\item\s+)(.*?)(?=\\item\s+|\\end\{itemize\}|$)', re.DOTALL)
                
                def item_replacer(item_match):
                    nonlocal bullet_counter
                    item_prefix = item_match.group(1)
                    item_text_raw = item_match.group(2)
                    item_text_clean = item_text_raw.strip()
                    
                    if item_text_clean: # Ignore empty items
                        bullet_id = f"bullet_{bullet_counter}"
                        bullets_map[bullet_id] = item_text_clean
                        bullet_counter += 1
                        
                        # Preserve exact leading/trailing whitespace of the matched raw string
                        # by only replacing the inner text chunk
                        new_raw = item_text_raw.replace(item_text_clean, f"{{{{{bullet_id}}}}}")
                        return f"{item_prefix}{new_raw}"
                    return item_match.group(0)
                
                new_content = item_pattern.sub(item_replacer, content)
                return f"{prefix}{new_content}{suffix}"
                
            parts[i] = itemize_pattern.sub(itemize_replacer, part)

    # Rejoin the document
    templated_latex = "".join(parts)
    return bullets_map, templated_latex

def reconstruct_latex(templated_latex: str, updated_bullets: Dict[str, str]) -> str:
    """
    Replaces the {{bullet_X}} placeholders with the updated text.
    """
    final_latex = templated_latex
    for bullet_id, text in updated_bullets.items():
        placeholder = f"{{{{{bullet_id}}}}}"
        final_latex = final_latex.replace(placeholder, text)
    return final_latex
