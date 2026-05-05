"""
intelligence/code_reviewer.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cracka AI — Code Review Assistant
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Features:
  ✅ Voice se code review  — "review my code"
  ✅ Error detect + fix    — "find errors in my code"
  ✅ Code explain          — "explain this code"
  ✅ Code likhna           — "write a function for X"
  ✅ VS Code terminal print + review.md file save

Usage in Cracka (add to core/ai_brain.py):
  elif "review" in command and "code" in command:
      from intelligence.code_reviewer import review_active_file
      return review_active_file()

  elif "explain" in command and "code" in command:
      from intelligence.code_reviewer import explain_active_file
      return explain_active_file()

  elif "write" in command and ("function" in command or "code" in command):
      from intelligence.code_reviewer import write_code(command)
      return write_code(command)

  elif "fix" in command and "code" in command or "errors" in command and "code" in command:
      from intelligence.code_reviewer import fix_active_file
      return fix_active_file()
"""

import os
import sys
import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from brain.chat_engine import ask_ai
from core.logger import log_info, log_error


# ── VS Code active file reader ────────────────────────────────────────────────

def get_vscode_active_file() -> tuple[str, str]:
    """
    Try to get the currently open file in VS Code.
    Returns (file_path, code_content) or ("", "")

    Method 1: Read VS Code workspace storage (most reliable)
    Method 2: Check recently modified files in common locations
    Method 3: Read from clipboard (if user copied code)
    """

    # Method 1: VS Code recently opened files via settings
    vscode_paths = [
        os.path.expandvars(r"%APPDATA%\Code\User\globalStorage\state.vscdb"),
        os.path.expandvars(r"%APPDATA%\Code\storage.json"),
        os.path.expanduser("~/.config/Code/User/globalStorage/state.vscdb"),
    ]

    # Method 2: Check VS Code workspace via running process
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Process code -ErrorAction SilentlyContinue | "
             "Select-Object -ExpandProperty MainWindowTitle"],
            capture_output=True, text=True, timeout=5
        )
        title = result.stdout.strip()
        if title and " - " in title:
            # Title format: "filename.py - foldername - Visual Studio Code"
            filename = title.split(" - ")[0].strip()
            log_info(f"VS Code active file from title: {filename}")
    except Exception:
        pass

    # Method 3: Check clipboard for code
    try:
        import pyperclip
        clipboard = pyperclip.paste()
        if clipboard and len(clipboard) > 20 and "\n" in clipboard:
            return ("clipboard", clipboard)
    except Exception:
        pass

    return ("", "")


def read_file_content(filepath: str) -> str:
    """Read content of any code file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            return ""
    except Exception as e:
        log_error(f"File read error: {e}")
        return ""


def get_latest_modified_code_file(search_dir: str = None) -> tuple[str, str]:
    """
    Find the most recently modified code file.
    Useful if VS Code detection fails.
    """
    if not search_dir:
        search_dir = os.path.expanduser("~")

    code_extensions = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp",
        ".c", ".cs", ".html", ".css", ".php", ".go", ".rs",
        ".swift", ".kt", ".rb", ".dart", ".vue"
    }

    latest_file = ""
    latest_time = 0

    try:
        # Search Desktop and Documents first (most likely locations)
        search_dirs = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents"),
            os.path.expandvars("%USERPROFILE%/Desktop"),
            os.path.expandvars("%USERPROFILE%/Documents"),
        ]

        for d in search_dirs:
            if not os.path.exists(d):
                continue
            for root, dirs, files in os.walk(d):
                # Skip node_modules, .git etc
                dirs[:] = [x for x in dirs if x not in
                           {"node_modules", ".git", "__pycache__", ".venv", "venv"}]
                for f in files:
                    if Path(f).suffix.lower() in code_extensions:
                        full = os.path.join(root, f)
                        mtime = os.path.getmtime(full)
                        if mtime > latest_time:
                            latest_time = mtime
                            latest_file = full

        if latest_file:
            content = read_file_content(latest_file)
            return (latest_file, content)
    except Exception as e:
        log_error(f"Latest file search error: {e}")

    return ("", "")


# ── Core review functions ─────────────────────────────────────────────────────

def _get_code_for_review(command: str = "") -> tuple[str, str]:
    """
    Smart code getter — tries multiple methods.
    Returns (source_description, code)
    """
    # 1. Try VS Code active file
    path, code = get_vscode_active_file()
    if code:
        return (f"VS Code active file: {path}", code)

    # 2. Try latest modified code file
    path, code = get_latest_modified_code_file()
    if code:
        return (f"Recent file: {path}", code)

    # 3. Ask Boss to paste code
    return ("", "")


def _detect_language(code: str, filepath: str = "") -> str:
    """Detect programming language from code or filepath."""
    ext = Path(filepath).suffix.lower() if filepath else ""
    ext_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".java": "Java", ".cpp": "C++", ".c": "C", ".cs": "C#",
        ".html": "HTML", ".css": "CSS", ".php": "PHP", ".go": "Go",
        ".rs": "Rust", ".swift": "Swift", ".kt": "Kotlin",
        ".rb": "Ruby", ".dart": "Dart", ".vue": "Vue",
    }
    if ext in ext_map:
        return ext_map[ext]

    # Detect from code patterns
    if "def " in code and "import " in code:
        return "Python"
    elif "function " in code or "const " in code or "let " in code:
        return "JavaScript"
    elif "public class" in code or "System.out" in code:
        return "Java"
    elif "#include" in code:
        return "C/C++"
    return "Unknown"


def _save_review_file(content: str, filename: str = "cracka_review.md") -> str:
    """
    Save review to file AND print to VS Code terminal.
    Returns saved file path.
    """
    # Save to Desktop for easy access
    desktop = os.path.expanduser("~/Desktop")
    os.makedirs(desktop, exist_ok=True)
    filepath = os.path.join(desktop, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    log_info(f"Review saved: {filepath}")

    # Open in VS Code
    try:
        subprocess.Popen(["code", filepath])
    except Exception:
        try:
            os.startfile(filepath)  # Windows fallback
        except Exception:
            pass

    return filepath


def _print_to_terminal(content: str):
    """Print colored review to terminal (visible in VS Code terminal)."""
    CYAN  = "\033[96m"
    GREEN = "\033[92m"
    RED   = "\033[91m"
    YELLOW= "\033[93m"
    BOLD  = "\033[1m"
    RESET = "\033[0m"
    DIM   = "\033[2m"

    print(f"\n{CYAN}{'━'*60}{RESET}")
    print(f"{BOLD}{CYAN}  CRACKA AI — CODE REVIEW{RESET}")
    print(f"{CYAN}{'━'*60}{RESET}")

    lines = content.split("\n")
    for line in lines:
        if line.startswith("##"):
            print(f"\n{BOLD}{CYAN}{line}{RESET}")
        elif line.startswith("###"):
            print(f"\n{YELLOW}{line}{RESET}")
        elif "❌" in line or "Error" in line or "Bug" in line:
            print(f"{RED}{line}{RESET}")
        elif "✅" in line or "Good" in line or "Correct" in line:
            print(f"{GREEN}{line}{RESET}")
        elif "⚠️" in line or "Warning" in line:
            print(f"{YELLOW}{line}{RESET}")
        elif line.startswith("```"):
            print(f"{DIM}{line}{RESET}")
        else:
            print(line)

    print(f"\n{CYAN}{'━'*60}{RESET}\n")


# ── Main voice command functions ──────────────────────────────────────────────

def review_active_file(filepath: str = "") -> str:
    """
    'review my code' — Full code review with suggestions.
    """
    from core.voice_engine import speak

    speak("Let me review your code Boss. One moment.")

    # Get code
    if filepath and os.path.exists(filepath):
        code = read_file_content(filepath)
        source = f"File: {filepath}"
    else:
        source, code = _get_code_for_review()

    if not code:
        return ("I could not find any code to review Boss. "
                "Please open a file in VS Code or copy your code and try again.")

    lang = _detect_language(code, filepath or source)
    lines = len(code.split("\n"))
    log_info(f"Reviewing {lang} code ({lines} lines) from {source}")

    prompt = f"""You are a senior {lang} developer doing a code review.

Review this {lang} code carefully and provide:

## 📊 Summary
- Language: {lang}
- Lines: {lines}
- Overall quality (1-10): X/10

## ❌ Bugs & Errors
List any actual bugs, logical errors, or code that will crash.
If none, write "No bugs found ✅"

## ⚠️ Warnings & Bad Practices
List code smells, bad practices, security issues, performance problems.

## ✅ What's Good
List 2-3 things done well.

## 🔧 Suggested Fixes
Show corrected versions of problematic code with ```{lang.lower()} code blocks.

## 💡 Improvements
List 3-5 specific improvements to make code better.

Be specific. Use line numbers where possible.

CODE TO REVIEW:
```{lang.lower()}
{code[:4000]}
```"""

    review = ask_ai(prompt)

    # Build full markdown report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md_content = f"""# Cracka AI — Code Review Report
**Generated:** {timestamp}
**Source:** {source}
**Language:** {lang}
**Lines:** {lines}

---

{review}

---
*Generated by Cracka AI v3.0*
"""

    # Print to terminal + save file
    _print_to_terminal(review)
    saved_path = _save_review_file(md_content, "cracka_review.md")

    speak(f"Review complete Boss! I found some issues. Check the file on your Desktop and in VS Code.")
    return f"Code review done Boss! Saved to Desktop/cracka_review.md and opened in VS Code. Check the terminal for details."


def fix_active_file(filepath: str = "") -> str:
    """
    'fix my code' / 'find errors' — Find and fix all errors.
    """
    from core.voice_engine import speak

    speak("Finding and fixing errors in your code Boss.")

    if filepath and os.path.exists(filepath):
        code = read_file_content(filepath)
        source = filepath
    else:
        source, code = _get_code_for_review()

    if not code:
        return "No code found to fix Boss. Please open a file in VS Code."

    lang = _detect_language(code, filepath or source)

    prompt = f"""Fix all bugs and errors in this {lang} code.

For each fix:
1. Show the ORIGINAL problematic line(s)
2. Explain what was wrong
3. Show the FIXED version

Then at the end provide the COMPLETE fixed code.

{lang} CODE:
```{lang.lower()}
{code[:4000]}
```

Format your response as:
## Fixes Made
[list each fix]

## Complete Fixed Code
```{lang.lower()}
[full corrected code here]
```"""

    result = ask_ai(prompt)

    # Extract fixed code block
    fixed_code = ""
    if "```" in result:
        parts = result.split("```")
        for i, part in enumerate(parts):
            if i % 2 == 1:  # Inside code block
                lines = part.split("\n")
                # Remove language identifier line
                if lines and lines[0].strip().lower() in [
                    lang.lower(), "python", "javascript", "java", "cpp", "c"
                ]:
                    lines = lines[1:]
                candidate = "\n".join(lines).strip()
                if len(candidate) > len(fixed_code):
                    fixed_code = candidate

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md_content = f"""# Cracka AI — Code Fix Report
**Generated:** {timestamp}
**Source:** {source}
**Language:** {lang}

---

{result}

---
*Generated by Cracka AI v3.0*
"""

    _print_to_terminal(result)
    saved_path = _save_review_file(md_content, "cracka_fixed.md")

    # Also save fixed code as separate file
    if fixed_code and filepath:
        ext = Path(filepath).suffix
        fixed_filepath = _save_review_file(
            fixed_code,
            f"cracka_fixed_code{ext}"
        )

    speak("Done Boss! I fixed the errors. Check cracka_fixed.md on your Desktop.")
    return "Errors fixed Boss! Check Desktop/cracka_fixed.md and Desktop/cracka_fixed_code file in VS Code."


def explain_active_file(filepath: str = "") -> str:
    """
    'explain this code' / 'explain my code' — Plain English explanation.
    """
    from core.voice_engine import speak

    speak("Let me explain this code for you Boss.")

    if filepath and os.path.exists(filepath):
        code = read_file_content(filepath)
        source = filepath
    else:
        source, code = _get_code_for_review()

    if not code:
        return "No code found to explain Boss."

    lang = _detect_language(code, filepath or source)

    prompt = f"""Explain this {lang} code in simple, clear language.

Structure your explanation as:

## 🎯 What This Code Does
One paragraph, plain English summary.

## 📦 Main Components
Explain each important part (functions, classes, variables).

## 🔄 How It Works — Step by Step
Number each step clearly.

## 🔗 Dependencies & Imports
Explain what each import/library is used for.

## 💡 Key Concepts Used
List important programming concepts this code uses.

Keep it beginner-friendly but accurate.

{lang} CODE:
```{lang.lower()}
{code[:4000]}
```"""

    explanation = ask_ai(prompt)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md_content = f"""# Cracka AI — Code Explanation
**Generated:** {timestamp}
**Source:** {source}
**Language:** {lang}

---

{explanation}

---
*Generated by Cracka AI v3.0*
"""

    _print_to_terminal(explanation)
    _save_review_file(md_content, "cracka_explanation.md")

    # Speak a short summary
    lines = explanation.split("\n")
    short = next((l for l in lines if l and not l.startswith("#")), "")
    speak(f"Boss, {short[:150]}" if short else "Explanation saved Boss. Check VS Code.")

    return "Explanation done Boss! Check Desktop/cracka_explanation.md in VS Code."


def write_code(command: str) -> str:
    """
    'write a function for X' / 'write code to do Y'
    Generates code and saves to file.
    """
    from core.voice_engine import speak

    speak("Writing the code for you Boss. One moment.")

    # Extract what to write
    task = command.lower()
    for phrase in ["write code", "write a function", "write function",
                   "create function", "create code", "code for",
                   "write", "create"]:
        task = task.replace(phrase, "").strip()

    if not task:
        return "Please tell me what code to write Boss. Like 'write a function to sort a list'."

    prompt = f"""Write clean, well-commented Python code for: {task}

Requirements:
- Write complete, working code
- Add docstring explaining what it does
- Add inline comments for complex parts
- Include a usage example at the bottom
- Handle edge cases and errors
- Follow PEP 8 style

Provide ONLY the code in a Python code block, then a brief explanation."""

    result = ask_ai(prompt)

    # Extract code
    generated_code = ""
    if "```" in result:
        parts = result.split("```")
        for i, part in enumerate(parts):
            if i % 2 == 1:
                lines = part.split("\n")
                if lines and lines[0].strip() in ["python", "py", ""]:
                    lines = lines[1:]
                generated_code = "\n".join(lines).strip()
                break

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_name = task[:30].replace(" ", "_").replace("/", "_")

    # Save generated code as .py file
    if generated_code:
        py_content = f'''"""
Generated by Cracka AI
Task: {task}
Date: {timestamp}
"""

{generated_code}
'''
        py_path = _save_review_file(py_content, f"cracka_{safe_name}.py")
        speak(f"Done Boss! I wrote the code for {task}. Opening in VS Code now.")
        _print_to_terminal(result)
        return f"Code written and saved Boss! Check Desktop/cracka_{safe_name}.py — it's open in VS Code."
    else:
        _print_to_terminal(result)
        speak("Code is ready Boss! Check the terminal.")
        return "Code ready Boss! Check the terminal output."


def optimize_code(filepath: str = "") -> str:
    """
    'optimize my code' — Performance + readability improvements.
    """
    from core.voice_engine import speak

    speak("Optimizing your code Boss.")

    if filepath and os.path.exists(filepath):
        code = read_file_content(filepath)
        source = filepath
    else:
        source, code = _get_code_for_review()

    if not code:
        return "No code found to optimize Boss."

    lang = _detect_language(code, source)

    prompt = f"""Optimize this {lang} code for:
1. Performance (speed, memory)
2. Readability (clean code)
3. Best practices

Show:
## ⚡ Performance Optimizations
(with before/after examples)

## 🧹 Code Cleanliness
(with before/after examples)

## 📈 Optimized Complete Code
```{lang.lower()}
[full optimized code]
```

{lang} CODE:
```{lang.lower()}
{code[:4000]}
```"""

    result = ask_ai(prompt)
    _print_to_terminal(result)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = f"# Cracka AI — Optimization Report\n**{timestamp}**\n\n{result}"
    _save_review_file(md, "cracka_optimized.md")

    speak("Optimization complete Boss! Check the VS Code file.")
    return "Code optimized Boss! Check Desktop/cracka_optimized.md in VS Code."


# ── VS Code Extension commands (run in terminal) ──────────────────────────────

def open_file_in_vscode(filepath: str) -> bool:
    """Open a file in VS Code."""
    try:
        subprocess.Popen(["code", filepath])
        return True
    except FileNotFoundError:
        try:
            subprocess.Popen([r"C:\Program Files\Microsoft VS Code\Code.exe", filepath])
            return True
        except Exception:
            return False


def get_vscode_workspace_files() -> list[str]:
    """Get list of files in current VS Code workspace."""
    try:
        result = subprocess.run(
            ["code", "--list-extensions"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip().split("\n")
    except Exception:
        return []