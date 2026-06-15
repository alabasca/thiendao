import re, glob

for f in sorted(glob.glob("**/*.py", recursive=True)):
    with open(f, encoding="utf-8") as fh:
        lines = fh.readlines()
    for i, line in enumerate(lines):
        if "app_commands.command" in line or "bot.tree.command" in line:
            block = "".join(lines[i:i+4])
            name = re.search(r'name=["\'](\w+)["\']', block)
            desc = re.search(r'description=["\']([^"\']+)["\']', block)
            print(f"{f:<45}  /{(name.group(1) if name else '?'):<22} {(desc.group(1)[:60] if desc else '')}")
