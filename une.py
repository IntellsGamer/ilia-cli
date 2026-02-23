import os
import sys
import re
import stat

DRY_RUN = "--dry-run" in sys.argv

def depth_of(line):
    return (len(line) - len(line.lstrip())) // 4

def clean_name(line):
    return re.sub(r"[│├└─]+", "", line).strip()

def parse_permissions(line):
    m = re.search(r"\[perm:\s*(\d+)\]", line)
    return int(m.group(1), 8) if m else None

def recreate(tree_lines):
    stack = []
    i = 0

    root = tree_lines[0].strip().rstrip("/")
    stack.append(os.path.abspath(root))

    if not DRY_RUN:
        os.makedirs(stack[0], exist_ok=True)
    else:
        print(f"[DRY] mkdir {stack[0]}")

    i = 1
    while i < len(tree_lines):
        line = tree_lines[i].rstrip("\n")

        if not line.strip():
            i += 1
            continue

        depth = depth_of(line)
        name = clean_name(line)
        stack = stack[: depth + 1]
        base = stack[-1]

        # ---- Symlink ----
        if "->" in name:
            src, target = map(str.strip, name.split("->"))
            path = os.path.join(base, src)

            if DRY_RUN:
                print(f"[DRY] symlink {path} -> {target}")
            else:
                os.symlink(target, path)

            i += 1
            continue

        # ---- Directory ----
        if name.endswith("/"):
            path = os.path.join(base, name.rstrip("/"))
            stack.append(path)

            if DRY_RUN:
                print(f"[DRY] mkdir {path}")
            else:
                os.makedirs(path, exist_ok=True)

            i += 1
            continue

        # ---- File ----
        path = os.path.join(base, name)
        content = ""
        perm = None
        i += 1

        # ---- Inline content ----
        if i < len(tree_lines) and tree_lines[i].lstrip().startswith("```"):
            lang = tree_lines[i]
            i += 1
            while i < len(tree_lines) and not tree_lines[i].lstrip().startswith("```"):
                content += tree_lines[i]
                i += 1
            i += 1  # skip closing ```

        # ---- Permissions ----
        if i < len(tree_lines) and "[perm:" in tree_lines[i]:
            perm = parse_permissions(tree_lines[i])
            i += 1

        if DRY_RUN:
            print(f"[DRY] file {path}")
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            if perm:
                os.chmod(path, perm)

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  py reverse_tree.py tree.txt [--dry-run]")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        lines = f.readlines()

    recreate(lines)

    if DRY_RUN:
        print("\nDry-run completed. No changes were made.")
    else:
        print("\nStructure recreated successfully.")

if __name__ == "__main__":
    main()
