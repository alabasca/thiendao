import re, glob

for f in sorted(glob.glob("**/*.py", recursive=True)):
    with open(f, encoding="utf-8") as fh:
        lines = fh.readlines()
    for i, line in enumerate(lines):
        m = re.search(r"@(\w+)_group\.command", line)
        if m:
            block = "".join(lines[i:i+4])
            name = re.search(r"name=[\"'](\w+)[\"']", block)
            desc = re.search(r"description=[\"']([^\"']+)[\"']", block)
            group = m.group(1)
            print(f"{f}:{i+1}  /{group} {name.group(1) if name else '?'}  --  {desc.group(1)[:60] if desc else ''}")
