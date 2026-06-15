"""
Fix script: thay thế tất cả bare `except Exception: pass` bằng log.exception()
Chạy: python _fix_exceptions.py
"""
import re
import os
import glob
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))

# Module name sẽ dùng cho getLogger nếu file chưa có log
LOGGER_NAME_MAP = {
    "cogs/give.py": "give",
    "cogs/cong_phap.py": "cong_phap",
    "bot.py": "bot",
}

# Mẫu log fix message - dùng tên file làm context
def make_log_msg(filepath):
    name = os.path.basename(filepath).replace(".py", "")
    return f"Lỗi {name}"

def fix_file(filepath):
    rel = filepath.replace(ROOT + os.sep, "").replace("\\", "/")
    with open(filepath, encoding="utf-8") as f:
        original = f.read()

    content = original

    # ── Bước 1: Thêm logging import nếu file chưa có ──────────────────────────
    needs_logging_import = (
        "import logging" not in content
        and rel in LOGGER_NAME_MAP
    )
    if needs_logging_import:
        logger_name = LOGGER_NAME_MAP[rel]
        # Chèn sau dòng import đầu tiên
        # Tìm dòng import đầu tiên hoặc dòng đầu tiên không phải docstring/blank
        first_import_match = re.search(r'^(import |from )', content, re.MULTILINE)
        if first_import_match:
            insert_pos = first_import_match.start()
            logging_block = f"import logging\nlog = logging.getLogger(\"{logger_name}\")\n"
            content = content[:insert_pos] + logging_block + content[insert_pos:]
        print(f"  [+] Thêm logging import vào {rel}")

    # ── Bước 2: Đếm trước để báo cáo ─────────────────────────────────────────
    initial = content

    msg = make_log_msg(filepath)
    changes = 0

    # Pattern A: multiline với pass trên dòng riêng
    # except Exception:\n    pass
    # except Exception as e:\n    pass  (biến e bị bỏ qua)
    # Bảo toàn indentation của except
    def replace_multiline_pass(m):
        nonlocal changes
        indent = m.group(1)   # indentation của 'except'
        body_indent = m.group(2)  # indentation của body (thường = indent + 4 spaces)
        # Chỉ thay nếu không có comment trên cùng dòng với except
        changes += 1
        return f"{indent}except Exception:\n{body_indent}log.exception(\"{msg}\")"

    content = re.sub(
        r'^([ \t]*)except Exception(?:\s+as\s+\w+)?:\s*\n([ \t]+)pass\b[ \t]*$',
        replace_multiline_pass,
        content,
        flags=re.MULTILINE
    )

    # Pattern B: inline  except Exception: pass
    def replace_inline_pass(m):
        nonlocal changes
        indent = m.group(1)
        changes += 1
        return f"{indent}except Exception:\n{indent}    log.exception(\"{msg}\")"

    content = re.sub(
        r'^([ \t]*)except Exception(?:\s+as\s+\w+)?:\s+pass\b[ \t]*$',
        replace_inline_pass,
        content,
        flags=re.MULTILINE
    )

    # Pattern C: multiline với return None / return {} trên dòng riêng (không có log trước đó)
    # except Exception:\n    return None   →  except Exception:\n    log.exception(msg)\n    return None
    # Chỉ thêm log, không xóa return (an toàn hơn)
    def replace_bare_return(m):
        nonlocal changes
        indent = m.group(1)
        body_indent = m.group(2)
        return_stmt = m.group(3)
        changes += 1
        return f"{indent}except Exception:\n{body_indent}log.exception(\"{msg}\")\n{body_indent}{return_stmt}"

    content = re.sub(
        r'^([ \t]*)except Exception(?:\s+as\s+\w+)?:\s*\n([ \t]+)(return(?:\s+None|\s+\{\}|\s+\[\])?)[ \t]*$',
        replace_bare_return,
        content,
        flags=re.MULTILINE
    )

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  [✓] {rel}: {changes} thay đổi")
        return changes
    else:
        return 0

def main():
    print(f"=== Fix exceptions script — {datetime.now().strftime('%H:%M:%S')} ===\n")
    py_files = glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True)
    # Bỏ qua chính script này
    py_files = [f for f in py_files if "_fix_exceptions" not in f]

    total = 0
    for fp in sorted(py_files):
        n = fix_file(fp)
        total += n

    print(f"\n=== Hoàn tất: {total} blocks đã được sửa ===")

if __name__ == "__main__":
    main()
