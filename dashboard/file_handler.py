"""
File handling utilities for SAS code processing
"""

import re
from typing import Tuple, Dict


def read_sas_file(uploaded_file) -> str:
    """
    Read SAS file content from Streamlit upload.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
    
    Returns:
        str: File content
    """
    try:
        return uploaded_file.getvalue().decode('utf-8')
    except UnicodeDecodeError:
        # Try with different encoding
        return uploaded_file.getvalue().decode('latin-1')


def validate_sas_file(content: str) -> Tuple[bool, str]:
    """
    Basic SAS file validation.
    
    Args:
        content: File content as string
    
    Returns:
        Tuple of (is_valid, message)
    """
    if not content.strip():
        return False, "File is empty"
    
    # Check for common SAS keywords
    sas_keywords = ['PROC', 'DATA', 'RUN', 'QUIT', 'SELECT', 'FROM', 'LIBNAME']
    content_upper = content.upper()
    has_sas_keyword = any(keyword in content_upper for keyword in sas_keywords)
    
    if not has_sas_keyword:
        return False, "File does not appear to contain SAS code (no PROC, DATA, or SQL keywords found)"
    
    return True, "Valid SAS file"


def extract_metadata(content: str) -> Dict:
    """
    Extract metadata from SAS code.
    
    Args:
        content: SAS code content
    
    Returns:
        dict with metadata about the SAS code
    """
    lines = content.split('\n')
    content_upper = content.upper()
    
    # Find PROC statements
    proc_matches = re.findall(r'PROC\s+(\w+)', content, re.IGNORECASE)
    procs_used = list(set(proc_matches))
    
    # Find table references
    table_matches = re.findall(r'FROM\s+[\w.]+|DATA\s+[\w.]+', content, re.IGNORECASE)
    
    # Check for specific SAS features
    has_proc_sql = 'PROC SQL' in content_upper
    has_proc_freq = 'PROC FREQ' in content_upper
    has_data_step = bool(re.search(r'DATA\s+\w+', content, re.IGNORECASE))
    has_libname = 'LIBNAME' in content_upper
    has_macro = '%' in content
    
    return {
        "line_count": len(lines),
        "non_empty_lines": len([line for line in lines if line.strip()]),
        "procs_used": procs_used,
        "proc_count": len(procs_used),
        "has_sql": has_proc_sql,
        "has_freq": has_proc_freq,
        "has_data_step": has_data_step,
        "has_libname": has_libname,
        "has_macro": has_macro,
        "table_references": len(table_matches)
    }


def prepare_download(code: str, filename: str, output_type: str) -> Tuple[str, str]:
    """
    Prepare converted code for download.
    
    Args:
        code: Converted code content
        filename: Original filename
        output_type: Either "PySpark" or "SQL"
    
    Returns:
        Tuple of (code_content, download_filename)
    """
    extension = ".py" if output_type == "PySpark" else ".sql"
    
    # Remove .sas extension if present
    base_filename = filename.replace('.sas', '').replace('.SAS', '')
    
    download_filename = f"{base_filename}_converted{extension}"
    
    return code, download_filename


def estimate_conversion_complexity(content: str) -> str:
    """
    Estimate conversion complexity based on SAS code features.
    
    Args:
        content: SAS code content
    
    Returns:
        str: "Simple", "Medium", or "Complex"
    """
    metadata = extract_metadata(content)
    
    # Simple: Basic SQL or single DATA step
    if metadata["proc_count"] <= 1 and not metadata["has_macro"] and metadata["line_count"] < 50:
        return "Simple"
    
    # Complex: Macros, multiple PROCs, or very long
    if metadata["has_macro"] or metadata["proc_count"] >= 3 or metadata["line_count"] > 200:
        return "Complex"
    
    # Medium: Everything else
    return "Medium"


def format_sas_code_preview(content: str, max_lines: int = 20) -> str:
    """
    Format SAS code preview for display.
    
    Args:
        content: SAS code content
        max_lines: Maximum lines to show
    
    Returns:
        str: Formatted preview
    """
    lines = content.split('\n')
    
    if len(lines) <= max_lines:
        return content
    
    preview_lines = lines[:max_lines]
    remaining = len(lines) - max_lines
    
    preview = '\n'.join(preview_lines)
    preview += f"\n\n... ({remaining} more lines)"
    
    return preview

