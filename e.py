import os

def print_tree(path, prefix=""):
    entries = sorted(
        os.scandir(path),
        key=lambda e: (not e.is_dir(), e.name.lower())
    )

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "

        name = entry.name + ("/" if entry.is_dir() else "")
        print(prefix + connector + name)

        if entry.is_dir():
            extension = "    " if is_last else "│   "
            print_tree(entry.path, prefix + extension)


def main():
    root = os.getcwd()
    print(os.path.basename(root) + "/")
    print_tree(root)


if __name__ == "__main__":
    main()
