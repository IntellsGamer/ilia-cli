#!/usr/bin/env python3
"""
APD - Advanced Project Deployer
Version: 3.1.0
"""
__version__ = "3.1.0"
import threading
import urllib.request
import urllib.error
import ssl
import os
import sys
import json
import shutil
import subprocess
import platform
import time
import hashlib
import zipfile
import tarfile
import textwrap
import re
import shlex
import tempfile
import fnmatch
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import configparser
from datetime import datetime
import getpass
import socket
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, font
import threading
import queue
import json

class TemplateManifest:
    """Template manifest for framework/command configuration"""
    
    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.manifest_file = template_dir / "manifest.json"
        self.data = self.load_manifest()
    
    def load_manifest(self) -> Dict[str, Any]:
        """Load manifest from file or create default"""
        default_manifest = {
            "name": self.template_dir.name,
            "version": "1.0.0",
            "description": f"{self.template_dir.name} template",
            "type": "framework",  # or "files", "commands"
            "framework": self.detect_framework(),
            "variables": self.extract_template_variables(),
            "commands": {
                "pre_copy": [],  # Commands to run before copying files
                "post_copy": [],  # Commands to run after copying files
                "setup": []       # Setup commands after project creation
            },
            "dependencies": {
                "python": [],
                "node": [],
                "system": []
            },
            "required_files": self.get_required_files(),
            "ignore_patterns": [".git", "__pycache__", "*.pyc", ".DS_Store"],
            "metadata": {
                "author": "Unknown",
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat()
            }
        }
        
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r') as f:
                    user_manifest = json.load(f)
                    # Merge with defaults
                    default_manifest.update(user_manifest)
            except:
                pass
        
        return default_manifest
    
    def detect_framework(self) -> str:
        """Detect framework type"""
        framework_indicators = {
            "flask": ["app.py", "requirements.txt", "flask"],
            "django": ["manage.py", "settings.py", "django"],
            "react": ["package.json", "src/", "node_modules/"],
            "vue": ["vue.config.js", "package.json"],
            "angular": ["angular.json", "package.json"],
            "html": ["index.html", "style.css", "script.js"],
            "rust": ["Cargo.toml", "Cargo.lock"],
            "go": ["go.mod", "go.sum", "main.go"]
        }
        
        for framework, indicators in framework_indicators.items():
            for indicator in indicators:
                if '*' in indicator:
                    # Handle wildcards
                    if list(self.template_dir.glob(indicator)):
                        return framework
                elif (self.template_dir / indicator).exists():
                    return framework
        
        return "custom"
    
    def extract_template_variables(self) -> List[Dict[str, str]]:
        """Extract template variables from files"""
        variables = []
        common_vars = [
            {"name": "project_name", "description": "Project name", "default": "", "required": True},
            {"name": "author", "description": "Author name", "default": getpass.getuser(), "required": False},
            {"name": "version", "description": "Project version", "default": "1.0.0", "required": False},
            {"name": "description", "description": "Project description", "default": "", "required": False},
            {"name": "license", "description": "Project license", "default": "MIT", "required": False}
        ]
        
        # Scan files for {{ variable }} patterns
        for file_path in self.template_dir.rglob("*.py"):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    import re
                    matches = re.findall(r'\{\{\s*(\w+)\s*\}\}', content)
                    for match in matches:
                        if match not in [v['name'] for v in variables + common_vars]:
                            variables.append({
                                "name": match,
                                "description": f"Custom variable: {match}",
                                "default": "",
                                "required": False
                            })
            except:
                pass
        
        return common_vars + variables
    
    def get_required_files(self) -> List[str]:
        """Get list of required files for this template"""
        required = []
        
        # Check for common essential files
        common_essential = ["README.md", "requirements.txt", "package.json", 
                          "app.py", "main.py", "index.html", "setup.py"]
        
        for file in common_essential:
            if (self.template_dir / file).exists():
                required.append(file)
        
        return required
    
    def save(self):
        """Save manifest to file"""
        with open(self.manifest_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate template structure"""
        errors = []
        
        # Check required files
        for file in self.data.get("required_files", []):
            if not (self.template_dir / file).exists():
                errors.append(f"Required file missing: {file}")
        
        # Check for framework-specific requirements
        framework = self.data.get("framework", "")
        if framework == "flask":
            if not (self.template_dir / "app.py").exists():
                errors.append("Flask template should have app.py")
        
        return len(errors) == 0, errors

class ILIACLI:
    """Main CLI class for apd project deployer"""
    
    def __init__(self):
        self.app_name = "APD"
        self.version = "3.0.0"
        self._configure_console()
        self.config_dir = self.get_config_dir()
        self.config_file = self.config_dir / "config.ini"
        self.templates_dir = self.config_dir / "templates"
        self.projects_dir = self.config_dir / "projects"
        self.logs_dir = self.config_dir / "logs"
        self.template_manifests = {}
        self.ensure_directories()
        self.config = self.load_config()
        self.session_id = self.generate_session_id()
        self._gui_app = None
        self._aliases = self._load_aliases()

    def _configure_console(self):
        """Make terminal output consistent across platforms."""
        if os.name == "nt":
            # Enable ANSI escape sequences on modern Windows terminals.
            os.system("")

        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    def _terminal_width(self, minimum: int = 60, maximum: int = 120) -> int:
        width = shutil.get_terminal_size((80, 24)).columns
        return max(minimum, min(width, maximum))

    def _supports_ansi(self) -> bool:
        return bool(getattr(sys.stdout, "isatty", lambda: False)())

    def _style(self, text: str, color: str = "", bold: bool = False, dim: bool = False) -> str:
        if not self._supports_ansi():
            return text

        codes = []
        if bold:
            codes.append("1")
        if dim:
            codes.append("2")
        if color:
            codes.append(color)

        if not codes:
            return text
        return f"\033[{';'.join(codes)}m{text}\033[0m"

    def _divider(self, char: str = "─") -> str:
        width = self._terminal_width()
        if not self._supports_ansi() and char == "─":
            char = "-"
        return char * width

    def _print_title(self, title: str, subtitle: str = ""):
        print()
        print(self._style(title, color="36", bold=True))
        if subtitle:
            print(self._style(subtitle, color="37", dim=True))
        print(self._style(self._divider(), color="90"))

    def _print_section(self, title: str):
        print()
        print(self._style(title, color="33", bold=True))

    def _render_pairs(self, pairs: List[Tuple[str, str]]):
        width = self._terminal_width()
        key_width = min(24, max(14, int(width * 0.28)))
        value_width = max(20, width - key_width - 4)

        for key, value in pairs:
            wrapped = textwrap.wrap(str(value), width=value_width) or [""]
            print(f"  {self._style((key + ':').ljust(key_width), color='90')}{wrapped[0]}")
            for line in wrapped[1:]:
                print(" " * (key_width + 2) + line)

    def _badge(self, ok: bool, good: str = "Enabled", bad: str = "Disabled") -> str:
        if ok:
            return self._style(good, color="32", bold=True)
        return self._style(bad, color="31", bold=True)

    def _supports_unicode(self) -> bool:
        encoding = (getattr(sys.stdout, "encoding", None) or "utf-8").lower()
        return "utf" in encoding or "unicode" in encoding

    def _truncate(self, text: str, width: int) -> str:
        text = str(text)
        if width <= 1:
            return text[:width]
        if len(text) <= width:
            return text
        return text[: max(1, width - 1)] + "…"

    def _panel(self, title: str, lines: List[str], tone: str = "info"):
        width = self._terminal_width()
        content_width = max(20, width - 4)

        if self._supports_unicode():
            h, tl, tr, bl, br, v = "─", "┌", "┐", "└", "┘", "│"
        else:
            h, tl, tr, bl, br, v = "-", "+", "+", "+", "+", "|"

        tone_color = {"info": "36", "ok": "32", "warn": "33", "error": "31"}.get(tone, "36")
        title_text = f" {title} "
        rule = (title_text + (h * max(0, content_width - len(title_text))))[:content_width]

        print(self._style(f"{tl}{rule}{tr}", color=tone_color))
        for line in lines:
            wrapped = textwrap.wrap(str(line), width=content_width) or [""]
            for item in wrapped:
                print(self._style(v, color=tone_color) + item.ljust(content_width) + self._style(v, color=tone_color))
        print(self._style(f"{bl}{h * content_width}{br}", color=tone_color))

    def _render_table(self, headers: List[str], rows: List[List[str]]):
        if not rows:
            return

        width = self._terminal_width()
        cols = len(headers)
        base = max(10, (width - (3 * cols) - 1) // cols)
        col_widths = [base for _ in headers]

        for i, header in enumerate(headers):
            col_widths[i] = max(col_widths[i], min(28, len(str(header)) + 2))

        total = sum(col_widths) + (3 * cols) + 1
        while total > width and any(w > 10 for w in col_widths):
            idx = max(range(cols), key=lambda k: col_widths[k])
            if col_widths[idx] > 10:
                col_widths[idx] -= 1
                total -= 1

        def render_row(cells: List[str], header: bool = False):
            parts = []
            for i, cell in enumerate(cells):
                cell_text = self._truncate(str(cell), col_widths[i]).ljust(col_widths[i])
                color = "36" if header else "37"
                style = self._style(cell_text, color=color, bold=header)
                parts.append(style)
            print(" " + " | ".join(parts))

        sep = "-" * max(20, min(width, sum(col_widths) + (3 * cols) - 1))
        print(self._style(sep, color="90"))
        render_row(headers, header=True)
        print(self._style(sep, color="90"))
        for row in rows:
            render_row(row)
        print(self._style(sep, color="90"))

    def _render_step(self, step: int, total: int, label: str):
        width = max(10, min(24, self._terminal_width() // 4))
        filled = int((step / max(1, total)) * width)
        bar = ("#" * filled) + ("-" * (width - filled))
        print()
        print(self._style(f"[{bar}] Step {step}/{total}", color="35", bold=True))
        print(self._style(label, color="37"))

    def _ask_yes_no(self, prompt: str, default: bool = False) -> bool:
        suffix = "Y/n" if default else "y/N"
        answer = input(f"{prompt} ({suffix}): ").strip().lower()
        if not answer:
            return default
        return answer in ("y", "yes")
        
    def get_template_manifest(self, template_name: str) -> Optional[TemplateManifest]:
        """Get template manifest"""
        template_path = self.templates_dir / template_name
        if template_path.exists():
            return TemplateManifest(template_path)
        return None

    def _load_projects_db(self) -> List[Dict[str, Any]]:
        """Load the projects registry."""
        projects_file = self.projects_dir / 'projects.json'
        if not projects_file.exists():
            return []

        try:
            with open(projects_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception as e:
            self.log_activity('error', f'Failed to load projects database: {e}')
        return []

    def _save_projects_db(self, projects: List[Dict[str, Any]]):
        """Persist the projects registry."""
        projects_file = self.projects_dir / 'projects.json'
        with open(projects_file, 'w', encoding='utf-8') as f:
            json.dump(projects, f, indent=2)

    def _find_project_index(self, project_name: str, projects: Optional[List[Dict[str, Any]]] = None) -> int:
        """Find a project index by name (case-insensitive)."""
        projects = projects if projects is not None else self._load_projects_db()
        for index, project in enumerate(projects):
            if project.get('name', '').lower() == project_name.lower():
                return index
        return -1

    def _parse_bool(self, value: Any) -> bool:
        """Parse a flexible boolean-like value."""
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'on', 'enabled'}

    def run(self, args):
        """Main CLI entry point."""
        if self.config['DEFAULT'].getboolean('first_run', True):
            self.first_run_setup()

        self.send_telemetry(
            "app_started",
            command=args[0] if args else None,
            args_count=len(args)
        )

        if len(args) == 0 or args[0] in ['-h', '--help', 'help']:
            if len(args) > 1 and args[1] in ['templates', 'template']:
                self.show_template_help(args[2] if len(args) > 2 else None)
            else:
                self.show_help()
            return

        # Resolve aliases
        original_command = args[0]
        resolved_command = self._resolve_alias(original_command)
        if resolved_command != original_command:
            # Split resolved command into args
            resolved_parts = resolved_command.split()
            args = resolved_parts + args[1:]
            self.log_activity('debug', f'Alias resolved: {original_command} -> {resolved_command}')
            print(f"🔗 Alias: {original_command} -> {resolved_command}")
        else:
            # Also try to resolve the full command string for multi-word aliases
            full_command = ' '.join(args)
            resolved_full = self._resolve_alias(full_command)
            if resolved_full != full_command:
                args = resolved_full.split()
                self.log_activity('debug', f'Alias resolved: {full_command} -> {resolved_full}')
                print(f"🔗 Alias: {full_command} -> {resolved_full}")

        command = args[0]

    def _coerce_config_value(self, value: str) -> str:
        """Normalize values before storing them in config.ini."""
        normalized = value.strip()
        if normalized.lower() in {'true', 'false'}:
            return normalized.lower()
        return normalized

    def _resolve_config_key(self, dotted_key: str) -> Tuple[Optional[str], Optional[str]]:
        """Resolve SECTION.key references, defaulting to DEFAULT."""
        if not dotted_key:
            return None, None

        if '.' in dotted_key:
            section, option = dotted_key.split('.', 1)
        else:
            section, option = 'DEFAULT', dotted_key

        section = section.strip().upper()
        option = option.strip()
        if not option:
            return None, None

        if section not in self.config and section != 'DEFAULT':
            return None, None

        return section, option

    def _get_config_value(self, dotted_key: str) -> Optional[str]:
        """Get a config value using SECTION.key notation."""
        section, option = self._resolve_config_key(dotted_key)
        if not section or not option:
            return None

        if section == 'DEFAULT':
            return self.config['DEFAULT'].get(option)
        return self.config[section].get(option)

    def _set_config_value(self, dotted_key: str, value: str) -> bool:
        """Set a config value using SECTION.key notation."""
        section, option = self._resolve_config_key(dotted_key)
        if not section or not option:
            return False

        target = self.config['DEFAULT'] if section == 'DEFAULT' else self.config[section]
        target[option] = self._coerce_config_value(value)
        return True

    def _template_text_extensions(self) -> set:
        """Extensions treated as text when processing template variables."""
        return {
            '.py', '.txt', '.md', '.rst', '.json', '.toml', '.yaml', '.yml', '.ini',
            '.cfg', '.env', '.gitignore', '.html', '.htm', '.css', '.scss', '.sass',
            '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.xml', '.svg', '.sql',
            '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd', '.java', '.kt', '.go',
            '.rs', '.c', '.cpp', '.h', '.hpp', '.php', '.rb', '.pl', '.cs'
        }

    def _is_probably_text_file(self, file_path: Path) -> bool:
        """Best-effort text file detection for variable processing."""
        if file_path.suffix.lower() in self._template_text_extensions():
            return True

        try:
            with open(file_path, 'rb') as f:
                sample = f.read(4096)
            if b'\x00' in sample:
                return False
            if not sample:
                return True
            sample.decode('utf-8')
            return True
        except Exception:
            return False

    def _extract_placeholders(self, content: str) -> List[str]:
        """Extract template placeholders from a string."""
        return re.findall(r'\{\{\s*(\w+)\s*\}\}', content)

    def _collect_template_variables(self, template_dir: Path) -> List[Dict[str, Any]]:
        """Collect variables referenced by template content and file paths."""
        discovered = {}
        manifest = self.get_template_manifest(template_dir.name)
        existing_names = set()
        if manifest:
            for item in manifest.data.get('variables', []):
                name = item.get('name')
                if name:
                    existing_names.add(name)

        for path in template_dir.rglob('*'):
            relative = str(path.relative_to(template_dir))
            for match in self._extract_placeholders(relative):
                if match not in existing_names:
                    discovered.setdefault(match, {
                        "name": match,
                        "description": f"Path variable: {match}",
                        "default": "",
                        "required": False,
                    })

            if path.is_file() and self._is_probably_text_file(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception:
                    continue

                for match in self._extract_placeholders(content):
                    if match not in existing_names:
                        discovered.setdefault(match, {
                            "name": match,
                            "description": f"Template variable: {match}",
                            "default": "",
                            "required": False,
                        })

        preferred_order = ['project_name', 'author', 'version', 'description', 'license']
        ordered = []
        for name in preferred_order:
            if name in discovered:
                ordered.append(discovered.pop(name))
        ordered.extend(sorted(discovered.values(), key=lambda item: item['name'].lower()))
        return ordered

    def _sanitize_template_name(self, name: str) -> str:
        """Normalize user-provided template names."""
        cleaned = re.sub(r'[^A-Za-z0-9._-]+', '-', name.strip().strip(". "))
        cleaned = re.sub(r'-{2,}', '-', cleaned).strip('-')
        return cleaned

    def _sanitize_project_name(self, name: str) -> str:
        """Normalize user-provided project names."""
        cleaned = re.sub(r'[^A-Za-z0-9_-]+', '-', name.strip())
        cleaned = re.sub(r'-{2,}', '-', cleaned)
        if cleaned and not cleaned[0].isalpha():
            cleaned = f"project-{cleaned}"
        return cleaned[:50].strip('-')

    def _safe_relative_archive_path(self, member_name: str) -> Optional[Path]:
        """Validate archive members and return a safe relative path."""
        normalized = member_name.replace('\\', '/').strip()
        if not normalized or normalized.endswith('/'):
            normalized = normalized.rstrip('/')
        if not normalized:
            return None

        candidate = Path(normalized)
        if candidate.is_absolute():
            raise ValueError(f"Archive contains absolute path: {member_name}")
        if '..' in candidate.parts:
            raise ValueError(f"Archive contains unsafe path traversal: {member_name}")

        return candidate

    def _safe_extract_archive(self, archive_path: Path, temp_extract_dir: Path, ext: str) -> List[str]:
        """Safely extract ZIP/TAR archives into a temporary directory."""
        extracted_files = []

        if ext == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                for info in zip_ref.infolist():
                    relative = self._safe_relative_archive_path(info.filename)
                    if relative is None:
                        continue
                    target_path = temp_extract_dir / relative
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    if info.is_dir():
                        target_path.mkdir(parents=True, exist_ok=True)
                    else:
                        with zip_ref.open(info, 'r') as src, open(target_path, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                    extracted_files.append(str(relative))

        elif ext in ['.tar.gz', '.tgz', '.tar']:
            mode = 'r:gz' if ext in ['.tar.gz', '.tgz'] else 'r'
            with tarfile.open(archive_path, mode) as tar_ref:
                for member in tar_ref.getmembers():
                    relative = self._safe_relative_archive_path(member.name)
                    if relative is None:
                        continue
                    if member.issym() or member.islnk():
                        raise ValueError(f"Archive contains links, which are not allowed: {member.name}")
                    target_path = temp_extract_dir / relative
                    if member.isdir():
                        target_path.mkdir(parents=True, exist_ok=True)
                    else:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        src = tar_ref.extractfile(member)
                        if src is None:
                            continue
                        with src, open(target_path, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                    extracted_files.append(str(relative))
        else:
            raise ValueError(f"Unsupported archive type: {ext}")

        return extracted_files

    def _resolve_extracted_root(self, extract_dir: Path, template_name: str) -> Path:
        """Pick the most useful directory from an extracted archive."""
        extracted_items = [item for item in extract_dir.iterdir() if item.name != '__MACOSX']
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            inner_dir = extracted_items[0]
            inner_name = inner_dir.name.lower()
            template_name_lower = template_name.lower()
            if (
                inner_name == template_name_lower
                or inner_name in {'template', 'templates', 'src', 'app', 'project'}
                or inner_name.startswith(template_name_lower)
            ):
                return inner_dir
        return extract_dir

    def _print_template_tree(self, template_dir: Path, max_depth: int = 3):
        """Show a concise tree preview for a template."""
        print(f"\nTemplate tree for {template_dir.name}:")
        self._show_template_structure(template_dir, max_depth=max_depth)

    def _build_template_variable_map(
        self,
        manifest: TemplateManifest,
        project_name: str,
        cli_variables: Optional[Dict[str, str]] = None,
        interactive: bool = True,
    ) -> Dict[str, Any]:
        """Build the final variable map used for templating."""
        cli_variables = cli_variables or {}
        variables = {}

        for var_info in manifest.data.get('variables', []):
            name = var_info.get('name')
            if not name:
                continue

            if name == 'project_name':
                value = project_name
            elif name in cli_variables:
                value = cli_variables[name]
            else:
                default = var_info.get('default', '')
                if interactive:
                    if var_info.get('required', False) and not default:
                        value = input(f"{var_info['description']}: ").strip()
                        while not value:
                            print(f"❌ {name} is required!")
                            value = input(f"{var_info['description']}: ").strip()
                    else:
                        value = input(f"{var_info['description']} [{default}]: ").strip()
                        if not value and default != "":
                            value = default
                else:
                    value = default
                    if var_info.get('required', False) and value in ("", None):
                        raise ValueError(
                            f"Missing required template variable '{name}'. "
                            f"Provide it with --var {name}=value or run interactively."
                        )

            variables[name] = value

        variables['project_name'] = project_name
        variables.setdefault('year', str(datetime.now().year))
        variables.setdefault('author', self.config['PROJECT']['author'])
        variables.setdefault('email', self.config['PROJECT']['email'])
        variables.setdefault('version', '1.0.0')
        variables.setdefault('date', datetime.now().strftime('%Y-%m-%d'))
        variables.setdefault('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        variables.setdefault('license', self.config['PROJECT']['license'])
        variables.setdefault('description', '')

        return variables

    def _apply_template_variables(self, project_dir: Path, variables: Dict[str, Any]):
        """Apply variable replacements to file contents and matching path names."""
        for file_path in project_dir.rglob('*'):
            if file_path.is_file() and self._is_probably_text_file(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    updated = content
                    for var_name, var_value in variables.items():
                        updated = re.sub(
                            rf'\{{\{{\s*{re.escape(var_name)}\s*\}}\}}',
                            str(var_value),
                            updated,
                        )
                    if updated != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(updated)
                except Exception:
                    continue

        rename_candidates = sorted(project_dir.rglob('*'), key=lambda p: len(p.parts), reverse=True)
        for path in rename_candidates:
            new_name = path.name
            for var_name, var_value in variables.items():
                new_name = re.sub(
                    rf'\{{\{{\s*{re.escape(var_name)}\s*\}}\}}',
                    str(var_value),
                    new_name,
                )
            if new_name != path.name:
                target = path.with_name(new_name)
                if target.exists():
                    raise FileExistsError(f"Cannot rename '{path.name}' to '{new_name}': target already exists")
                path.rename(target)

    def _archive_output_dir(self) -> Path:
        """Return the archive output directory and ensure it exists."""
        archive_dir = self.projects_dir / 'archives'
        archive_dir.mkdir(parents=True, exist_ok=True)
        return archive_dir

    def _template_copy_ignore(self, directory: str, names: List[str]):
        """Ignore bulky/generated directories when capturing templates."""
        patterns = {
            '.git', '.hg', '.svn', '__pycache__', '.pytest_cache', '.mypy_cache',
            '.ruff_cache', '.tox', '.venv', 'venv', 'env', 'node_modules',
            'dist', 'build', '.idea', '.vscode', '.DS_Store'
        }
        ignored = set()
        for name in names:
            if name in patterns:
                ignored.add(name)
                continue
            if fnmatch.fnmatch(name, '*.pyc') or fnmatch.fnmatch(name, '*.pyo'):
                ignored.add(name)
        return ignored

    def generate_template_docs(self, template_name: str):
        """Generate documentation for a template"""
        manifest = self.get_template_manifest(template_name)
        if not manifest:
            print(f"❌ Template '{template_name}' not found")
            return
        
        print(f"\n📋 Template: {template_name}")
        print("=" * 60)
        
        print(f"Name: {manifest.data['name']}")
        print(f"Version: {manifest.data['version']}")
        print(f"Type: {manifest.data['type']}")
        print(f"Framework: {manifest.data['framework']}")
        print(f"Description: {manifest.data['description']}")
        
        # Show variables
        if manifest.data['variables']:
            print("\n📝 Variables:")
            for var in manifest.data['variables']:
                required = " (required)" if var.get('required', False) else ""
                default = f" [default: {var['default']}]" if var.get('default') else ""
                print(f"  • {var['name']}: {var['description']}{required}{default}")
        
        # Show commands
        if any(manifest.data['commands'].values()):
            print("\n⚙️  Commands:")
            for cmd_type, cmds in manifest.data['commands'].items():
                if cmds:
                    print(f"  {cmd_type}:")
                    for cmd in cmds:
                        print(f"    • {cmd}")
        
        # Show dependencies
        if any(manifest.data['dependencies'].values()):
            print("\n📦 Dependencies:")
            for dep_type, deps in manifest.data['dependencies'].items():
                if deps:
                    print(f"  {dep_type}:")
                    for dep in deps:
                        print(f"    • {dep}")
        
        # Show help command usage
        print(f"\n💡 Usage: apd templates info {template_name}")

    def list_templates_with_details(self):
        """List all templates with manifest details"""
        self._print_title("Available Templates")
        
        templates = []
        for item in self.templates_dir.iterdir():
            if item.is_dir():
                manifest = TemplateManifest(item)
                templates.append(manifest.data)
        
        if not templates:
            self._panel(
                "No Templates Found",
                [
                    f"Template directory: {self.templates_dir}",
                    "Create one with: apd templates create <name>",
                    "Or import one with: apd templates import <url-or-file>",
                ],
                tone="warn",
            )
            return

        rows = []
        for template in sorted(templates, key=lambda t: t["name"].lower()):
            file_count = len(list((self.templates_dir / template['name']).rglob('*')))
            template_type = self.detect_template_type(self.templates_dir / template['name'])
            rows.append([
                template["name"],
                template["version"],
                f"{template['framework']} ({template_type})",
                template["type"],
                str(file_count),
            ])

        self._render_table(
            ["Template", "Version", "Framework", "Type", "Files"],
            rows
        )

        self._print_section("Quick Actions")
        print("  apd templates info <name>")
        print("  apd templates validate <name>")

    def create_template_from_current(self, template_name: str, is_framework: bool = False):
        """Create a template from current directory with manifest"""
        current_dir = Path.cwd()
        template_name = self._sanitize_template_name(template_name)
        if not template_name:
            print("❌ Template name required")
            return

        template_dst = self.templates_dir / template_name
        
        # Check if directory has files
        files = list(current_dir.rglob('*'))
        if not files:
            print("❌ Current directory is empty!")
            return
        
        if template_dst.exists():
            print(f"⚠️  Template '{template_name}' already exists!")
            choice = input("Overwrite? (y/N): ").strip().lower()
            if choice != 'y':
                return
            shutil.rmtree(template_dst)
        
        try:
            # Copy files
            print(f"📁 Copying from {current_dir} to {template_dst}")
            shutil.copytree(current_dir, template_dst, ignore=self._template_copy_ignore)
            
            # Verify the copy worked
            if not template_dst.exists():
                print(f"❌ Failed to copy template to {template_dst}")
                return
            
            print(f"✅ Template copied to: {template_dst}")
            
            # Create manifest
            manifest = TemplateManifest(template_dst)
            manifest.data['type'] = 'framework' if is_framework else 'files'
            manifest.data['description'] = input(f"Template description [{template_name} template]: ").strip() or f"{template_name} template"
            manifest.data['variables'] = self._collect_template_variables(template_dst) or manifest.data['variables']
            manifest.save()
            
            # Validate
            is_valid, errors = manifest.validate()
            if not is_valid:
                print("⚠️  Template validation warnings:")
                for error in errors:
                    print(f"  • {error}")
            
            print(f"✅ Template '{template_name}' created with manifest!")
            print(f"📁 Template location: {template_dst}")
            print(f"📋 View documentation: apd template info {template_name}")
            
            self.log_activity('info', f'Template created: {template_name}')
            
        except Exception as e:
            import traceback
            traceback.print_exc()            
            print(f"❌ Error creating template: {e}")

    def process_template_with_manifest(self, template_name: str, project_dir: Path, project_name: str):
        """Process template using manifest configuration"""
        print(f"🔍 Looking for template '{template_name}' in {self.templates_dir}")
        manifest = self.get_template_manifest(template_name)
        template_src = self.templates_dir / template_name
        
        print(f"🔍 Template source path: {template_src}")
        print(f"🔍 Template source exists: {template_src.exists()}")
        
        if not manifest:
            print(f"⚠️  No manifest found for {template_name}, using basic processing")
            if not template_src.exists():
                print(f"❌ Template source directory not found: {template_src}")
                return            
            shutil.copytree(template_src, project_dir, dirs_exist_ok=True)
            self.process_template_variables(project_dir, project_name)
            return
        
        print(f"📋 Processing {template_name} template...")
        
        # Run pre-copy commands
        self.run_template_commands(manifest.data['commands']['pre_copy'], project_dir)
        
        # Copy files with ignore patterns
        ignore_patterns = manifest.data.get('ignore_patterns', [])
        ignore = shutil.ignore_patterns(*ignore_patterns)
        
        print(f"📁 Copying from {template_src} to {project_dir}")
        
        # Check if source exists
        if not template_src.exists():
            print(f"❌ Template source not found: {template_src}")
            print(f"Available templates: {self.list_available_templates()}")
            return
        
        shutil.copytree(template_src, project_dir, ignore=ignore, dirs_exist_ok=True)
        print(f"✅ Files copied successfully")
        
        # Process variables
        variables = {}
        print("\n📝 Template Variables:")
        for var_info in manifest.data['variables']:
            if var_info.get('required', False) and not var_info.get('default'):
                value = input(f"{var_info['description']}: ").strip()
                while not value:
                    print(f"❌ {var_info['name']} is required!")
                    value = input(f"{var_info['description']}: ").strip()
            else:
                default = var_info.get('default', '')
                value = input(f"{var_info['description']} [{default}]: ").strip()
                if not value and default:
                    value = default
            
            variables[var_info['name']] = value
        
        # Special handling for project_name
        variables['project_name'] = project_name
        
        # Replace variables in files
        for file_path in project_dir.rglob('*'):
            if file_path.is_file():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for var_name, var_value in variables.items():
                        placeholder = f'{{{{ {var_name} }}}}'
                        content = content.replace(placeholder, str(var_value))
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                except:
                    pass
        
        # Run post-copy commands
        self.run_template_commands(manifest.data['commands']['post_copy'], project_dir)
        
        print("✅ Template processed with manifest")

    def run_template_commands(self, commands: List[str], project_dir: Path):
        """Run template commands"""
        # Allowed commands (expanded for better Windows support)
        ALLOWED_COMMANDS = [
            # External executables
            'npm', 'pip', 'python', 'git', 'node', 'npx',
            'powershell', 'cmd', 'bash', 'sh',
            
            # Windows shell built-ins (these work in cmd.exe)
            'echo', 'mkdir', 'rmdir', 'del', 'copy', 'xcopy', 'move',
            'cd', 'dir', 'type', 'find', 'findstr',
            
            # Unix shell built-ins  
            'ls', 'cp', 'mv', 'rm', 'cat', 'grep', 'sed', 'awk'
        ]
        
        for command in commands:
            print(f"⚙️  Running: {command}")
            try:
                # Replace variables in command
                command = command.replace('{{ project_dir }}', str(project_dir))
                
                # Basic command validation
                cmd_parts = command.strip().split()
                if not cmd_parts:
                    continue
                
                base_cmd = cmd_parts[0].lower()
                
                # Special handling for Windows shell built-ins
                if platform.system() == 'Windows':
                    # These are cmd.exe built-ins, always allow
                    windows_builtins = ['echo', 'mkdir', 'rmdir', 'del', 'copy', 'xcopy', 'move', 'cd', 'dir']
                    if base_cmd in windows_builtins:
                        # Run through cmd.exe
                        subprocess.run(command, shell=True, cwd=project_dir, check=True)
                        continue
                
                # Check if command is in allowed list
                if base_cmd not in ALLOWED_COMMANDS:
                    # Allow any .exe, .bat, .sh, .ps1 files
                    if not any(base_cmd.endswith(ext) for ext in ['.exe', '.bat', '.cmd', '.sh', '.ps1']):
                        print(f"⚠️  Skipping potentially unsafe command: {command}")
                        continue
                
                # Run the command
                if platform.system() == 'Windows':
                    # For Windows, use shell=True for built-ins, list form for others
                    if base_cmd in ['echo', 'mkdir', 'rmdir', 'cd', 'dir']:
                        subprocess.run(command, shell=True, cwd=project_dir, check=True)
                    else:
                        subprocess.run(cmd_parts, cwd=project_dir, check=True)
                else:
                    subprocess.run(cmd_parts, cwd=project_dir, check=True)
                    
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Command failed: {command}")
                print(f"Error: {e}")
            except FileNotFoundError:
                print(f"⚠️  Command not found: {cmd_parts[0] if cmd_parts else 'unknown'}")            

    def show_template_help(self, template_name: str = None):
        """Show help for templates or specific template"""
        if template_name:
            self.generate_template_docs(template_name)
        else:
            print("\n📚 Template Help")
            print("=" * 60)
            print("\n📁 Creating Templates:")
            print("  1. Create your project structure")
            print("  2. Add {{ variables }} in files")
            print("  3. Run: apd template create <name> [--framework]")
            print("  4. Add manifest.json for advanced configuration")
            
            print("\n📋 Manifest Structure (manifest.json):")
            print("""
    {
    "name": "template-name",
    "version": "1.0.0",
    "description": "Template description",
    "type": "framework",  // or "files"
    "framework": "flask", // auto-detected
    "variables": [
        {
        "name": "project_name",
        "description": "Project name",
        "default": "",
        "required": true
        }
    ],
    "commands": {
        "pre_copy": ["echo 'Running before copy'"],
        "post_copy": ["npm install", "pip install -r requirements.txt"],
        "setup": ["git init", "npm start"]
    },
    "dependencies": {
        "python": ["flask", "requests"],
        "node": ["react", "vue"],
        "system": ["docker", "git"]
    },
    "required_files": ["app.py", "requirements.txt"]
    }
    """)
            
            print("\n📝 Commands:")
            print("  apd template create <name> [--framework]  - Create template from current dir")
            print("  apd template list                         - List templates with details")
            print("  apd template info <name>                  - Show template details")
            print("  apd template validate <name>              - Validate template")
            print("  apd template edit <name>                  - Edit template manifest")
            print("  apd help templates                        - Show this help")
            
            print("\n💡 Example workflow:")
            print("  1. Create a Flask app")
            print("  2. Add {{ project_name }} in app.py")
            print("  3. Run: apd template create my-flask --framework")
            print("  4. Run: apd new myapp --template my-flask")
        
    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = str(int(time.time()))
        rand = str(os.getpid())
        return hashlib.md5(f"{timestamp}{rand}".encode()).hexdigest()[:8]
    
    def get_config_dir(self) -> Path:
        """Get platform-specific configuration directory"""
        system = platform.system()
        
        if system == "Windows":
            base_dir = Path(os.getenv('APPDATA', ''))
        elif system == "Darwin":  # macOS
            base_dir = Path.home() / "Library" / "Application Support"
        else:  # Linux and others
            base_dir = Path.home() / ".config"
            
        return base_dir / self.app_name
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.config_dir,
            self.templates_dir,
            self.projects_dir,
            self.logs_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
    def load_config(self) -> configparser.ConfigParser:
        """Load or create configuration"""
        config = configparser.ConfigParser()
        
        if self.config_file.exists():
            config.read(self.config_file)
        else:
            # Default configuration
            config['DEFAULT'] = {
                'version': self.version,
                'first_run': 'true',
                'auto_update': 'false',
                'telemetry': 'false',
                'log_level': 'info',
                'default_template': 'html',
                'editor': self.detect_default_editor(),
                'last_update_check': '0'
            }
            config['MIRROR'] = {
                'enabled': 'false',
                'url': 'https://mirror-pypi.runflare.com/simple',
                'trusted_host': 'mirror-pypi.runflare.com',
                'backup_url': 'https://pypi.org/simple'
            }
            config['PATHS'] = {
                'templates': str(self.templates_dir),
                'projects': str(self.projects_dir),
                'logs': str(self.logs_dir)
            }
            config['PROJECT'] = {
                'auto_git': 'false',
                'auto_open': 'false',
                'auto_venv': 'true',
                'license': 'MIT',
                'author': getpass.getuser(),
                'email': f"{getpass.getuser()}@localhost"
            }
            config['SECURITY'] = {
                'verify_ssl': 'true',
                'timeout': '30',
                'max_retries': '3'
            }
            config['TELEMETRY'] = {
                'url': 'https://example.com/tm/submit'
            }
            config['TEMPLATE_REPO'] = {
                'enabled': 'true',
                'owner': 'IntellsGamer',
                'repo': 'ilia-cli',
                'path': 'templates',
                'branch': 'main'
            }
            config['ALIASES'] = {
                # Default aliases - Core commands
                'c': 'new',
                'create': 'new',
                'n': 'new',
                
                # Project management
                'ls': 'projects',
                'list': 'projects',
                'p': 'projects',
                'rm': 'delete',
                'remove': 'delete',
                'del': 'delete',
                
                # Templates
                't': 'templates',
                'tmpl': 'templates',
                'template': 'templates',
                'cp': 'templates clone',
                'clone': 'templates clone',
                'import': 'templates import',
                'install': 'templates install',
                'export': 'templates export',
                'list-online': 'templates list --online',
                'lo': 'templates list --online',
                'search-online': 'templates search --online',
                'so': 'templates search --online',
                'preview': 'templates preview',
                'info': 'templates info',
                'validate': 'templates validate',
                'score': 'templates score',
                
                # System
                'doc': 'doctor',
                'fix': 'doctor --fix',
                'st': 'status',
                'status': 'status',
                'up': 'update',
                'update': 'update',
                'log': 'logs',
                'logs': 'logs',
                'clean': 'cleanup',
                'cleanup': 'cleanup',
                'un': 'uninstall',
                'uninstall': 'uninstall',
                
                # Config
                'cfg': 'config',
                'settings': 'config',
                'conf': 'config',
                
                # Project analysis
                'audit': 'audit-all',
                'audit-all': 'audit-all',
                'sbom': 'sbom',
                'graph': 'graph',
                'metrics': 'metrics',
                'plan': 'plan',
                'release': 'release',
                'snap': 'snapshot',
                'snapshot': 'snapshot',
                'restore': 'restore',
                'blueprint': 'blueprint',
                
                # Dev tools
                'env': 'env',
                'docker': 'dockerize',
                'dockerize': 'dockerize',
                'ci': 'ci',
                'test': 'test',
                'run': 'run',
                'onboard': 'onboard',
                'harden': 'harden',
                
                # Shortcuts for common operations
                'open': 'open',
                'o': 'open',
                'i': 'inspect',
                'inspect': 'inspect',
                'deps': 'deps',
                'scripts': 'scripts',
                'ports': 'ports',
                'env-check': 'env-check',
                'lock': 'lock',
                'verify': 'verify',
                'clean-project': 'clean-project',
                'scaffold-tests': 'scaffold-tests',
                'compare': 'compare',
                'rename': 'rename',
                'mv': 'rename',
                'archive': 'archive',
                'zip': 'archive'
            }
            
        return config
    
    def detect_default_editor(self) -> str:
        """Detect default code editor on system"""
        editors = [
            'code',      # VS Code
            'vim',       # Vim
            'nano',      # Nano
            'notepad',   # Notepad (Windows)
            'gedit',     # GEdit (Linux)
            'subl',      # Sublime Text
            'atom'       # Atom
        ]
        
        for editor in editors:
            if shutil.which(editor):
                return editor
        
        return 'notepad' if platform.system() == 'Windows' else 'vim'
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            self.config.write(f)
    
    def log_activity(self, level: str, message: str):
        """Log activity to file"""
        if level not in ['debug', 'info', 'warning', 'error']:
            level = 'info'
            
        log_level = self.config['DEFAULT'].get('log_level', 'info')
        levels = {'debug': 0, 'info': 1, 'warning': 2, 'error': 3}
        
        if levels.get(level, 1) < levels.get(log_level, 1):
            return
            
        log_file = self.logs_dir / f"apd_{datetime.now().strftime('%Y%m')}.log"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level.upper()}] [{self.session_id}] {message}\n"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except:
            pass  # Silent fail for logging errors
        
    def send_telemetry(self, event_name: str, **kwargs):
        """Send anonymous telemetry if enabled"""
        if not self.config['DEFAULT'].getboolean('telemetry', False):
            return
        
        telemetry_url = self.config.get('TELEMETRY', {}).get('url', '')
        if not telemetry_url:
            # Development default - should be overridden in production
            telemetry_url = "https://example.com/tm/submit"
               
        # Prepare telemetry data
        telemetry_data = {
            "event": event_name,
            "apd_version": self.version,
            "python_version": platform.python_version().split('.')[0] + '.' + platform.python_version().split('.')[1],  # Major.minor only
            "platform": platform.system(),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "mirror_enabled": self.config['MIRROR'].getboolean('enabled', False),
            "auto_venv": self.config['PROJECT'].getboolean('auto_venv', True),
            "auto_git": self.config['PROJECT'].getboolean('auto_git', False)
        }
        
        # Add event-specific data
        telemetry_data.update(kwargs)
        
        # Remove any None values
        telemetry_data = {k: v for k, v in telemetry_data.items() if v is not None}
        
        # Send in background thread (silent, no output)
        def send_async():
            try:
                # Prepare request
                url = telemetry_url
                data = json.dumps(telemetry_data).encode('utf-8')
                
                # Create request with timeout
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': f'APD/{self.version}'
                    },
                    method='POST'
                )
                
                # Send request (silent - no output regardless of success/failure)
                context = ssl.create_default_context()
                # if not self.config['SECURITY'].getboolean('verify_ssl', True):
                #     context.check_hostname = False
                #     context.verify_mode = ssl.CERT_NONE
                
                with urllib.request.urlopen(
                    req, 
                    timeout=int(self.config['SECURITY'].get('timeout', '30')),
                    context=context
                ) as response:
                    # Success - but silent (no output)
                    pass
                    
            except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout, ConnectionError):
                # Failure - but silent (no output)
                pass
            except Exception:
                # Any other error - but silent (no output)
                pass
        
        # Start async thread
        thread = threading.Thread(target=send_async, daemon=True)
        thread.start()
        
        # Log locally for debugging (optional)
        self.log_activity('debug', f'Telemetry sent: {event_name}')
    
    def check_internet(self) -> bool:
        """Check internet connectivity"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False
    
    def first_run_setup(self):
        """First-time setup wizard"""
        self._print_title(f"Welcome to {self.app_name} v{self.version}", "First-time setup wizard")
        self._panel(
            "Setup Overview",
            [
                "This guided setup configures mirrors, telemetry, updates, editor, and project defaults.",
                "Press Enter to accept default choices shown in each prompt.",
            ],
            tone="info",
        )

        total_steps = 5

        self._render_step(1, total_steps, "Configure national PyPI mirror")
        print("Mirror URL: https://mirror-pypi.runflare.com/simple")
        enable_mirror = self._ask_yes_no("Enable national PyPI mirror", default=False)
        if enable_mirror:
            self.config['MIRROR']['enabled'] = 'true'
            print(self._style("Mirror enabled", color="32"))
            if self.check_internet():
                print("Testing mirror connectivity...")
                if self.test_mirror():
                    print(self._style("Mirror is accessible", color="32"))
                else:
                    print(self._style("Mirror may be temporarily unavailable", color="33"))
        else:
            self.config['MIRROR']['enabled'] = 'false'
            print(self._style("Mirror disabled", color="31"))

        self._render_step(2, total_steps, "Telemetry and update behavior")
        telemetry_enabled = self._ask_yes_no("Enable anonymous usage statistics", default=False)
        self.config['DEFAULT']['telemetry'] = 'true' if telemetry_enabled else 'false'
        print(self._style(
            "Telemetry enabled" if telemetry_enabled else "Telemetry disabled",
            color="32" if telemetry_enabled else "31",
        ))

        auto_update_enabled = self._ask_yes_no("Enable automatic update checks [does not work]", default=True)
        self.config['DEFAULT']['auto_update'] = 'true' if auto_update_enabled else 'false'
        print(self._style(
            "Auto-update enabled" if auto_update_enabled else "Auto-update disabled",
            color="32" if auto_update_enabled else "31",
        ))

        self._render_step(3, total_steps, "Choose default code editor")
        print(f"Detected default editor: {self.config['DEFAULT']['editor']}")
        if self._ask_yes_no("Change default editor", default=False):
            available_editors = self.detect_available_editors()
            if available_editors:
                rows = [[str(i), name, cmd] for i, (cmd, name) in enumerate(available_editors, 1)]
                self._render_table(["#", "Editor", "Command"], rows)
                try:
                    choice = int(input(f"Select editor (1-{len(available_editors)}): ").strip())
                    if 1 <= choice <= len(available_editors):
                        self.config['DEFAULT']['editor'] = available_editors[choice - 1][0]
                        print(self._style(
                            f"Default editor set to: {available_editors[choice - 1][1]}",
                            color="32",
                        ))
                except (ValueError, IndexError):
                    print(self._style("Invalid selection, keeping current editor", color="33"))
            else:
                print(self._style("No additional editors detected", color="33"))

        self._render_step(4, total_steps, "Set project defaults")
        default_template = input("Default template [html/flask] (html): ").strip().lower()
        if default_template in ['html', 'flask']:
            self.config['DEFAULT']['default_template'] = default_template
        else:
            self.config['DEFAULT']['default_template'] = 'html'
            if default_template:
                print(self._style("Invalid template, fallback to 'html'", color="33"))

        auto_git = self._ask_yes_no("Initialize git repository for new projects", default=False)
        self.config['PROJECT']['auto_git'] = 'true' if auto_git else 'false'

        auto_venv = self._ask_yes_no("Create virtual environment for Python projects", default=True)
        self.config['PROJECT']['auto_venv'] = 'true' if auto_venv else 'false'

        self._render_step(5, total_steps, "Finalize setup")
        self.config['DEFAULT']['first_run'] = 'false'
        self.save_config()
        
        self.send_telemetry("setup_completed", 
                   mirror_enabled=self.config['MIRROR'].getboolean('enabled'),
                   telemetry_enabled=self.config['DEFAULT'].getboolean('telemetry'),
                   auto_update_enabled=self.config['DEFAULT'].getboolean('auto_update'))

        # Check if templates exist
        self.check_templates_exist(verbose=False)

        self._panel(
            "Setup Complete",
            [
                "Your APD is now ready.",
                f"Mirror: {'ON' if self.config['MIRROR'].getboolean('enabled') else 'OFF'}",
                f"Telemetry: {'ON' if self.config['DEFAULT'].getboolean('telemetry') else 'OFF'}",
                f"Auto-update: {'ON' if self.config['DEFAULT'].getboolean('auto_update') else 'OFF'}",
            ],
            tone="ok",
        )

        self._print_section("Quick Start")
        print("  apd new myproject")
        print("  apd new api --flask")
        print("  apd templates")
        print("  apd config")
        print("  apd doctor")
        print()
        print(self._style("Tip: run 'apd --help' for all commands.", color="90"))

        input("Press Enter to continue...")
        self.log_activity('info', 'First run setup completed')
    
    def detect_available_editors(self) -> List[Tuple[str, str]]:
        """Detect available code editors on system"""
        editors = [
            ('code', 'VS Code'),
            ('vim', 'Vim'),
            ('nano', 'Nano'),
            ('notepad', 'Notepad'),
            ('gedit', 'GEdit'),
            ('subl', 'Sublime Text'),
            ('atom', 'Atom'),
            ('emacs', 'Emacs'),
            ('pycharm', 'PyCharm'),
            ('webstorm', 'WebStorm')
        ]
        
        available = []
        for cmd, name in editors:
            if shutil.which(cmd):
                available.append((cmd, name))
        
        return available
    
    def test_mirror(self) -> bool:
        """Test if mirror is accessible"""
        try:
            mirror_url = self.config['MIRROR']['url']
            req = urllib.request.Request(
                f"{mirror_url}/",
                headers={'User-Agent': f'APD/{self.version}'}
            )
            response = urllib.request.urlopen(req, timeout=5)
            return response.getcode() == 200
        except:
            return False
    
    def install_templates(self, source_dir: Path):
        """Install templates from source directory"""
        try:
            installed_count = 0
            
            # Copy HTML template if exists
            html_src = source_dir / "html"
            html_dst = self.templates_dir / "html"
            if html_src.exists():
                shutil.copytree(html_src, html_dst, dirs_exist_ok=True)
                print(f"✅ Installed HTML template")
                installed_count += 1
            
            # Copy Flask template if exists
            flask_src = source_dir / "flask"
            flask_dst = self.templates_dir / "flask"
            if flask_src.exists():
                shutil.copytree(flask_src, flask_dst, dirs_exist_ok=True)
                print(f"✅ Installed Flask template")
                installed_count += 1
            
            # Create available.inf marker
            if installed_count > 0:
                marker_file = self.config_dir / "available.inf"
                with open(marker_file, 'w') as f:
                    f.write(f"APD v{self.version}\n")
                    f.write(f"Installed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Templates: {installed_count}\n")
            
            print(f"\n📊 Installed {installed_count} template(s)")
            
        except Exception as e:
            print(f"❌ Error installing templates: {e}")
            self.log_activity('error', f'Template installation failed: {e}')
    
    def check_installation(self) -> bool:
        """Check if CLI is properly installed and has templates"""
        return self.check_templates_exist()
    
    def check_templates_exist(self, verbose: bool = True) -> bool:
        """Check if templates exist and report status"""
        all_templates = self.list_available_templates()
        templates_exist = len(all_templates) > 0
        
        # Define built-in templates
        builtin_templates = ['html', 'flask']
        
        if verbose:
            self._print_title("Template Status")
            rows = []
            
            # Show built-in templates first
            for template_name in builtin_templates:
                template_path = self.templates_dir / template_name
                if template_path.exists():
                    file_count = len(list(template_path.rglob("*")))
                    rows.append([template_name, "Available (built-in)", f"{file_count} files"])
                else:
                    rows.append([template_name, "Not installed", "Run 'apd --setup' to install"])
            
            # Show custom templates
            custom_templates = [t for t in all_templates if t not in builtin_templates]
            for template_name in custom_templates:
                template_path = self.templates_dir / template_name
                file_count = len(list(template_path.rglob("*")))
                template_type = self.detect_template_type(template_path)
                rows.append([template_name, "Available (custom)", f"{file_count} files | Type: {template_type}"])

            self._render_table(["Template", "Status", "Details"], rows)

            if not templates_exist:
                self._panel(
                    "How To Add Templates",
                    [
                        f"Templates directory: {self.templates_dir}",
                        "1. Create a template: apd templates create <name>",
                        "2. Or import one: apd templates import <url-or-file>",
                        "3. Or run 'apd --setup' to install default templates",
                    ],
                    tone="warn",
                )
        
        return templates_exist
    
    def show_help(self):
        """Display comprehensive help information"""
        self._print_title(
            f"{self.app_name} v{self.version}",
            "Advanced project deployer and template manager"
        )

        self._print_section("Usage")
        print("  apd <command> [options]")

        sections = [
            ("Core", [
                ("new <name> [--template <name>]", "Create a new project"),
                ("init [name] [--flask|--html]", "Interactive project creation"),
                ("doctor", "Run system diagnostics"),
                ("update [--force|-f]", "Check for updates (--force to install)"),
            ]),
            ("Projects", [
                ("projects", "List created projects"),
                ("open <name>", "Open project in default editor"),
                ("info <name>", "Show project details"),
                ("archive <name>", "Archive project"),
                ("delete <name>", "Delete project with confirmation"),
            ]),
            ("Templates", [
                ("templates", "List available templates"),
                ("templates list [--online|-o] [--no-cache|-nc]", "List templates with details"),
                ("templates search <term> [--no-cache|-nc]", "Search templates locally and on remote repo"),
                ("templates install <name> [--no-cache|-nc]", "Download and install template from remote repo"),
                ("templates create <name>", "Create template from current directory"),
                ("templates info <name>", "Show manifest details"),
                ("templates validate <name>", "Validate template structure"),
                ("templates edit <name>", "Edit template manifest"),
                ("templates import <source>", "Import from URL or local archive"),
                ("templates remove <name>", "Remove template"),
                ("templates export <name>", "Export template archive"),
                ("help templates", "Show template creation guide"),
            ]),
            ("Config", [
                ("config", "Show current configuration"),
                ("config mirror [enable|disable]", "Configure PyPI mirror"),
                ("config editor <name>", "Set default editor"),
                # ("config reset", "Reset configuration to defaults"),
                ("config path", "Show all configuration paths"),
            ]),
            ("System", [
                ("status", "Show runtime and system status"),
                ("logs [--tail]", "Show logs or live tail"),
                ("cleanup", "Clean old logs and empty folders"),
                ("uninstall", "Uninstall APD"),
                ("version / about / help", "Show information screens"),
            ]),
        ]

        width = self._terminal_width()
        cmd_width = max(30, min(42, int(width * 0.46)))
        desc_width = max(20, width - cmd_width - 6)

        for title, rows in sections:
            self._print_section(title)
            for cmd, desc in rows:
                desc_lines = textwrap.wrap(desc, width=desc_width) or [""]
                print(f"  {self._style(cmd.ljust(cmd_width), color='36')}{desc_lines[0]}")
                for line in desc_lines[1:]:
                    print(" " * (cmd_width + 2) + line)

        self._print_section("Examples")
        for example in [
            "apd new myapp --flask",
            "apd new website --html",
            "apd config mirror enable",
            "apd doctor",
            "apd open myapp",
        ]:
            print(f"  {self._style(example, color='32')}")

        self._print_section("Paths")
        self._render_pairs([
            ("Templates", str(self.templates_dir)),
            ("Configuration", str(self.config_dir)),
        ])
    
    def show_about(self):
        """Show about information"""
        self._print_title(
            f"{self.app_name} v{self.version}",
            "Advanced Project Deployer CLI"
        )

        self._print_section("Description")
        description = (
            "A CLI tool for scaffolding and managing projects with template support, "
            "mirror-aware package installation, diagnostics, and project lifecycle tools."
        )
        for line in textwrap.wrap(description, width=self._terminal_width() - 4):
            print(f"  {line}")

        self._print_section("Features")
        for item in [
            "Template-based project generation",
            "National PyPI mirror support",
            "Project lifecycle management",
            "System diagnostics and health checks",
            "Configurable code editors",
            "Activity logging with session tracking",
            "Cross-platform support",
        ]:
            print(f"  - {item}")

        self._print_section("Project Info")
        self._render_pairs([
            ("Author", self.config['PROJECT']['author']),
            ("License", self.config['PROJECT']['license'])
            # ("Repository", "https://github.com/IntellsGamer/ilia-cli"),
        ])

        self._print_section("Directories")
        self._render_pairs([
            ("Config", str(self.config_dir)),
            ("Templates", str(self.templates_dir)),
            ("Logs", str(self.logs_dir)),
        ])

        print()
        print(self._style("Run 'apd --help' for usage details.", color="90"))
    
    def show_config(self):
        """Display current configuration"""
        self._print_title("Current Configuration")

        self._print_section("System")
        self._render_pairs([
            ("Version", self.version),
            ("Python", platform.python_version()),
            ("Platform", platform.platform()),
            ("Session ID", self.session_id),
        ])

        self._print_section("Paths")
        self._render_pairs([
            ("Config", str(self.config_dir)),
            ("Templates", str(self.templates_dir)),
            ("Projects", str(self.projects_dir)),
            ("Logs", str(self.logs_dir)),
        ])

        mirror_enabled = self.config['MIRROR'].getboolean('enabled', False)
        auto_update = self.config['DEFAULT'].getboolean('auto_update', False)
        telemetry = self.config['DEFAULT'].getboolean('telemetry', False)

        self._print_section("Features")
        self._render_pairs([
            ("PyPI Mirror", self._badge(mirror_enabled)),
            ("Auto-Update", self._badge(auto_update)),
            ("Telemetry", self._badge(telemetry)),
        ])
        if mirror_enabled:
            self._render_pairs([
                ("Mirror URL", self.config['MIRROR']['url']),
                ("Trusted Host", self.config['MIRROR']['trusted_host']),
            ])

        self._print_section("Project Defaults")
        self._render_pairs([
            ("Default Template", self.config['DEFAULT']['default_template']),
            ("Default Editor", self.config['DEFAULT']['editor']),
            ("Auto Git", self._badge(self.config['PROJECT'].getboolean('auto_git'), "Yes", "No")),
            ("Auto VirtualEnv", self._badge(self.config['PROJECT'].getboolean('auto_venv'), "Yes", "No")),
            ("Author", self.config['PROJECT']['author']),
            ("License", self.config['PROJECT']['license']),
        ])

        self._print_section("Template Status")
        self.check_templates_exist(verbose=True)

        self._print_section("Storage")
        try:
            config_size = sum(f.stat().st_size for f in self.config_dir.rglob('*') if f.is_file())
            projects_size = 0
            if self.projects_dir.exists():
                projects_size = sum(f.stat().st_size for f in self.projects_dir.rglob('*') if f.is_file())
            self._render_pairs([
                ("Config", self.format_size(config_size)),
                ("Projects", self.format_size(projects_size)),
            ])
        except Exception:
            print("  Storage usage: unable to calculate")

        print()
        print(self._style(self._divider(), color="90"))
    
    def format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def detect_template_type(self, template_path: Path) -> str:
        """Detect what type of template this is"""
        if (template_path / "requirements.txt").exists() or (template_path / "app.py").exists():
            return "Flask/Python"
        elif (template_path / "index.html").exists() or (template_path / "package.json").exists():
            return "HTML/Web"
        elif (template_path / "Cargo.toml").exists():
            return "Rust"
        elif (template_path / "go.mod").exists():
            return "Go"
        else:
            return "Unknown"
    
    def configure_mirror(self, action: str = None):
        """Configure PyPI mirror settings"""
        if action == "enable":
            self.config['MIRROR']['enabled'] = 'true'
            self.save_config()
            self.send_telemetry("mirror_configured", enabled=(action == "enable"))
            print("✅ National PyPI mirror enabled")
            
            # Test mirror
            if self.check_internet():
                print("🔍 Testing mirror connectivity...")
                if self.test_mirror():
                    print("✅ Mirror is accessible")
                else:
                    print("⚠️  Mirror might be unavailable")
            
            # Ask about global config
            print("\nWould you like to set this mirror globally for pip?")
            choice = input("Set global pip mirror? (y/N): ").strip().lower()
            if choice == 'y':
                self.set_global_pip_mirror()
                
        elif action == "disable":
            self.config['MIRROR']['enabled'] = 'false'
            self.save_config()
            print("✅ National PyPI mirror disabled")
            
            # Optionally remove global config
            print("\nWould you like to remove global pip mirror settings?")
            choice = input("Remove global pip mirror? (y/N): ").strip().lower()
            if choice == 'y':
                self.remove_global_pip_mirror()
        else:
            print("\n🌐 PyPI Mirror Configuration")
            print("-" * 40)
            current = "enabled" if self.config['MIRROR'].getboolean('enabled') else "disabled"
            print(f"Current status: {current}")
            print(f"\nURL: {self.config['MIRROR']['url']}")
            print(f"Trusted host: {self.config['MIRROR']['trusted_host']}")
            print(f"\nCommands:")
            print("  apd config mirror enable   - Enable national mirror")
            print("  apd config mirror disable  - Disable national mirror")
    
    def set_global_pip_mirror(self):
        """Set PyPI mirror globally for pip"""
        try:
            mirror_url = self.config['MIRROR']['url']
            trusted_host = self.config['MIRROR']['trusted_host']
            
            commands = [
                [sys.executable, "-m", "pip", "config", "--user", "set", "global.index", mirror_url],
                [sys.executable, "-m", "pip", "config", "--user", "set", "global.index-url", mirror_url],
                [sys.executable, "-m", "pip", "config", "--user", "set", "global.trusted-host", trusted_host]
            ]
            
            success = True
            for cmd in commands:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"⚠️  Note: Could not set global config: {result.stderr}")
                    success = False
            
            if success:
                print("✅ Global pip mirror configured")
                print(f"   URL: {mirror_url}")
                print(f"   Trusted host: {trusted_host}")
            else:
                print("⚠️  Some configurations may not have been set")
            
        except Exception as e:
            print(f"❌ Error configuring global pip: {e}")
    
    def remove_global_pip_mirror(self):
        """Remove global pip mirror configuration"""
        try:
            commands = [
                [sys.executable, "-m", "pip", "config", "--user", "unset", "global.index"],
                [sys.executable, "-m", "pip", "config", "--user", "unset", "global.index-url"],
                [sys.executable, "-m", "pip", "config", "--user", "unset", "global.trusted-host"]
            ]
            
            for cmd in commands:
                subprocess.run(cmd, capture_output=True, text=True)
            
            print("✅ Global pip mirror configuration removed")
            
        except Exception as e:
            print(f"❌ Error removing global pip config: {e}")
    
    def install_with_mirror(self, requirements_file: Path, project_dir: Path = None):
        """Install packages using configured mirror if enabled"""
        # print(f"🔍 DEBUG START: requirements_file={requirements_file}, project_dir={project_dir}")
        
        # ALWAYS use the venv if it exists
        use_venv_pip = False
        venv_pip_path = None
        
        if project_dir and (project_dir / 'venv').exists():
            # print(f"🔍 DEBUG: Venv directory exists")
            
            if platform.system() == 'Windows':
                # Windows paths
                possible_pips = [
                    project_dir / 'venv' / 'Scripts' / 'pip.exe',
                    project_dir / 'venv' / 'Scripts' / 'pip',
                    project_dir / 'venv' / 'Scripts' / 'python.exe',  # fallback to python -m pip
                ]
            else:
                # Unix paths
                possible_pips = [
                    project_dir / 'venv' / 'bin' / 'pip',
                    project_dir / 'venv' / 'bin' / 'python',  # fallback to python -m pip
                ]
            
            # Find the first existing pip executable
            for pip_path in possible_pips:
                if pip_path.exists():
                    venv_pip_path = pip_path
                    use_venv_pip = True
                    # print(f"🔍 DEBUG: Found venv pip at: {pip_path}")
                    break
            
            # if not use_venv_pip:
            #     # print(f"🔍 DEBUG: No pip found in venv, checking manually...")
            #     # Manual check
            #     if platform.system() == 'Windows':
            #         venv_dir = project_dir / 'venv' / 'Scripts'
            #         if venv_dir.exists():
            #             for item in venv_dir.iterdir():
            #                 if 'pip' in item.name.lower() or 'python' in item.name.lower():
            #                     # print(f"🔍 DEBUG: Found in venv: {item.name}")
            #     else:
            #         venv_dir = project_dir / 'venv' / 'bin'
            #         if venv_dir.exists():
            #             for item in venv_dir.iterdir():
            #                 # print(f"🔍 DEBUG: Found in venv: {item.name}")
        
        # Build the command
        if use_venv_pip and venv_pip_path:
            # Check if it's a python executable (for python -m pip)
            if 'python' in venv_pip_path.name.lower():
                pip_cmd = [str(venv_pip_path), "-m", "pip"]
                # print(f"🔍 DEBUG: Using venv python -m pip")
            else:
                pip_cmd = [str(venv_pip_path)]
                # print(f"🔍 DEBUG: Using venv pip directly")
        else:
            pip_cmd = [sys.executable, "-m", "pip"]
            # print(f"🔍 DEBUG: Using system pip: {sys.executable}")
        
        # print(f"🔍 DEBUG: Final pip command: {pip_cmd}")
        
        if self.config['MIRROR'].getboolean('enabled', False):
            mirror_url = self.config['MIRROR']['url']
            trusted_host = self.config['MIRROR']['trusted_host']
            print(f"📦 Installing using national mirror: {mirror_url}")
            
            cmd = pip_cmd + [
                "install", "-i", mirror_url,
                "--trusted-host", trusted_host,
                "-r", str(requirements_file)
            ]
        else:
            print("📦 Installing packages...")
            cmd = pip_cmd + ["install", "-r", str(requirements_file)]
        
        # print(f"🔍 DEBUG: Full command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            # print(f"🔍 DEBUG: Command return code: {result.returncode}")
            # print(f"🔍 DEBUG: Command stdout: {result.stdout[:200]}...")
            # if result.stderr:
            #     print(f"🔍 DEBUG: Command stderr: {result.stderr[:200]}...")
            
            if result.returncode == 0:
                print("✅ Dependencies installed successfully")
                
                # VERIFY the installation
                # print("🔍 Verifying installation...")
                # if use_venv_pip and project_dir:
                #     # Try to import flask using the venv python
                #     if platform.system() == 'Windows':
                #         venv_python = project_dir / 'venv' / 'Scripts' / 'python.exe'
                #     else:
                #         venv_python = project_dir / 'venv' / 'bin' / 'python'
                    
                #     if venv_python.exists():
                #         verify_cmd = [str(venv_python), "-c", "import flask; print(f'✅ Flask version: {flask.__version__}')"]
                #         verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
                #         if verify_result.returncode == 0:
                #             print(verify_result.stdout.strip())
                #         else:
                #             print(f"❌ Flask not found in venv: {verify_result.stderr}")
                #     else:
                #         print("⚠️ Could not find venv python to verify")
                
                return True
            else:
                print(f"❌ Installation failed:")
                print(result.stderr)
                
                # Try without mirror if mirror failed
                if self.config['MIRROR'].getboolean('enabled', False):
                    print("\n⚠️  Mirror installation failed. Trying without mirror...")
                    cmd = pip_cmd + ["install", "-r", str(requirements_file)]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        return True
                
                return False
                
        except FileNotFoundError:
            print("❌ pip not found. Make sure Python is properly installed.")
            return False
        except Exception as e:
            print(f"❌ Installation error: {e}")
            return False
    
    def init_project(self, project_type: str = None, project_name: str = None):
        """Initialize a new project"""
        
        # Check templates first
        if not self.check_templates_exist():
            print("\n❌ Cannot create project: No templates found!")
            print(f"\nPlease add templates to {self.templates_dir}")
            print("or run 'apd --setup' to configure templates.")
            return
        
        print(f"\n🚀 {self.app_name} Project Initializer")
        print("=" * 60)
        
        # Get project name if not provided
        if not project_name:
            project_name = input("Project name [myproject]: ").strip()
            if not project_name:
                project_name = "myproject"
        
        # Validate project name
        if not self.validate_project_name(project_name):
            print("❌ Invalid project name!")
            print("Project name must:")
            print("  • Start with a letter")
            print("  • Contain only letters, numbers, hyphens, and underscores")
            print("  • Be 3-50 characters long")
            return
        
        # Get project type if not provided
        if not project_type:
            available_templates = self.list_available_templates()
            if not available_templates:
                print("❌ No templates available!")
                return
            
            print("\n📁 Available Templates:")
            for i, template in enumerate(available_templates, 1):
                template_type = self.detect_template_type(self.templates_dir / template)
                print(f"  {i}) {template} ({template_type})")
            
            while True:
                try:
                    choice = input(f"\nSelect template (1-{len(available_templates)}): ").strip()
                    if not choice:
                        # Use default
                        project_type = self.config['DEFAULT']['default_template']
                        if project_type in available_templates:
                            break
                        else:
                            print(f"Default template '{project_type}' not available")
                            continue
                    
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(available_templates):
                        project_type = available_templates[choice_idx]
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(available_templates)}")
                except ValueError:
                    print("Please enter a valid number")

        # Validate that project_type exists
        template_path = self.templates_dir / project_type
        if not template_path.exists():
            print(f"\n❌ Template '{project_type}' not found!")
            print(f"Available templates in {self.templates_dir}:")
            for item in self.templates_dir.iterdir():
                if item.is_dir():
                    print(f"  • {item.name}")
            return
        
        # Create project directory
        project_dir = Path.cwd() / project_name
        if project_dir.exists():
            print(f"\n⚠️  Directory '{project_name}' already exists!")
            print("\nOptions:")
            print("  1) Overwrite (delete existing)")
            print("  2) Choose different name")
            print("  3) Cancel")
            
            choice = input("\nChoose option (1-3): ").strip()
            if choice == '1':
                overwrite = input("Are you sure? This will DELETE the existing directory! (y/N): ").strip().lower()
                if overwrite in ['y', 'yes']:
                    try:
                        # First try normal removal
                        shutil.rmtree(project_dir)
                    except PermissionError:
                        # If permission error, try with read-only attribute removal
                        print("⚠️  Permission error. Trying with force removal...")
                        try:
                            # Remove read-only attributes recursively
                            for root, dirs, files in os.walk(project_dir):
                                for dir_name in dirs:
                                    dir_path = os.path.join(root, dir_name)
                                    os.chmod(dir_path, 0o777)
                                for file_name in files:
                                    file_path = os.path.join(root, file_name)
                                    os.chmod(file_path, 0o777)
                            
                            # Try removal again
                            shutil.rmtree(project_dir)
                            print("✅ Directory removed successfully")
                        except Exception as e:
                            print(f"❌ Could not remove directory: {e}")
                            print("Please manually delete the directory and try again.")
                            return
                    except Exception as e:
                        print(f"❌ Error removing directory: {e}")
                        return
                else:
                    print("Operation cancelled.")
                    return

            elif choice == '2':
                new_name = input("New project name: ").strip()
                if new_name and self.validate_project_name(new_name):
                    project_name = new_name
                    project_dir = Path.cwd() / project_name
                    if project_dir.exists():
                        print("❌ That name also exists! Operation cancelled.")
                        return
                else:
                    print("❌ Invalid name. Operation cancelled.")
                    return
            else:
                print("Operation cancelled.")
                return
        
        # Get template path
        template_path = self.templates_dir / project_type
        if not template_path.exists():
            print(f"\n❌ Template '{project_type}' not found!")
            print(f"Available templates in {self.templates_dir}:")
            for item in self.templates_dir.iterdir():
                if item.is_dir():
                    print(f"  • {item.name}")
            return
        
        # Create project
        try:
            print(f"\n📁 Creating '{project_name}' as {project_type} project...")

            # Copy/process template
            self.process_template_with_manifest(project_type, project_dir, project_name)
            print("✅ Project structure created")
            
            # Initialize git if enabled
            if self.config['PROJECT'].getboolean('auto_git'):
                self.initialize_git_repo(project_dir, project_name)
            
            # For Python/Flask projects
            if project_type == 'flask' or self.detect_template_type(template_path) == "Flask/Python":
                os.chdir(project_dir)
                
                # Create virtual environment if enabled
                if self.config['PROJECT'].getboolean('auto_venv'):
                    self.create_virtual_environment(project_dir, project_name)
                
                # Install dependencies
                requirements_file = project_dir / "requirements.txt"
                if requirements_file.exists():
                    success = self.install_with_mirror(requirements_file, project_dir)
                    if success:
                        print("✅ Dependencies installed")
                    else:
                        print("⚠️  Dependency installation failed")
                        print("You can install manually with:")
                        print(f"  cd {project_name}")
                        print(f"  pip install -r requirements.txt")
            
            # Register project
            self.register_project(project_dir, project_name, project_type)
            self.send_telemetry(
                "project_created",
                template_type=project_type,
                success=True,
                auto_git=self.config['PROJECT'].getboolean('auto_git'),
                auto_venv=self.config['PROJECT'].getboolean('auto_venv'),
                mirror_used=self.config['MIRROR'].getboolean('enabled'),
                project_size=self.get_directory_size(project_dir)
            )
            
            # Show success message
            print(f"\n🎉 Project '{project_name}' created successfully!")
            print("\n📁 Project Location:")
            print(f"  {project_dir}")
            
            # Show next steps
            print("\n🚀 Next Steps:")
            self.show_project_next_steps(project_dir, project_name, project_type)
            
            # Open in editor
            if self.config['PROJECT'].getboolean('auto_open'):
                self.open_in_editor(project_dir)
            else:
                open_now = input("\nOpen project in editor? (y/N): ").strip().lower()
                if open_now in ['y', 'yes', '']:
                    self.open_in_editor(project_dir)
            
        except Exception as e:
            print(f"\n❌ Error creating project: {e}")
            self.log_activity('error', f'Project creation failed: {e}')
            # Clean up on error
            if project_dir.exists():
                try:
                    shutil.rmtree(project_dir)
                except:
                    pass
    
    def validate_project_name(self, name: str) -> bool:
        """Validate project name"""
        if not name or len(name) < 3 or len(name) > 50:
            return False
        
        if not name[0].isalpha():
            return False
        
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        return all(char in valid_chars for char in name)
    
    def list_available_templates(self):
        """List all available templates"""
        templates = []
        if self.templates_dir.exists():
            for item in self.templates_dir.iterdir():
                if item.is_dir():
                    templates.append(item.name)
                    
        # Only print debug if verbose mode is on
        if hasattr(self, '_debug') and self._debug:
            print(f"DEBUG: Templates directory: {self.templates_dir}")
            print(f"DEBUG: Found templates: {templates}")        
        return sorted(templates)
    
    def process_template_variables(self, project_dir: Path, project_name: str):
        """Process template variables in files"""
        variables = {
            'project_name': project_name,
            'year': datetime.now().year,
            'author': self.config['PROJECT']['author'],
            'email': self.config['PROJECT']['email'],
            'version': '1.0.0',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        for file_path in project_dir.rglob('*'):
            if file_path.is_file():
                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Replace variables
                    for key, value in variables.items():
                        placeholder = f'{{{{ {key} }}}}'
                        content = content.replace(placeholder, str(value))
                    
                    # Write back if changed
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
                except (UnicodeDecodeError, PermissionError):
                    # Skip binary files or files without permission
                    continue
        
        print("✅ Template variables processed")
    
    def initialize_git_repo(self, project_dir: Path, project_name: str):
        """Initialize git repository"""
        try:
            if shutil.which('git'):
                # Initialize repo
                subprocess.run(['git', 'init'], cwd=project_dir, capture_output=True)
                
                # Create .gitignore if not exists
                gitignore_file = project_dir / '.gitignore'
                if not gitignore_file.exists():
                    default_gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
.env

# Virtual Environment
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
"""
                    with open(gitignore_file, 'w') as f:
                        f.write(default_gitignore)
                
                # Initial commit
                subprocess.run(['git', 'add', '.'], cwd=project_dir, capture_output=True)
                subprocess.run(['git', 'commit', '-m', f'Initial commit: {project_name}'], 
                             cwd=project_dir, capture_output=True)
                
                print("✅ Git repository initialized")
            else:
                print("⚠️  Git not found, skipping git initialization")
                
        except Exception as e:
            print(f"⚠️  Git initialization failed: {e}")
    
    def create_virtual_environment(self, project_dir: Path, project_name: str):
        """Create Python virtual environment"""
        try:
            venv_dir = project_dir / 'venv'
            
            # Check if venv already exists
            if venv_dir.exists():
                print("⚠️  Virtual environment already exists")
                return
            
            print("🔧 Creating virtual environment...")
            
            # Create venv
            subprocess.run([sys.executable, '-m', 'venv', str(venv_dir)], 
                         capture_output=True)
            
            print("✅ Virtual environment created")
            
            # Create activation helper
            self.create_venv_activation_helper(project_dir, venv_dir)
            
        except Exception as e:
            print(f"⚠️  Virtual environment creation failed: {e}")
    
    def create_venv_activation_helper(self, project_dir: Path, venv_dir: Path):
        """Create virtual environment activation helper scripts"""
        # Create activate.bat for Windows
        activate_bat = project_dir / 'activate.bat'
        with open(activate_bat, 'w') as f:
            f.write(f'@echo off\n"{venv_dir / "Scripts" / "activate.bat"}"\n')
        
        # Create activate.sh for Unix
        activate_sh = project_dir / 'activate.sh'
        with open(activate_sh, 'w') as f:
            f.write(f'#!/bin/bash\nsource "{venv_dir / "bin" / "activate"}"\n')
        activate_sh.chmod(0o755)
    
    def register_project(self, project_dir: Path, project_name: str, project_type: str):
        """Register project in projects database"""
        try:
            projects_file = self.projects_dir / 'projects.json'
            
            if projects_file.exists():
                with open(projects_file, 'r') as f:
                    projects = json.load(f)
            else:
                projects = []
            
            project_info = {
                'name': project_name,
                'type': project_type,
                'path': str(project_dir),
                'created': datetime.now().isoformat(),
                'modified': datetime.now().isoformat(),
                'size': self.get_directory_size(project_dir)
            }
            
            # Remove if exists
            projects = [p for p in projects if p['name'] != project_name]
            projects.append(project_info)
            
            with open(projects_file, 'w') as f:
                json.dump(projects, f, indent=2)
            
            self.log_activity('info', f'Project registered: {project_name}')
            
        except Exception as e:
            self.log_activity('error', f'Project registration failed: {e}')
    
    def get_directory_size(self, directory: Path) -> int:
        """Get directory size in bytes"""
        total = 0
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                try:
                    total += file_path.stat().st_size
                except:
                    pass
        return total
    
    def show_project_next_steps(self, project_dir: Path, project_name: str, project_type: str):
        """Show next steps for the created project"""
        
        if project_type == 'flask' or self.detect_template_type(self.templates_dir / project_type) == "Flask/Python":
            print(f"  cd {project_name}")
            
            if (project_dir / 'venv').exists():
                if platform.system() == 'Windows':
                    print("  activate.bat")
                else:
                    print("  source activate.sh")
                # print("  pip install -r requirements.txt")
            
            if (project_dir / 'venv').exists():
                if platform.system() == 'Windows':
                    print("  python app.py  # Uses venv python")
                else:
                    print("  python app.py  # Uses venv python")
            else:
                print(f"  {sys.executable} app.py")
            print("\n🌐 Open browser to: http://localhost:5000")
        
        elif project_type == 'html' or self.detect_template_type(self.templates_dir / project_type) == "HTML/Web":
            print(f"  cd {project_name}")
            print("  Open index.html in your browser")
            
            # Check for package.json
            if (project_dir / 'package.json').exists():
                print("\n📦 Node.js project detected:")
                print("  npm install")
                print("  npm start")
        
        print(f"\n📝 Edit with: {self.config['DEFAULT']['editor']} .")
    
    def open_in_editor(self, project_dir: Path):
        """Open project in default editor"""
        editor = self.config['DEFAULT']['editor']
        if editor:
            try:
                # First, try to find the full path to the editor executable
                editor_path = shutil.which(editor)
                
                if platform.system() == 'Windows':
                    if editor_path:
                        # Use the full path if found
                        subprocess.Popen([editor_path, str(project_dir)])
                    else:
                        # Try common install locations for VS Code
                        common_paths = [
                            r"C:\Program Files\Microsoft VS Code\Code.exe",
                            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
                            r"%USERPROFILE%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
                        ]
                        
                        found = False
                        for path in common_paths:
                            expanded_path = os.path.expandvars(path)
                            if os.path.exists(expanded_path):
                                subprocess.Popen([expanded_path, str(project_dir)])
                                found = True
                                break
                        
                        if not found:
                            # Last resort: try with shell=True
                            subprocess.Popen(f'"{editor}" "{project_dir}"', shell=True)
                else:
                    # Unix-like systems
                    if editor_path:
                        subprocess.Popen([editor_path, str(project_dir)])
                    else:
                        subprocess.Popen([editor, str(project_dir)])
                        
                print(f"✅ Opening in {editor}...")
            except Exception as e:
                print(f"⚠️  Could not open editor: {e}")
        else:
            print("⚠️  No default editor configured")
    
    def list_templates(self):
        """List all available templates with details"""
        print("\n📁 Available Templates")
        print("=" * 60)
        
        if not self.templates_dir.exists():
            print("❌ Templates directory not found!")
            return
        
        templates = []
        for item in self.templates_dir.iterdir():
            if item.is_dir():
                count = len(list(item.rglob("*")))
                template_type = self.detect_template_type(item)
                size = self.get_directory_size(item)
                last_modified = datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d')
                
                templates.append({
                    'name': item.name,
                    'type': template_type,
                    'files': count,
                    'size': size,
                    'modified': last_modified,
                    'path': item
                })
        
        if not templates:
            print("❌ No templates found!")
            print(f"\nTo add templates:")
            print(f"  1. Copy template folders to: {self.templates_dir}")
            print(f"  2. Or run: apd templates add <name>")
            print(f"  3. Or run from directory with templates and restart")
            return
        
        print(f"\nFound {len(templates)} template(s):")
        print("-" * 60)
        
        for i, template in enumerate(templates, 1):
            size_str = self.format_size(template['size'])
            print(f"{i:2}. {template['name']:15} ({template['type']:15})")
            print(f"     Files: {template['files']:3} | Size: {size_str:>8} | Modified: {template['modified']}")
        
        print(f"\n📁 Location: {self.templates_dir}")
        
        print("\n📋 Commands:")
        print("  apd templates create <name>   - Add template from current directory")
        print("  apd templates remove <name>   - Remove template")
        print("  apd templates import <source> - Import template from URL or local file")
        print("  apd templates export <name>   - Export template as archive")
        print("\n  Examples:")
        print("    apd templates import https://github.com/user/template/archive/main.zip")
        print("    apd templates import ./my-template.zip")
        print("    apd templates import /path/to/template.tar.gz")
    
    def manage_templates(self, action: str = None, template_name: str = None):
        """Manage templates"""
        if action == "add":
            self.add_template_from_current(template_name)
        elif action == "remove":
            self.remove_template(template_name)
        elif action == "import":
            self.import_template(template_name)
        elif action == "export":
            self.export_template(template_name)
        else:
            self.list_templates()
    
    def add_template_from_current(self, template_name: str = None):
        """Add a template from current directory"""
        if not template_name:
            template_name = input("Template name: ").strip()
            if not template_name:
                print("❌ Template name required")
                return
        
        current_dir = Path.cwd()
        template_dst = self.templates_dir / template_name
        
        # Check if current directory has files
        files = list(current_dir.rglob('*'))
        if not files:
            print("❌ Current directory is empty!")
            return
        
        if template_dst.exists():
            print(f"⚠️  Template '{template_name}' already exists!")
            print("\nOptions:")
            print("  1) Overwrite")
            print("  2) Merge (keep both)")
            print("  3) Cancel")
            
            choice = input("\nChoose option (1-3): ").strip()
            if choice == '1':
                shutil.rmtree(template_dst)
            elif choice == '2':
                pass  # Continue with copy
            else:
                print("Operation cancelled.")
                return
        
        try:
            shutil.copytree(current_dir, template_dst, dirs_exist_ok=True)
            print(f"✅ Template '{template_name}' added successfully!")
            
            # Count files
            file_count = len(list(template_dst.rglob('*')))
            self.send_telemetry("template_added", 
                   template_name=template_name,
                   file_count=file_count)
            print(f"   Files added: {file_count}")
            
            self.log_activity('info', f'Template added: {template_name}')
            
        except Exception as e:
            print(f"❌ Error adding template: {e}")
            self.log_activity('error', f'Template add failed: {e}')
    
    def remove_template(self, template_name: str):
        """Remove a template"""
        if not template_name:
            print("❌ Template name required")
            return
        
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            print(f"❌ Template '{template_name}' not found!")
            return
        
        # Show template info
        file_count = len(list(template_path.rglob('*')))
        size = self.get_directory_size(template_path)
        size_str = self.format_size(size)
        
        print(f"\n📁 Template: {template_name}")
        print(f"   Files: {file_count}")
        print(f"   Size: {size_str}")
        
        confirm = input(f"\n❌ Remove template '{template_name}'? (y/N): ").strip().lower()
        if confirm in ['yes', 'y']:
            try:
                shutil.rmtree(template_path)
                print(f"✅ Template '{template_name}' removed")
                self.send_telemetry("template_removed", 
                   template_name=template_name,
                   template_size=size)
                self.log_activity('info', f'Template removed: {template_name}')
            except Exception as e:
                print(f"❌ Error removing template: {e}")
                self.log_activity('error', f'Template removal failed: {e}')
        else:
            print("Operation cancelled.")
    
    def _import_from_url(self, url: str, template_dst: Path, template_name: str):
        """Import template from URL"""
        print(f"🔗 Downloading from URL: {url}")
        
        if not self.check_internet():
            print("❌ No internet connection!")
            return
        
        # Download to temporary file
        import tempfile
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Determine file extension from URL
            if url.endswith('.zip'):
                ext = '.zip'
                temp_file = Path(temp_dir) / f"template.zip"
            elif url.endswith('.tar.gz') or url.endswith('.tgz'):
                ext = '.tar.gz'
                temp_file = Path(temp_dir) / f"template.tar.gz"
            elif url.endswith('.tar'):
                ext = '.tar'
                temp_file = Path(temp_dir) / f"template.tar"
            else:
                # Default to zip
                ext = '.zip'
                temp_file = Path(temp_dir) / f"template.zip"
            
            print(f"📥 Downloading...")
            
            # Download file
            req = urllib.request.Request(
                url,
                headers={'User-Agent': f'APD/{self.version}'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(temp_file, 'wb') as f:
                    shutil.copyfileobj(response, f)
            
            print(f"✅ Downloaded: {temp_file.stat().st_size:,} bytes")
            
            # Extract and import
            self._extract_and_import(temp_file, template_dst, template_name, ext)
            
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    def _import_from_github(self, url: str, template_dst: Path, template_name: str):
        """Import template from GitHub/GitLab URL"""
        print(f"🐙 Importing from GitHub/GitLab: {url}")
        
        if not self.check_internet():
            print("❌ No internet connection!")
            return
        
        # Check if it's a GitHub URL
        if 'github.com' in url:
            # Convert GitHub URL to ZIP download
            if '/archive/' not in url:
                if url.endswith('.git'):
                    url = url[:-4]
                if url.endswith('/'):
                    url = url[:-1]
                url = f"{url}/archive/refs/heads/main.zip"
        
        self._import_from_url(url, template_dst, template_name)
            
    def _extract_and_import(self, archive_path: Path, template_dst: Path, template_name: str, ext: str):
        """Extract archive and import as template with manifest validation"""
        print(f"📦 Extracting {ext} archive...")
        
        try:
            # Create destination directory, but fail fast on invalid collisions
            if template_dst.exists():
                if template_dst.is_file():
                    raise FileExistsError(f"Destination exists as a file: {template_dst}")
                if any(template_dst.iterdir()):
                    raise FileExistsError(f"Destination directory is not empty: {template_dst}")
            else:
                template_dst.mkdir(parents=True, exist_ok=True)
            
            if ext == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    # Get all files
                    file_list = zip_ref.namelist()
                    print(f"  Found {len(file_list)} files in archive")
                    
                    # Extract all files
                    zip_ref.extractall(template_dst)
                    
            elif ext in ['.tar.gz', '.tgz']:
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    # Get all files
                    file_list = tar_ref.getnames()
                    print(f"  Found {len(file_list)} files in archive")
                    
                    # Extract all files
                    tar_ref.extractall(template_dst)
                    
            elif ext == '.tar':
                with tarfile.open(archive_path, 'r') as tar_ref:
                    # Get all files
                    file_list = tar_ref.getnames()
                    print(f"  Found {len(file_list)} files in archive")
                    
                    # Extract all files
                    tar_ref.extractall(template_dst)
            
            # Check if we extracted a nested structure
            extracted_items = list(template_dst.iterdir())
            
            # If there's only one directory and it's the template name, move contents up
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                inner_dir = extracted_items[0]
                
                # If inner directory name matches template name or common patterns, move contents up
                inner_name = inner_dir.name.lower()
                template_name_lower = template_name.lower()
                
                if (inner_name == template_name_lower or 
                    inner_name in ['template', 'templates', 'src', 'app', 'project'] or
                    inner_name.startswith(template_name_lower)):
                    
                    print(f"📁 Moving contents from nested directory: {inner_dir.name}")
                    
                    # Move all items from inner directory to template_dst
                    for item in inner_dir.iterdir():
                        target_path = template_dst / item.name
                        if target_path.exists():
                            if item.is_file():
                                target_path.unlink()
                            else:
                                shutil.rmtree(target_path)
                        shutil.move(str(item), str(template_dst))
                    
                    # Remove the now-empty inner directory
                    inner_dir.rmdir()
                    print(f"✅ Consolidated template structure")
            
            # Count files and directories
            extracted_files = list(template_dst.rglob('*'))
            file_count = len([f for f in extracted_files if f.is_file()])
            dir_count = len([f for f in extracted_files if f.is_dir()])
            
            print(f"✅ Imported '{template_name}' successfully!")
            print(f"   Files: {file_count}")
            print(f"   Directories: {dir_count - 1}")  # Subtract template_dst itself
            
            # Check for manifest
            manifest_file = template_dst / "manifest.json"
            if manifest_file.exists():
                print(f"📋 Manifest found: {manifest_file.name}")
                
                try:
                    # Load and validate manifest
                    with open(manifest_file, 'r') as f:
                        manifest_data = json.load(f)
                    
                    print(f"   Name: {manifest_data.get('name', 'Unknown')}")
                    print(f"   Version: {manifest_data.get('version', '1.0.0')}")
                    print(f"   Type: {manifest_data.get('type', 'files')}")
                    print(f"   Framework: {manifest_data.get('framework', 'custom')}")
                    
                    # Validate required files if specified
                    required_files = manifest_data.get('required_files', [])
                    missing_files = []
                    
                    for req_file in required_files:
                        # Handle variables in file names
                        if '{{' in req_file and '}}' in req_file:
                            # Skip variable-based file names for now
                            continue
                        
                        if not (template_dst / req_file).exists():
                            # Check recursively
                            found = False
                            for f in template_dst.rglob(req_file):
                                if f.is_file():
                                    found = True
                                    break
                            if not found:
                                missing_files.append(req_file)
                    
                    if missing_files:
                        print(f"⚠️  Warning: Missing required files: {missing_files}")
                    else:
                        print("✅ All required files present")
                    
                    # Check template structure
                    self._validate_imported_template(template_dst, manifest_data)
                    
                except json.JSONDecodeError:
                    print("⚠️  Manifest file is not valid JSON")
                except Exception as e:
                    print(f"⚠️  Could not parse manifest: {e}")
            else:
                print("ℹ️  No manifest.json found - using basic template")
                
                # Create a basic manifest for imported templates without one
                self._create_basic_manifest(template_dst, template_name)
            
            # Show template structure
            print("\n📁 Template Structure:")
            self._show_template_structure(template_dst)
            
            # Check for framework indicators
            framework = self._detect_framework_from_files(template_dst)
            if framework:
                print(f"🔍 Detected framework: {framework}")
                
                # Update manifest if exists
                if manifest_file.exists():
                    try:
                        with open(manifest_file, 'r') as f:
                            manifest = json.load(f)
                        
                        if manifest.get('framework') == 'custom' or not manifest.get('framework'):
                            manifest['framework'] = framework
                            with open(manifest_file, 'w') as f:
                                json.dump(manifest, f, indent=2)
                            print(f"✅ Updated framework in manifest to: {framework}")
                    except:
                        pass
            
            print(f"\n💡 Template ready! Use: apd new myproject --template {template_name}")
            
            self.log_activity('info', f'Template imported: {template_name} from {archive_path}')
            
        except zipfile.BadZipFile:
            print("❌ Invalid ZIP file")
            raise
        except tarfile.ReadError:
            print("❌ Invalid tar archive")
            raise
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            raise

    def _validate_imported_template(self, template_dir: Path, manifest_data: dict):
        """Validate imported template structure"""
        print(f"\n🔍 Validating template structure...")
        
        framework = manifest_data.get('framework', 'custom')
        issues = []
        
        # Framework-specific validation
        if framework == 'flask':
            if not any(template_dir.rglob('app.py')) and not any(template_dir.rglob('*.py')):
                issues.append("Flask template should have Python files")
            
            if not (template_dir / 'requirements.txt').exists():
                issues.append("Flask template should have requirements.txt")
        
        elif framework == 'react':
            if not (template_dir / 'package.json').exists():
                issues.append("React template should have package.json")
            
            if not any(template_dir.rglob('*.js')) and not any(template_dir.rglob('*.jsx')):
                issues.append("React template should have JavaScript/JSX files")
        
        elif framework == 'html':
            if not any(template_dir.rglob('*.html')) and not any(template_dir.rglob('index.html')):
                issues.append("HTML template should have HTML files")
        
        # Check for template variables
        variable_files = []
        for file_path in template_dir.rglob('*.py'):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if '{{' in content and '}}' in content:
                        variable_files.append(str(file_path.relative_to(template_dir)))
            except:
                pass
        
        for file_path in template_dir.rglob('*.html'):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if '{{' in content and '}}' in content:
                        variable_files.append(str(file_path.relative_to(template_dir)))
            except:
                pass
        
        for file_path in template_dir.rglob('*.json'):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if '{{' in content and '}}' in content:
                        variable_files.append(str(file_path.relative_to(template_dir)))
            except:
                pass
        
        if variable_files:
            print(f"✅ Found template variables in {len(variable_files)} files")
            if len(variable_files) <= 5:  # Don't show too many
                for file in variable_files[:5]:
                    print(f"   • {file}")
        
        # Check commands
        commands = manifest_data.get('commands', {})
        if any(commands.values()):
            print(f"✅ Template has {sum(len(c) for c in commands.values())} commands")
        
        if issues:
            print(f"⚠️  Validation warnings ({len(issues)}):")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print("✅ Template validation passed")

    def _create_basic_manifest(self, template_dir: Path, template_name: str):
        """Create basic manifest for imported templates without one"""
        manifest_file = template_dir / "manifest.json"
        
        # Detect framework
        framework = self._detect_framework_from_files(template_dir)
        
        # Extract variables from files
        variables = []
        
        # Scan for common variables
        for file_path in template_dir.rglob('*.py'):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    import re
                    matches = re.findall(r'\{\{\s*(\w+)\s*\}\}', content)
                    for match in matches:
                        if match not in [v['name'] for v in variables]:
                            variables.append({
                                "name": match,
                                "description": f"Variable: {match}",
                                "default": "",
                                "required": False
                            })
            except:
                pass
        
        # Add default variables if none found
        if not variables:
            variables = [
                {
                    "name": "project_name",
                    "description": "Project name",
                    "default": "",
                    "required": True
                },
                {
                    "name": "author",
                    "description": "Author name",
                    "default": getpass.getuser(),
                    "required": False
                }
            ]
        
        # Create manifest
        manifest = {
            "name": template_name,
            "version": "1.0.0",
            "description": f"{template_name} template",
            "type": "framework" if framework != 'custom' else "files",
            "framework": framework,
            "variables": variables,
            "commands": {
                "pre_copy": [],
                "post_copy": [],
                "setup": []
            },
            "dependencies": {
                "python": [],
                "node": [],
                "system": []
            },
            "required_files": [],
            "ignore_patterns": [".git", "__pycache__", "*.pyc", ".DS_Store"],
            "metadata": {
                "author": "APD",
                "created": datetime.now().isoformat(),
                "source": "imported"
            }
        }
        
        try:
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            print(f"📋 Created basic manifest: {manifest_file.name}")
        except Exception as e:
            print(f"⚠️  Could not create manifest: {e}")

    def _detect_framework_from_files(self, template_dir: Path) -> str:
        """Detect framework from files in template directory"""
        framework_indicators = {
            "flask": ["app.py", "requirements.txt", "flask"],
            "django": ["manage.py", "settings.py", "wsgi.py"],
            "react": ["package.json", "src/", "node_modules/"],
            "vue": ["vue.config.js", "package.json"],
            "angular": ["angular.json", "package.json"],
            "html": ["index.html", "style.css", "script.js"],
            "rust": ["Cargo.toml", "Cargo.lock"],
            "go": ["go.mod", "go.sum", "main.go"]
        }
        
        for framework, indicators in framework_indicators.items():
            for indicator in indicators:
                if '*' in indicator:
                    # Handle wildcards
                    if list(template_dir.glob(indicator)):
                        return framework
                elif (template_dir / indicator).exists():
                    return framework
                else:
                    # Check recursively
                    for file in template_dir.rglob(indicator):
                        if file.is_file():
                            return framework
        
        return "custom"

    def _show_template_structure(self, template_dir: Path, indent: int = 0, max_depth: int = 5):
        """Show template structure in a tree format"""
        if indent >= max_depth:
            print("    " * indent + "└── ... (truncated, too deep)")
            return
        
        items = list(template_dir.iterdir())
        items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
        
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            
            # Skip some directories
            if item.name in ['.git', '__pycache__', 'node_modules', '.idea', '.vscode']:
                continue
            
            prefix = "└── " if is_last else "├── "
            if indent > 0:
                prefix = ("    " * (indent - 1)) + ("└── " if is_last else "├── ")
            
            if item.is_dir():
                print(f"{prefix}📁 {item.name}/")
                self._show_template_structure(item, indent + 1, max_depth)
            else:
                # Show file icons based on extension
                ext = item.suffix.lower()
                icon = "📄"  # Default
                if ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c']:
                    icon = "📝"
                elif ext in ['.json', '.yaml', '.yml', '.toml']:
                    icon = "⚙️"
                elif ext in ['.html', '.htm']:
                    icon = "🌐"
                elif ext in ['.css', '.scss', '.sass']:
                    icon = "🎨"
                elif ext in ['.md', '.txt', '.rst']:
                    icon = "📋"
                elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
                    icon = "🖼️"
                elif item.name == 'manifest.json':
                    icon = "📋"
                elif item.name == 'requirements.txt':
                    icon = "📦"
                elif item.name == 'package.json':
                    icon = "📦"
                
                print(f"{prefix}{icon} {item.name}")

    def _import_from_file(self, source_path: Path, template_dst: Path, template_name: str):
        """Import template from local file"""
        print(f"📁 Importing from file: {source_path}")
        
        if not source_path.exists():
            print(f"❌ File not found: {source_path}")
            return
        
        # Check file size
        file_size = source_path.stat().st_size
        if file_size > 100 * 1024 * 1024:  # 100MB limit
            print(f"⚠️  File is large: {self.format_size(file_size)}")
            confirm = input("Continue? (y/N): ").strip().lower()
            if confirm != 'y':
                print("Import cancelled.")
                return
        
        # Determine file type from extension
        if source_path.suffix.lower() == '.zip':
            ext = '.zip'
        elif source_path.suffix.lower() in ['.tar.gz', '.tgz']:
            ext = '.tar.gz'
        elif source_path.suffix.lower() == '.tar':
            ext = '.tar'
        elif source_path.suffix.lower() == '.gz':
            # Could be .tar.gz or just .gz
            if source_path.name.lower().endswith('.tar.gz'):
                ext = '.tar.gz'
            else:
                print("⚠️  .gz files must be .tar.gz format")
                return
        else:
            # Try to detect from file magic bytes
            try:
                with open(source_path, 'rb') as f:
                    magic = f.read(4)
                    if magic[:2] == b'PK':
                        ext = '.zip'
                    elif magic[:2] == b'\x1f\x8b':
                        ext = '.tar.gz'
                    else:
                        print("❌ Unsupported file format")
                        print("Supported: .zip, .tar.gz, .tar")
                        return
            except:
                print("❌ Could not determine file format")
                return
        
        # Extract and import
        self._extract_and_import(source_path, template_dst, template_name, ext)
    
    def import_template(self, url_or_path: str = None):
        """Import template from URL or local file"""
        if not url_or_path:
            print("❌ Source required")
            print("Usage: apd templates import <url-or-file>")
            print("\nExamples:")
            print("  apd templates import https://example.com/template.zip")
            print("  apd templates import ./my-template.zip")
            print("  apd templates import C:\\templates\\project.tar.gz")
            return
        
        # Determine if it's a URL or local file
        is_url = url_or_path.startswith(('http://', 'https://', 'ftp://'))
        source_path = Path(url_or_path)
        
        # Extract template name
        if is_url:
            if 'github.com' in url_or_path:
                # Extract from GitHub URL
                parts = url_or_path.rstrip('/').split('/')
                if len(parts) >= 5:
                    template_name = parts[-1]
                    if template_name.endswith('.git'):
                        template_name = template_name[:-4]
                else:
                    template_name = parts[-1] if parts[-1] else 'github-template'
            else:
                template_name = url_or_path.split('/')[-1].replace('.git', '').replace('.zip', '').replace('.tar.gz', '').replace('.tar', '')
        else:
            template_name = source_path.stem.replace('-template', '').replace('_template', '')
        
        if not template_name or template_name == source_path.name:
            template_name = input("Template name: ").strip()
        
        template_name = template_name.strip().strip(". ")
        if not template_name:
            print("❌ Template name required")
            return
        if "/" in template_name or "\\" in template_name:
            print("❌ Invalid template name: path separators are not allowed")
            return
        
        template_dst = self.templates_dir / template_name
        
        # Check if template already exists
        if template_dst.exists():
            print(f"⚠️  Template '{template_name}' already exists!")
            print("\nOptions:")
            print("  1) Overwrite")
            print("  2) Choose different name")
            print("  3) Cancel")
            
            choice = input("\nChoose option (1-3): ").strip()
            if choice == '1':
                shutil.rmtree(template_dst)
            elif choice == '2':
                while True:
                    template_name = input("New template name: ").strip().strip(". ")
                    if not template_name:
                        print("❌ Template name required")
                        return
                    if "/" in template_name or "\\" in template_name:
                        print("❌ Invalid template name: path separators are not allowed")
                        continue
                    template_dst = self.templates_dir / template_name
                    if template_dst.exists():
                        print(f"⚠️  '{template_name}' already exists. Choose another name.")
                        continue
                    break
            else:
                print("Operation cancelled.")
                return
        
        print(f"📦 Importing template: {template_name}")
        
        try:
            if is_url:
                self._import_from_url(url_or_path, template_dst, template_name)
            else:
                self._import_from_file(source_path, template_dst, template_name)
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            self.log_activity('error', f'Template import failed: {e}')
            # Clean up on error
            if template_dst.exists():
                try:
                    shutil.rmtree(template_dst)
                except:
                    pass
    
    def export_template(self, template_name: str = None):
        """Export template as archive"""
        if not template_name:
            print("❌ Template name required")
            print("Usage: apd templates export <name>")
            return
        
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            print(f"❌ Template '{template_name}' not found!")
            return
        
        export_name = f"{template_name}-template-{datetime.now().strftime('%Y%m%d')}"
        export_file = Path.cwd() / f"{export_name}.zip"
        
        try:
            print(f"📦 Exporting '{template_name}'...")
            
            with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in template_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(template_path)
                        zipf.write(file_path, arcname)
            
            size = export_file.stat().st_size
            size_str = self.format_size(size)
            
            print(f"✅ Template exported: {export_file.name}")
            self.send_telemetry("template_exported",
                   template_name=template_name,
                   export_size=size)
            print(f"   Size: {size_str}")
            print(f"   Files: {len(list(template_path.rglob('*')))}")
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
    
    def list_projects(self):
        """List all created projects"""
        self.send_telemetry("projects_listed")
        projects_file = self.projects_dir / 'projects.json'
        
        if not projects_file.exists():
            self._print_title("Projects")
            print("No projects found.")
            print()
            print("Create your first project:")
            print(f"  {self._style('apd new myproject --html', color='32')}")
            print(f"  {self._style('apd new myapi --flask', color='32')}")
            return
        
        try:
            with open(projects_file, 'r') as f:
                projects = json.load(f)
            
            if not projects:
                self._print_title("Projects")
                print("No projects found.")
                return
            
            self._print_title(f"Your Projects ({len(projects)})")
            width = self._terminal_width()
            name_width = max(14, min(26, int(width * 0.25)))
            type_width = max(8, min(14, int(width * 0.12)))
            
            for i, project in enumerate(projects, 1):
                created = datetime.fromisoformat(project['created']).strftime('%Y-%m-%d')
                size_str = self.format_size(project.get('size', 0))
                
                name = project['name'][:name_width]
                ptype = project['type'][:type_width]
                header = f"{i:>2}. {name:<{name_width}} {ptype:<{type_width}}"
                print(self._style(header, color="36", bold=True))
                self._render_pairs([
                    ("Created", created),
                    ("Size", size_str),
                    ("Path", project['path']),
                ])
                if i < len(projects):
                    print(self._style(self._divider("."), color="90"))
            
            self._print_section("Commands")
            print("  apd open <name>      Open project in editor")
            print("  apd info <name>      Show project information")
            print("  apd delete <name>    Delete project")
            
        except Exception as e:
            print(f"❌ Error loading projects: {e}")
    
    def open_project(self, project_name: str):
        """Open project in editor"""
        self.send_telemetry("project_opened", project_name=project_name)
        project_info = self.get_project_info(project_name)
        if not project_info:
            print(f"❌ Project '{project_name}' not found!")
            return
        
        project_path = Path(project_info['path'])
        if not project_path.exists():
            print(f"❌ Project directory not found: {project_path}")
            return
        
        self.open_in_editor(project_path)
    
    def get_project_info(self, project_name: str):
        """Get project information"""
        projects_file = self.projects_dir / 'projects.json'
        
        if not projects_file.exists():
            return None
        
        try:
            with open(projects_file, 'r') as f:
                projects = json.load(f)
            
            for project in projects:
                if project['name'] == project_name:
                    return project
        except:
            pass
        
        return None
    
    def show_project_info(self, project_name: str):
        """Show detailed project information"""
        self.send_telemetry("project_info_viewed", project_name=project_name)
        project_info = self.get_project_info(project_name)
        if not project_info:
            print(f"❌ Project '{project_name}' not found!")
            return
        
        project_path = Path(project_info['path'])

        self._print_title(f"Project: {project_info['name']}")
        self._render_pairs([
            ("Type", project_info['type']),
            ("Created", datetime.fromisoformat(project_info['created']).strftime('%Y-%m-%d %H:%M:%S')),
            ("Modified", datetime.fromisoformat(project_info['modified']).strftime('%Y-%m-%d %H:%M:%S')),
            ("Size", self.format_size(project_info.get('size', 0))),
            ("Path", str(project_path)),
        ])
        
        # Check if project exists
        if project_path.exists():
            self._panel("Project Status", ["Exists on disk"], tone="ok")
            
            # Count files
            files = list(project_path.rglob('*'))
            file_count = len([f for f in files if f.is_file()])
            dir_count = len([f for f in files if f.is_dir()])
            self._render_pairs([
                ("Files", str(file_count)),
                ("Directories", str(dir_count)),
            ])
            
            # Check for common files
            self._print_section("Key Files")
            common_files = ['requirements.txt', 'package.json', 'app.py', 'index.html', 'README.md']
            key_rows = []
            for file in common_files:
                file_path = project_path / file
                if file_path.exists():
                    key_rows.append([file, "Present"])
                else:
                    # Check in subdirectories
                    found = False
                    for f in project_path.rglob(file):
                        if f.is_file():
                            key_rows.append([str(f.relative_to(project_path)), "Present"])
                            found = True
                            break
                    if not found:
                        key_rows.append([file, "Missing"])

            self._render_table(["File", "Status"], key_rows)
            
            # Git status
            if (project_path / '.git').exists():
                git_status = "Initialized"
            else:
                git_status = "Not initialized"
            
            # Virtual environment
            venv_dirs = ['venv', '.venv', 'env']
            venv_found = False
            venv_label = "Not found"
            for venv_dir in venv_dirs:
                if (project_path / venv_dir).exists():
                    venv_label = venv_dir
                    venv_found = True
                    break
            self._render_pairs([
                ("Git", git_status),
                ("Virtual Environment", venv_label if venv_found else "Not found"),
            ])
        
        else:
            self._panel("Project Status", ["Project directory is missing"], tone="error")
        
        self._print_section("Commands")
        print(f"  apd open {project_name}")
        print(f"  cd {project_path}")
    
    def run_doctor(self):
        """Run system diagnostics"""
        self._print_title("apd System Doctor")
        
        checks = []
        
        # Check 1: Python version
        python_version = platform.python_version()
        checks.append(("Python Version", f"{python_version}", "✅"))
        
        # Check 2: Platform
        platform_name = platform.system()
        checks.append(("Platform", platform_name, "✅"))
        
        # Check 3: Config directory
        if self.config_dir.exists():
            checks.append(("Config Directory", "Exists", "✅"))
        else:
            checks.append(("Config Directory", "Missing", "❌"))
        
        # Check 4: Templates directory
        if self.templates_dir.exists():
            checks.append(("Templates Directory", "Exists", "✅"))
        else:
            checks.append(("Templates Directory", "Missing", "❌"))
        
        # Check 5: Templates exist
        template_count = len(self.list_available_templates())
        if template_count > 0:
            checks.append(("Templates", f"{template_count} found", "✅"))
        else:
            checks.append(("Templates", "None found", "❌"))
        
        # Check 6: Internet connectivity
        internet = self.check_internet()
        checks.append(("Internet", "Connected" if internet else "Disconnected", 
                      "✅" if internet else "⚠️"))
        
        # Check 7: Mirror status
        mirror_enabled = self.config['MIRROR'].getboolean('enabled', False)
        checks.append(("PyPI Mirror", 
                      "Enabled" if mirror_enabled else "Disabled",
                      "✅" if mirror_enabled else "ℹ️"))
        
        # Check 8: Git availability
        git_available = shutil.which('git') is not None
        checks.append(("Git", 
                      "Available" if git_available else "Not found",
                      "✅" if git_available else "⚠️"))
        
        # Check 9: Editor availability
        editor = self.config['DEFAULT']['editor']
        editor_available = shutil.which(editor) is not None
        checks.append(("Default Editor", 
                      f"{editor} ({'Available' if editor_available else 'Not found'})",
                      "✅" if editor_available else "⚠️"))
        
        # Check 10: Virtual environment availability
        venv_available = False
        try:
            subprocess.run([sys.executable, '-m', 'venv', '--help'], 
                         capture_output=True, check=False)
            venv_available = True
        except:
            pass
        
        checks.append(("Virtual Environment", 
                      "Available" if venv_available else "Not found",
                      "✅" if venv_available else "⚠️"))
        
        # Display checks
        self._print_section("System Checks")
        for check_name, status, icon in checks:
            clean_icon = icon.replace("✅", "OK").replace("⚠️", "WARN").replace("❌", "FAIL").replace("ℹ️", "INFO")
            label = f"[{clean_icon}] {check_name}"
            self._render_pairs([(label, status)])
        
        # Summary
        self._print_section("Summary")
        
        total = len(checks)
        ok = sum(1 for _, _, icon in checks if icon == "✅")
        warnings = sum(1 for _, _, icon in checks if icon == "⚠️")
        errors = sum(1 for _, _, icon in checks if icon == "❌")
        
        self._render_pairs([
            ("Total Checks", str(total)),
            ("Passed", str(ok)),
            ("Warnings", str(warnings)),
            ("Errors", str(errors)),
        ])
        
        # Recommendations
        self._print_section("Recommendations")
        recommendations = []
        
        if template_count == 0:
            recommendations.append(f"Add templates to: {self.templates_dir}")
        
        if not editor_available:
            recommendations.append(f"Install '{editor}' or run: apd config editor <editor-name>")
        
        if not git_available and self.config['PROJECT'].getboolean('auto_git'):
            recommendations.append("Install Git or disable auto-git: apd config set PROJECT.auto_git false")
        
        if not venv_available and self.config['PROJECT'].getboolean('auto_venv'):
            recommendations.append("Install venv module or disable auto-venv: apd config set PROJECT.auto_venv false")

        if recommendations:
            for rec in recommendations:
                print(f"  - {rec}")
        else:
            print(f"  {self._style('No action required. Environment looks good.', color='32')}")
        
        self._print_section("Quick Commands")
        print("  apd config      View configuration")
        print("  apd templates   List templates")
        print("  apd alias list  List all aliases")
        print("  apd --setup     Run setup wizard")
        
        self.log_activity('info', 'System diagnostics completed')
        self.send_telemetry("doctor_ran", 
                   template_count=len(self.list_available_templates()),
                   internet_available=self.check_internet(),
                   git_available=shutil.which('git') is not None)
    
    def show_status(self):
        """Show system status"""
        self._print_title("apd System Status")
        
        # Basic info
        self._print_section("Runtime")
        self._render_pairs([
            ("Version", self.version),
            ("Session", self.session_id),
            ("Python", platform.python_version()),
            ("Platform", platform.platform()),
        ])
        
        # Configuration
        self._print_section("Configuration")
        self._render_pairs([
            ("Config", str(self.config_dir)),
            ("Templates", str(self.templates_dir)),
            ("Projects", str(self.projects_dir)),
        ])
        
        # Features
        self._print_section("Features")
        mirror = "✅ Enabled" if self.config['MIRROR'].getboolean('enabled') else "❌ Disabled"
        auto_update = "✅ Yes" if self.config['DEFAULT'].getboolean('auto_update') else "❌ No"
        telemetry = "✅ Yes" if self.config['DEFAULT'].getboolean('telemetry') else "❌ No"
        alias_count = len(self._aliases)
        self._render_pairs([
            ("PyPI Mirror", mirror),
            ("Auto-Update", auto_update),
            ("Telemetry", telemetry),
            ("Aliases", f"{alias_count} configured"),
        ])
        
        # Statistics
        self._print_section("Statistics")
        
        # Template count
        templates = self.list_available_templates()
        template_total = len(templates)
        
        # Project count
        projects_file = self.projects_dir / 'projects.json'
        project_count = 0
        if projects_file.exists():
            try:
                with open(projects_file, 'r') as f:
                    projects = json.load(f)
                    project_count = len(projects)
            except:
                pass
        projects_total = project_count
        
        # Log size
        log_size = 0
        if self.logs_dir.exists():
            for log_file in self.logs_dir.glob('*.log'):
                try:
                    log_size += log_file.stat().st_size
                except:
                    pass
        self._render_pairs([
            ("Templates", str(template_total)),
            ("Projects", str(projects_total)),
            ("Logs", self.format_size(log_size)),
        ])
        
        # System health
        self._print_section("System Health")
        internet = "✅ Connected" if self.check_internet() else "❌ Disconnected"
        git = "✅ Available" if shutil.which('git') else "❌ Not found"
        editor = self.config['DEFAULT']['editor']
        editor_status = "✅ Available" if shutil.which(editor) else "❌ Not found"
        self._render_pairs([
            ("Internet", internet),
            ("Git", git),
            (f"Editor ({editor})", editor_status),
        ])

        print()
        print(self._style("Run 'apd doctor' for detailed diagnostics.", color="90"))
    
    def _get_remote_version(self) -> Optional[str]:
        """Get the version string from the remote schematic_deploy.py."""
        owner, repo, path, branch = self._get_repo_info()
        if not owner or not repo:
            return None

        raw_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/schematic_deploy.py'
        token = self.config.get('TEMPLATE_REPO', 'token', fallback=None)
        headers = {'User-Agent': f'APD/{self.version}'}
        if token:
            headers['Authorization'] = f'token {token}'

        try:
            req = urllib.request.Request(raw_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode('utf-8')
                # Extract version from the file using regex
                import re
                match = re.search(r'^Version:\s*([\d.]+)', content, re.MULTILINE)
                if match:
                    return match.group(1)
                # Fallback: look for __version__ = "X.X.X"
                match = re.search(r'__version__\s*=\s*["\']([\d.]+)["\']', content)
                if match:
                    return match.group(1)
                # If no version found, use the first 8 chars of SHA as a fallback
                return hashlib.sha256(content.encode()).hexdigest()[:8]
        except Exception as e:
            self.log_activity('debug', f'Failed to fetch remote version: {e}')
            return None

    def _get_local_version(self) -> Optional[str]:
        """Get the version string from the local schematic_deploy.py."""
        try:
            script_path = Path(sys.argv[0]).resolve()
            if not script_path.exists():
                return None
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
                import re
                # Look for Version: X.X.X in the docstring
                match = re.search(r'^Version:\s*([\d.]+)', content, re.MULTILINE)
                if match:
                    return match.group(1)
                # Look for __version__ = "X.X.X"
                match = re.search(r'__version__\s*=\s*["\']([\d.]+)["\']', content)
                if match:
                    return match.group(1)
                # Fallback: use file's SHA
                with open(script_path, 'rb') as fb:
                    return hashlib.sha256(fb.read()).hexdigest()[:8]
        except Exception:
            return None

    def _get_script_path(self) -> Path:
        """Get the path of the currently running script."""
        return Path(sys.argv[0]).resolve()

    def _download_remote_file(self) -> Optional[bytes]:
        """Download the latest schematic_deploy.py from the repo."""
        owner, repo, path, branch = self._get_repo_info()
        if not owner or not repo:
            return None

        raw_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/schematic_deploy.py'
        token = self.config.get('TEMPLATE_REPO', 'token', fallback=None)
        headers = {'User-Agent': f'APD/{self.version}'}
        if token:
            headers['Authorization'] = f'token {token}'

        try:
            req = urllib.request.Request(raw_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("⚠️  Remote schematic_deploy.py not found in repository.")
                print(f"   Check: https://github.com/{owner}/{repo}/blob/{branch}/schematic_deploy.py")
            else:
                print(f"⚠️  HTTP Error {e.code}: Could not download file.")
            return None
        except Exception as e:
            self.log_activity('debug', f'Failed to download remote file: {e}')
            return None

    def check_for_updates(self, silent: bool = False):
        """Check for apd updates"""
        if not silent:
            self._print_title("Update Check")

        if not self.check_internet():
            if not silent:
                self._panel("Update Result", ["No internet connection"], tone="error")
            return

        try:
            remote_version = self._get_remote_version()
            if not remote_version:
                if not silent:
                    print("❌ Could not fetch remote version information.")
                return

            local_version = self._get_local_version()
            if not local_version:
                if not silent:
                    print("❌ Could not read local file.")
                return

            # Update last check timestamp
            self.config['DEFAULT']['last_update_check'] = str(int(time.time()))
            self.save_config()

            # Compare versions (simple string compare, assumes semantic versioning)
            if remote_version != local_version:
                if not silent:
                    self._panel(
                        "Update Available!",
                        [
                            f"Local version: {local_version}",
                            f"Remote version: {remote_version}",
                            "A newer version is available.",
                            "Run 'apd update --force' to download and install it.",
                        ],
                        tone="warn",
                    )
                return True
            else:
                if not silent:
                    self._panel(
                        "Update Result",
                        [
                            "You have the latest version installed.",
                            f"Version: {local_version}",
                        ],
                        tone="ok",
                    )
                return False

        except Exception as e:
            if not silent:
                print(f"❌ Update check failed: {e}")
            return False

    def perform_update(self):
        """Actually download and install the update."""
        self._print_title("Updating APD")

        if not self.check_internet():
            self._panel("Update Failed", ["No internet connection"], tone="error")
            return

        print("📥 Downloading latest version...")
        content = self._download_remote_file()
        if not content:
            print("❌ Failed to download update.")
            return

        script_path = self._get_script_path()
        if not script_path.exists():
            print(f"❌ Script not found at: {script_path}")
            return

        # Verify the downloaded file is valid Python
        try:
            compile(content, '<string>', 'exec')
            print("✅ Downloaded file is valid Python.")
        except SyntaxError as e:
            print(f"❌ Downloaded file has syntax errors: {e}")
            return

        # Get the directory where the script is located
        script_dir = script_path.parent
        script_name = script_path.name

        # Write to a new file
        new_script = script_dir / f"{script_name}.new"
        try:
            with open(new_script, 'wb') as f:
                f.write(content)
            print(f"✅ Downloaded to: {new_script}")
        except Exception as e:
            print(f"❌ Failed to write new file: {e}")
            return

        # Spawn a detached process to replace the file and restart
        print("\n🔄 Spawning updater process...")
        
        if platform.system() == 'Windows':
            # Create a temporary batch file that:
            # 1. Waits 2 seconds for this process to exit
            # 2. Replaces the file
            # 3. Restarts APD
            bat_content = f'''@echo off
echo Updating APD...
timeout /t 2 /nobreak > nul
copy /Y "{new_script}" "{script_path}" > nul
if errorlevel 1 (
    echo [FAIL] Update failed! Restoring backup...
    copy /Y "{script_dir}\\{script_name}.bak" "{script_path}" > nul
    echo Backup restored.
) else (
    echo [OK] Update successful!
    del "{new_script}" 2>nul
)
echo.
echo Starting APD...
python "{script_path}" update --verify
pause
'''
            bat_path = script_dir / "update_apd_temp.bat"
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)
            
            # Launch the batch file in a new window and exit
            # Use a simpler approach that works reliably on Windows
            try:
                # Method 1: Use start with proper quoting
                subprocess.Popen(
                    ['cmd', '/c', 'start', '/min', 'cmd', '/c', str(bat_path)],
                    shell=False,
                    creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS
                )
            except Exception:
                # Method 2: Fallback to simpler approach
                subprocess.Popen(
                    f'start /min cmd /c "{bat_path}"',
                    shell=True,
                    creationflags=subprocess.DETACHED_PROCESS
                )
            
            print("\n" + "=" * 60)
            print(self._style("[OK] Update is running in the background!", color="32", bold=True))
            print("The updater will:")
            print("  1. Wait 2 seconds for this process to exit")
            print("  2. Replace the file")
            print("  3. Restart APD with the new version")
            print("=" * 60)
            print("\n[*] This terminal will now close. A new window will open shortly.")
            
            # Schedule cleanup of the batch file after 10 seconds
            def cleanup():
                time.sleep(10)
                try:
                    if bat_path.exists():
                        bat_path.unlink()
                except:
                    pass
            threading.Thread(target=cleanup, daemon=True).start()
            
            # Exit this process so the file can be replaced
            print("\n👋 Exiting APD...")
            sys.exit(0)
            
        else:
            # Unix: use a shell script
            sh_content = f'''#!/bin/sh
sleep 2
cp "{new_script}" "{script_path}"
if [ $? -eq 0 ]; then
    echo "✅ Update successful!"
    rm -f "{new_script}"
else
    echo "❌ Update failed!"
    cp "{script_dir}/{script_name}.bak" "{script_path}"
fi
echo "Starting APD..."
python "{script_path}" update --verify
'''
            sh_path = script_dir / "update_apd_temp.sh"
            with open(sh_path, 'w') as f:
                f.write(sh_content)
            os.chmod(sh_path, 0o755)
            
            subprocess.Popen(
                ['nohup', str(sh_path), '&'],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            print("\n" + "=" * 60)
            print(self._style("✅ Update is running in the background!", color="32", bold=True))
            print("=" * 60)
            print("\n[*] Exiting APD...")
            sys.exit(0)
    
    def show_logs(self, tail: bool = False):
        """Show or tail logs"""
        self.send_telemetry("logs_viewed", tail_mode=tail)
        log_files = list(self.logs_dir.glob('*.log'))
        
        if not log_files:
            self._panel("Logs", ["No log files found"], tone="warn")
            return
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        self._print_title(f"Logs ({len(log_files)} files)")
        rows = []
        for i, log_file in enumerate(log_files[:8], 1):
            size = self.format_size(log_file.stat().st_size)
            modified = datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            rows.append([str(i), log_file.name, size, modified])
        self._render_table(["#", "File", "Size", "Modified"], rows)
        
        if len(log_files) > 8:
            print(self._style(f"... and {len(log_files) - 8} more", color="90"))
        
        # Show latest log
        latest_log = log_files[0]
        self._print_section(f"Latest: {latest_log.name}")
        
        try:
            with open(latest_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Show last lines by default to keep output compact like a log viewer.
            lines = lines[-20:]
            
            for line in lines:
                print(line.rstrip())
            
            if tail:
                print()
                print(self._style("Tailing log (Ctrl+C to stop)...", color="36"))
                # Simple tail implementation
                try:
                    with open(latest_log, 'r', encoding='utf-8') as f:
                        f.seek(0, 2)  # Go to end
                        while True:
                            line = f.readline()
                            if line:
                                print(line.rstrip())
                            else:
                                time.sleep(0.1)
                except KeyboardInterrupt:
                    print("\nStopped tailing")
            
        except Exception as e:
            print(f"❌ Error reading log: {e}")
    
    def cleanup(self):
        """Clean up temporary files"""
        self.send_telemetry("cleanup_started")
        print("\n🧹 Cleaning up...")
        
        items_cleaned = 0
        items_failed = 0
        
        # Clean old log files (keep last 30 days)
        if self.logs_dir.exists():
            cutoff = time.time() - (30 * 24 * 60 * 60)  # 30 days
            
            for log_file in self.logs_dir.glob('*.log'):
                try:
                    if log_file.stat().st_mtime < cutoff:
                        log_file.unlink()
                        print(f"✅ Removed old log: {log_file.name}")
                        items_cleaned += 1
                except Exception as e:
                    print(f"❌ Failed to remove {log_file.name}: {e}")
                    items_failed += 1
        
        # Clean empty directories
        for root, dirs, files in os.walk(self.config_dir, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        print(f"✅ Removed empty directory: {dir_path.relative_to(self.config_dir)}")
                        items_cleaned += 1
                except Exception as e:
                    print(f"❌ Failed to remove directory {dir_path}: {e}")
                    items_failed += 1
        
        print(f"\n📊 Cleanup completed:")
        print(f"  ✅ Cleaned: {items_cleaned} items")
        print(f"  ❌ Failed: {items_failed} items")
        
        if items_cleaned == 0 and items_failed == 0:
            print("  💡 System is already clean!")
    
    def uninstall(self):
        """Uninstall APD - removes ALL files"""
        self.send_telemetry("uninstall_started")
        print("\n⚠️  UNINSTALL APD")
        print("=" * 60)
        
        print("\nThis will remove ALL apd files including:")
         
        if platform.system() == 'Windows':
            print(f"  1. User folder apd.bat: {Path.home() / 'apd.bat'}")
            print(f"  2. User folder schematic_deploy.py: {Path.home() / 'schematic_deploy.py'}")
        else:
            print(f"  1. User file apd: {Path.home() / 'apd'}")
            print(f"  2. User file schematic_deploy.py: {Path.home() / 'schematic_deploy.py'}")
        
        print(f"  3. AppData configuration: {self.config_dir}")
        
        print("\n⚠️  WARNING: This action cannot be undone!")
        
        confirm1 = input("\nType 'UNINSTALL' to confirm: ").strip()
        if confirm1 != 'UNINSTALL':
            print("Uninstall cancelled.")
            return
        
        confirm2 = input("Are you absolutely sure? (yes/NO): ").strip().lower()
        if confirm2 != 'yes':
            print("Uninstall cancelled.")
            return
        
        try:
            removed_items = []
            
            # 1. Remove user folder apd.bat
            user_apd_bat = Path.home() / 'apd.bat'
            if user_apd_bat.exists():
                user_apd_bat.unlink()
                removed_items.append(f"✅ {user_apd_bat}")
            
            # 2. Remove user folder schematic_deploy.py
            user_deploy_py = Path.home() / 'schematic_deploy.py'
            if user_deploy_py.exists():
                user_deploy_py.unlink()
                removed_items.append(f"✅ {user_deploy_py}")
            
            # 3. Remove AppData APD directory (force remove read-only files)
            if self.config_dir.exists():
                # Remove read-only attributes first
                for root, dirs, files in os.walk(self.config_dir):
                    for dir_name in dirs:
                        dir_path = Path(root) / dir_name
                        try:
                            os.chmod(dir_path, 0o777)
                        except:
                            pass
                    for file_name in files:
                        file_path = Path(root) / file_name
                        try:
                            os.chmod(file_path, 0o777)
                        except:
                            pass
                
                # Now remove the directory
                shutil.rmtree(self.config_dir, ignore_errors=True)
                removed_items.append(f"✅ {self.config_dir}")
            
            # Show what was removed
            if removed_items:
                print("\n📋 Removed files/directories:")
                for item in removed_items:
                    display_path = str(item).replace('✅ ', '')
                    print(f"  ✅ {display_path}")
            else:
                print("\n📭 No apd files found to remove")
            
            print("\n✅ APD has been completely uninstalled.")
            print("\nThank you for using apd! 👋")
            exit()
            
        except Exception as e:
            print(f"❌ Uninstall failed: {e}")
            print("\nYou may need to manually remove:")
            print(f"  {Path.home() / 'apd.bat'}")
            print(f"  {Path.home() / 'schematic_deploy.py'}")
            print(f"  {self.config_dir}")
    
    # def reset_config(self):
    #     """Reset configuration to defaults"""
    #     print("\n🔄 Reset Configuration")
    #     print("=" * 60)
        
    #     print("\nThis will reset all settings to defaults.")
    #     print("Your templates and projects will NOT be affected.")
        
    #     confirm = input("\nReset configuration? (y/N): ").strip().lower()
    #     if confirm != 'yes':
    #         print("Reset cancelled.")
    #         return
        
    #     try:
    #         # Backup old config
    #         backup_file = self.config_dir / f"config.backup.{int(time.time())}.ini"
    #         if self.config_file.exists():
    #             shutil.copy2(self.config_file, backup_file)
            
    #         # Remove config file
    #         if self.config_file.exists():
    #             self.config_file.unlink()
            
    #         # Reload defaults
    #         self.config = self.load_config()
    #         self.save_config()
            
    #         print("✅ Configuration reset to defaults")
    #         self.send_telemetry("config_reset")
    #         print(f"Backup saved to: {backup_file.name}")
            
    #         self.log_activity('info', 'Configuration reset')
            
    #     except Exception as e:
    #         print(f"❌ Reset failed: {e}")
    
    def show_help(self):
        """Display comprehensive help information."""
        self._print_title(
            f"{self.app_name} v{self.version}",
            "Advanced project deployer and template manager"
        )

        self._print_section("Usage")
        print("  apd <command> [options]")

        sections = [
            ("Core", [
                ("new <name> [--template <name>]", "Create a new project"),
                ("init [name] [--flask|--html]", "Interactive project creation"),
                ("doctor", "Run system diagnostics"),
                ("update [--force|-f]", "Check for updates (--force to install)"),
            ]),
            ("Aliases", [
                ("alias list", "List all configured aliases"),
                ("alias add <alias> <command>", "Add a new alias"),
                ("alias remove <alias>", "Remove an alias"),
                ("alias help", "Show alias management help"),
            ]),
            ("Projects", [
                ("projects", "List created projects"),
                ("projects refresh", "Recalculate project metadata"),
                ("projects search <term>", "Search project registry"),
                ("inspect <name|path>", "Detect stack, entrypoints, commands, env vars"),
                ("audit <name|path> [--fix|--json]", "Run local quality and secret checks"),
                ("onboard <path> [--install]", "Register and prepare an existing project"),
                ("run <name|path> [--dry-run]", "Run detected project start command"),
                ("test <name|path> [--dry-run]", "Run detected tests or syntax check"),
                ("harden <name|path>", "Generate practical safety/project files"),
                ("readme <name|path>", "Generate README.md from detected project"),
                ("license <name|path>", "Generate LICENSE file"),
                ("editorconfig <name|path>", "Generate .editorconfig"),
                ("deps <name|path>", "List parsed project dependencies"),
                ("scripts <name|path>", "List detected run/test/package scripts"),
                ("ports <name|path>", "Find ports referenced by project files"),
                ("env-check <name|path>", "Compare code env vars with env files"),
                ("lock <name|path>", "Write apd-lock.json checksums"),
                ("verify <name|path>", "Verify project against apd-lock.json"),
                ("clean-project <name|path>", "Remove generated cache/build files"),
                ("plan <name|path>", "Print practical deployment plan"),
                ("release <name|path> [label]", "Create release ZIP with audit and SBOM"),
                ("sbom <name|path>", "Generate Software Bill of Materials JSON"),
                ("graph <name|path>", "Generate dependency graph DOT file"),
                ("metrics <name|path>", "Show file, line, and size metrics"),
                ("compare <left> <right>", "Compare two projects"),
                ("scaffold-tests <name|path>", "Create smoke test scaffold"),
                ("audit-all", "Audit all registered projects"),
                ("open <name>", "Open project in default editor"),
                ("info <name>", "Show project details"),
                ("archive <name>", "Archive project to ZIP"),
                ("snapshot <name|path> [label]", "Create restorable project snapshot"),
                ("restore <zip> [dest]", "Restore an APD snapshot safely"),
                ("blueprint <name|path>", "Export reproducible project blueprint"),
                ("env <name|path>", "Generate .env.example from code references"),
                ("dockerize <name|path>", "Generate Dockerfile and .dockerignore"),
                ("ci <name|path>", "Generate GitHub Actions workflow"),
                ("delete <name>", "Delete project with confirmation"),
                ("rename <old> <new>", "Rename project and registry entry"),
            ]),
            ("Templates", [
                ("templates", "List available templates"),
                ("templates list [--online|-o] [--no-cache|-nc]", "List templates with details (show remote with -o)"),
                ("templates preview <name>", "Preview template structure"),
                ("templates search <term> [--no-cache|-nc]", "Search templates locally and on remote repo"),
                ("templates install <name> [--no-cache|-nc]", "Download and install template from remote repo"),
                ("templates create <name>", "Create template from current directory"),
                ("templates info <name>", "Show manifest details"),
                ("templates validate <name>", "Validate template structure"),
                ("templates score <name>", "Score template quality"),
                ("templates clone <src> <dst>", "Clone an installed template"),
                ("templates import <source>", "Import from URL or local archive"),
                ("templates export <name>", "Export template archive"),
            ]),
            ("Config", [
                ("config", "Show current configuration"),
                ("config get <SECTION.key>", "Read a config value"),
                ("config set <SECTION.key> <value>", "Update a config value"),
                ("config mirror [enable|disable]", "Configure PyPI mirror"),
                ("config editor <name>", "Set default editor"),
                ("config path", "Show all configuration paths"),
            ]),
            ("Power Flags", [
                ("--var key=value", "Inject template variables non-interactively"),
                ("--no-input", "Disable prompts for project creation"),
                ("--no-git / --git", "Override auto Git behavior"),
                ("--no-venv / --venv", "Override virtualenv behavior"),
                ("--no-open / --open", "Override editor launch behavior"),
                ("--force", "Overwrite/replace without extra prompt"),
                ("--preview", "Preview a template instead of creating"),
            ]),
        ]

        width = self._terminal_width()
        cmd_width = max(30, min(42, int(width * 0.46)))
        desc_width = max(20, width - cmd_width - 6)

        for title, rows in sections:
            self._print_section(title)
            for cmd, desc in rows:
                desc_lines = textwrap.wrap(desc, width=desc_width) or [""]
                print(f"  {self._style(cmd.ljust(cmd_width), color='36')}{desc_lines[0]}")
                for line in desc_lines[1:]:
                    print(" " * (cmd_width + 2) + line)

        self._print_section("Examples")
        for example in [
            "apd new myapp --flask --git --var author=ilia",
            "apd new landing --template html --no-open",
            "apd templates preview flask",
            "apd archive myapp",
            "apd config set PROJECT.auto_git true",
            "apd alias add c new        # Create alias 'c' for 'new'",
            "apd c myapp --flask        # Use alias to create project",
        ]:
            print(f"  {self._style(example, color='32')}")

        self._print_section("Paths")
        self._render_pairs([
            ("Templates", str(self.templates_dir)),
            ("Configuration", str(self.config_dir)),
            ("Projects", str(self.projects_dir)),
        ])

    def process_template_with_manifest(
        self,
        template_name: str,
        project_dir: Path,
        project_name: str,
        cli_variables: Optional[Dict[str, str]] = None,
        interactive: bool = True,
        preview_only: bool = False,
    ):
        """Process template using manifest configuration."""
        print(f"Looking for template '{template_name}' in {self.templates_dir}")
        manifest = self.get_template_manifest(template_name)
        template_src = self.templates_dir / template_name

        if not template_src.exists():
            print(f"❌ Template source not found: {template_src}")
            print(f"Available templates: {self.list_available_templates()}")
            return

        if not manifest:
            print(f"No manifest found for {template_name}, using basic processing")
            if preview_only:
                self._print_template_tree(template_src)
                return
            shutil.copytree(
                template_src,
                project_dir,
                dirs_exist_ok=True,
                ignore=self._template_copy_ignore,
            )
            self.process_template_variables(project_dir, project_name)
            return

        variable_map = self._build_template_variable_map(
            manifest,
            project_name=project_name,
            cli_variables=cli_variables or {},
            interactive=interactive,
        )

        if preview_only:
            self._panel(
                "Template Preview",
                [
                    f"Template: {template_name}",
                    f"Framework: {manifest.data.get('framework', 'custom')}",
                    f"Source: {template_src}",
                    f"Variables: {', '.join(sorted(variable_map.keys())) or 'none'}",
                ],
                tone="info",
            )
            self._print_template_tree(template_src)
            return

        print(f"Processing {template_name} template...")
        self.run_template_commands(manifest.data.get('commands', {}).get('pre_copy', []), project_dir)

        ignore_patterns = manifest.data.get('ignore_patterns', [])
        ignore = shutil.ignore_patterns(*ignore_patterns)
        shutil.copytree(template_src, project_dir, ignore=ignore, dirs_exist_ok=True)
        print("Files copied successfully")

        self._apply_template_variables(project_dir, variable_map)
        self.run_template_commands(manifest.data.get('commands', {}).get('post_copy', []), project_dir)
        print("Template processed with manifest")

    def process_template_variables(
        self,
        project_dir: Path,
        project_name: str,
        extra_variables: Optional[Dict[str, Any]] = None,
    ):
        """Process template variables in files."""
        variables = {
            'project_name': project_name,
            'year': datetime.now().year,
            'author': self.config['PROJECT']['author'],
            'email': self.config['PROJECT']['email'],
            'version': '1.0.0',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'license': self.config['PROJECT']['license'],
        }
        if extra_variables:
            variables.update(extra_variables)

        self._apply_template_variables(project_dir, variables)
        print("Template variables processed")

    def _parse_new_project_options(self, args: List[str]) -> Dict[str, Any]:
        """Parse advanced project-creation flags."""
        options = {
            'project_type': None,
            'project_name': None,
            'interactive': True,
            'force': False,
            'preview': False,
            'variables': {},
            'auto_git': None,
            'auto_venv': None,
            'auto_open': None,
            'install_dependencies': None,
            'target_dir': None,
        }

        i = 0
        while i < len(args):
            arg = args[i]

            if arg in ['--flask', '-f', '--python']:
                options['project_type'] = 'flask'
            elif arg in ['--html', '--web']:
                options['project_type'] = 'html'
            elif arg == '--template' and i + 1 < len(args):
                options['project_type'] = args[i + 1]
                i += 1
            elif arg == '--var' and i + 1 < len(args):
                key_value = args[i + 1]
                if '=' not in key_value:
                    raise ValueError("Expected --var key=value")
                key, value = key_value.split('=', 1)
                options['variables'][key.strip()] = value
                i += 1
            elif arg.startswith('--var='):
                key_value = arg.split('=', 1)[1]
                if '=' not in key_value:
                    raise ValueError("Expected --var key=value")
                key, value = key_value.split('=', 1)
                options['variables'][key.strip()] = value
            elif arg in ['--no-input', '--yes', '-y']:
                options['interactive'] = False
            elif arg == '--force':
                options['force'] = True
            elif arg == '--preview':
                options['preview'] = True
            elif arg == '--git':
                options['auto_git'] = True
            elif arg == '--no-git':
                options['auto_git'] = False
            elif arg == '--venv':
                options['auto_venv'] = True
            elif arg == '--no-venv':
                options['auto_venv'] = False
            elif arg == '--open':
                options['auto_open'] = True
            elif arg == '--no-open':
                options['auto_open'] = False
            elif arg == '--install':
                options['install_dependencies'] = True
            elif arg == '--no-install':
                options['install_dependencies'] = False
            elif arg == '--dir' and i + 1 < len(args):
                options['target_dir'] = Path(args[i + 1]).expanduser()
                i += 1
            elif not arg.startswith('-') and not options['project_name']:
                options['project_name'] = arg
            i += 1

        return options

    def init_project(
        self,
        project_type: str = None,
        project_name: str = None,
        cli_variables: Optional[Dict[str, str]] = None,
        interactive: bool = True,
        force: bool = False,
        auto_git: Optional[bool] = None,
        auto_venv: Optional[bool] = None,
        auto_open: Optional[bool] = None,
        install_dependencies: Optional[bool] = None,
        target_dir: Optional[Path] = None,
        preview_only: bool = False,
    ):
        """Initialize a new project."""
        if not self.check_templates_exist():
            print("\n❌ Cannot create project: No templates found!")
            print(f"\nPlease add templates to {self.templates_dir}")
            print("or run 'apd --setup' to configure templates.")
            return

        print(f"\n{self.app_name} Project Initializer")
        print("=" * 60)

        if not project_name and interactive:
            project_name = input("Project name [myproject]: ").strip() or "myproject"
        elif not project_name:
            project_name = "myproject"

        suggested_name = self._sanitize_project_name(project_name)
        if suggested_name != project_name:
            project_name = suggested_name

        if not self.validate_project_name(project_name):
            print("❌ Invalid project name!")
            print("Project name must:")
            print("  • Start with a letter")
            print("  • Contain only letters, numbers, hyphens, and underscores")
            print("  • Be 3-50 characters long")
            return

        if not project_type:
            available_templates = self.list_available_templates()
            if not available_templates:
                print("❌ No templates available!")
                return

            if interactive:
                print("\nAvailable Templates:")
                for i, template in enumerate(available_templates, 1):
                    template_type = self.detect_template_type(self.templates_dir / template)
                    print(f"  {i}) {template} ({template_type})")

                while True:
                    choice = input(f"\nSelect template (1-{len(available_templates)}): ").strip()
                    if not choice:
                        project_type = self.config['DEFAULT']['default_template']
                        if project_type in available_templates:
                            break
                        print(f"Default template '{project_type}' not available")
                        continue
                    try:
                        choice_idx = int(choice) - 1
                    except ValueError:
                        print("Please enter a valid number")
                        continue
                    if 0 <= choice_idx < len(available_templates):
                        project_type = available_templates[choice_idx]
                        break
                    print(f"Please enter a number between 1 and {len(available_templates)}")
            else:
                project_type = self.config['DEFAULT']['default_template']

        template_path = self.templates_dir / project_type
        if not template_path.exists():
            print(f"\n❌ Template '{project_type}' not found!")
            print(f"Available templates in {self.templates_dir}:")
            for item in self.templates_dir.iterdir():
                if item.is_dir():
                    print(f"  • {item.name}")
            return

        base_dir = target_dir.expanduser() if target_dir else Path.cwd()
        project_dir = base_dir / project_name

        if preview_only:
            self.process_template_with_manifest(
                project_type,
                project_dir,
                project_name,
                cli_variables=cli_variables or {},
                interactive=interactive,
                preview_only=True,
            )
            return

        if project_dir.exists():
            if force:
                shutil.rmtree(project_dir, ignore_errors=False)
            elif interactive:
                print(f"\nDirectory '{project_dir}' already exists!")
                print("\nOptions:")
                print("  1) Overwrite (delete existing)")
                print("  2) Choose different name")
                print("  3) Cancel")
                choice = input("\nChoose option (1-3): ").strip()
                if choice == '1':
                    overwrite = input("Are you sure? This will DELETE the existing directory! (y/N): ").strip().lower()
                    if overwrite not in ['y', 'yes']:
                        print("Operation cancelled.")
                        return
                    shutil.rmtree(project_dir, ignore_errors=False)
                elif choice == '2':
                    new_name = input("New project name: ").strip()
                    if new_name and self.validate_project_name(new_name):
                        project_name = new_name
                        project_dir = base_dir / project_name
                        if project_dir.exists():
                            print("❌ That name also exists! Operation cancelled.")
                            return
                    else:
                        print("❌ Invalid name. Operation cancelled.")
                        return
                else:
                    print("Operation cancelled.")
                    return
            else:
                print(f"❌ Directory already exists: {project_dir}. Use --force to overwrite.")
                return

        auto_git = self.config['PROJECT'].getboolean('auto_git') if auto_git is None else auto_git
        auto_venv = self.config['PROJECT'].getboolean('auto_venv') if auto_venv is None else auto_venv
        auto_open = self.config['PROJECT'].getboolean('auto_open') if auto_open is None else auto_open
        install_dependencies = True if install_dependencies is None else install_dependencies

        original_cwd = Path.cwd()
        try:
            print(f"\nCreating '{project_name}' as {project_type} project...")
            self.process_template_with_manifest(
                project_type,
                project_dir,
                project_name,
                cli_variables=cli_variables or {},
                interactive=interactive,
            )
            if not project_dir.exists():
                raise RuntimeError("Project directory was not created")

            print("Project structure created")

            if auto_git:
                self.initialize_git_repo(project_dir, project_name)

            if project_type == 'flask' or self.detect_template_type(template_path) == "Flask/Python":
                os.chdir(project_dir)
                if auto_venv:
                    self.create_virtual_environment(project_dir, project_name)

                requirements_file = project_dir / "requirements.txt"
                if install_dependencies and requirements_file.exists():
                    success = self.install_with_mirror(requirements_file, project_dir)
                    if success:
                        print("Dependencies installed")
                    else:
                        print("Dependency installation failed")
                        print("You can install manually with:")
                        print(f"  cd {project_name}")
                        print("  pip install -r requirements.txt")

            self.register_project(project_dir, project_name, project_type)
            self.send_telemetry(
                "project_created",
                template_type=project_type,
                success=True,
                auto_git=auto_git,
                auto_venv=auto_venv,
                mirror_used=self.config['MIRROR'].getboolean('enabled'),
                project_size=self.get_directory_size(project_dir)
            )

            print(f"\nProject '{project_name}' created successfully!")
            print("\nProject Location:")
            print(f"  {project_dir}")
            print("\nNext Steps:")
            self.show_project_next_steps(project_dir, project_name, project_type)

            if auto_open:
                self.open_in_editor(project_dir)
            elif interactive:
                open_now = input("\nOpen project in editor? (y/N): ").strip().lower()
                if open_now in ['y', 'yes', '']:
                    self.open_in_editor(project_dir)
        except Exception as e:
            print(f"\n❌ Error creating project: {e}")
            self.log_activity('error', f'Project creation failed: {e}')
            if project_dir.exists():
                try:
                    shutil.rmtree(project_dir)
                except Exception:
                    pass
        finally:
            try:
                os.chdir(original_cwd)
            except Exception:
                pass

    def _get_cache_file(self) -> Path:
        """Get the cache file path for remote template list."""
        cache_dir = self.config_dir / 'cache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / 'remote_templates_cache.json'

    def _is_cache_valid(self) -> bool:
        """Check if the cached remote template list is still valid (1 hour)."""
        cache_file = self._get_cache_file()
        if not cache_file.exists():
            return False
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            cached_at = data.get('cached_at', 0)
            # Cache expires after 1 hour (3600 seconds)
            if time.time() - cached_at > 3600:
                return False
            return True
        except Exception:
            return False

    def _get_cached_remote_templates(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached remote template list if valid."""
        if not self._is_cache_valid():
            return None
        cache_file = self._get_cache_file()
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('templates', [])
        except Exception:
            return None

    def _save_remote_templates_cache(self, templates: List[Dict[str, Any]]):
        """Save remote template list to cache."""
        cache_file = self._get_cache_file()
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'cached_at': time.time(),
                    'templates': templates
                }, f, indent=2)
        except Exception as e:
            self.log_activity('debug', f'Failed to save remote templates cache: {e}')

    def _fetch_remote_template_list(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Fetch list of available templates from the remote repository."""
        if use_cache:
            cached = self._get_cached_remote_templates()
            if cached is not None:
                return cached

        if not self.check_internet():
            return []

        owner, repo, path, branch = self._get_repo_info()
        if not owner or not repo:
            return []

        # Try with token if configured
        token = self.config.get('TEMPLATE_REPO', 'token', fallback=None)
        headers = {
            'User-Agent': f'APD/{self.version}',
            'Accept': 'application/vnd.github.v3+json'
        }
        if token:
            headers['Authorization'] = f'token {token}'

        api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            templates = []
            for item in data:
                if item.get('type') == 'dir':
                    templates.append({
                        'name': item['name'],
                        'path': item['path'],
                        'api_url': item['url'],
                        'source': 'remote',
                    })
            # Cache the result
            if templates:
                self._save_remote_templates_cache(templates)
            return templates
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"⚠️  Remote repository not found or private. Check your TEMPLATE_REPO config.")
                self.log_activity('warning', f'Remote repo fetch failed (404): {api_url}')
            else:
                self.log_activity('debug', f'Failed to fetch remote templates: {e}')
            return []
        except Exception as e:
            self.log_activity('debug', f'Failed to fetch remote templates: {e}')
            return []

    def list_templates(self, online: bool = False, no_cache: bool = False):
        """List all available templates with details."""
        print("\nAvailable Templates")
        print("=" * 60)

        if not self.templates_dir.exists():
            print("❌ Templates directory not found!")
            return

        templates = []
        for item in self.templates_dir.iterdir():
            if item.is_dir():
                manifest = self.get_template_manifest(item.name)
                variables_count = len(manifest.data.get('variables', [])) if manifest else 0
                templates.append({
                    'name': item.name,
                    'type': self.detect_template_type(item),
                    'files': len(list(item.rglob("*"))),
                    'size': self.get_directory_size(item),
                    'modified': datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d'),
                    'framework': manifest.data.get('framework', 'custom') if manifest else 'custom',
                    'variables': variables_count,
                    'source': 'local',
                })

        remote_templates = []
        if online:
            print("🌐 Fetching remote templates...")
            remote_templates = self._fetch_remote_template_list(use_cache=not no_cache)
            if remote_templates:
                for rt in remote_templates:
                    # Try to get manifest info for each remote template
                    manifest = self._fetch_remote_template_manifest(rt['name'])
                    rt['type'] = manifest.get('framework', 'custom') if manifest else 'custom'
                    rt['framework'] = manifest.get('framework', 'custom') if manifest else 'custom'
                    rt['variables'] = len(manifest.get('variables', [])) if manifest else 0
                    rt['source'] = 'remote'
                    rt['files'] = '?'
                    rt['size'] = '?'
                    rt['modified'] = '?'
                    templates.append(rt)
            else:
                print("⚠️  No remote templates found (check internet or repo settings)")

        if not templates:
            print("❌ No templates found!")
            print(f"\nTo add templates:")
            print(f"  1. Copy template folders to: {self.templates_dir}")
            print("  2. Or run: apd templates create <name>")
            print("  3. Or import one and retry")
            return

        rows = []
        for template in sorted(templates, key=lambda item: item.get('name', '').lower()):
            source = template.get('source', 'local')
            source_label = "📁 local" if source == 'local' else "🌐 remote"
            rows.append([
                template.get('name', ''),
                template.get('type', 'Unknown'),
                template.get('framework', 'Unknown'),
                str(template.get('variables', 0)),
                template.get('size', '?') if isinstance(template.get('size'), str) else self.format_size(template.get('size', 0)),
                template.get('modified', '?'),
                source_label,
            ])

        self._render_table(["Template", "Type", "Framework", "Vars", "Size", "Modified", "Source"], rows)

        print(f"\n📍 Local: {self.templates_dir}")
        if online:
            print(f"🌐 Remote: {self.config.get('TEMPLATE_REPO', 'owner', '')}/{self.config.get('TEMPLATE_REPO', 'repo', '')}")
            if no_cache:
                print("   ℹ️  Fetched fresh (cache skipped)")
            elif self._is_cache_valid():
                print("   ℹ️  From cache (valid for 1 hour)")
            else:
                print("   ℹ️  Fresh fetch (cache updated)")
        print("\nCommands:")
        print("  apd templates preview <name>")
        print("  apd templates search <term>")
        print("  apd templates install <name>")
        print("  apd templates clone <src> <dst>")
        print("  apd templates export <name>")

    def manage_templates(self, action: str = None, template_name: str = None, no_cache: bool = False, online: bool = False):
        """Manage templates."""
        if action == "add":
            self.add_template_from_current(template_name)
        elif action == "remove":
            self.remove_template(template_name)
        elif action == "import":
            self.import_template(template_name)
        elif action == "export":
            self.export_template(template_name)
        elif action == "list":
            self.list_templates(online=online, no_cache=no_cache)
        else:
            self.list_templates(online=online, no_cache=no_cache)

    def add_template_from_current(self, template_name: str = None):
        """Add a template from current directory."""
        if not template_name:
            template_name = input("Template name: ").strip()
            if not template_name:
                print("❌ Template name required")
                return

        template_name = self._sanitize_template_name(template_name)
        current_dir = Path.cwd()
        template_dst = self.templates_dir / template_name

        files = [p for p in current_dir.rglob('*') if p.name not in self._template_copy_ignore(str(current_dir), [p.name])]
        if not files:
            print("❌ Current directory is empty!")
            return

        if template_dst.exists():
            print(f"Template '{template_name}' already exists!")
            print("\nOptions:")
            print("  1) Overwrite")
            print("  2) Merge (keep both)")
            print("  3) Cancel")

            choice = input("\nChoose option (1-3): ").strip()
            if choice == '1':
                shutil.rmtree(template_dst)
            elif choice != '2':
                print("Operation cancelled.")
                return

        try:
            shutil.copytree(current_dir, template_dst, dirs_exist_ok=True, ignore=self._template_copy_ignore)
            manifest = self.get_template_manifest(template_name)
            if manifest:
                manifest.data['variables'] = self._collect_template_variables(template_dst) or manifest.data.get('variables', [])
                manifest.save()
            print(f"Template '{template_name}' added successfully!")
            file_count = len(list(template_dst.rglob('*')))
            self.send_telemetry("template_added", template_name=template_name, file_count=file_count)
            print(f"  Files added: {file_count}")
            self.log_activity('info', f'Template added: {template_name}')
        except Exception as e:
            print(f"❌ Error adding template: {e}")
            self.log_activity('error', f'Template add failed: {e}')

    def create_template_from_current(self, template_name: str, is_framework: bool = False):
        """Create a template from current directory with manifest."""
        template_name = self._sanitize_template_name(template_name)
        if not template_name:
            print("❌ Template name required")
            return

        current_dir = Path.cwd()
        template_dst = self.templates_dir / template_name
        files = [p for p in current_dir.rglob('*') if p.name not in self._template_copy_ignore(str(current_dir), [p.name])]
        if not files:
            print("❌ Current directory is empty!")
            return

        if template_dst.exists():
            print(f"Template '{template_name}' already exists!")
            choice = input("Overwrite? (y/N): ").strip().lower()
            if choice != 'y':
                return
            shutil.rmtree(template_dst)

        try:
            print(f"Copying from {current_dir} to {template_dst}")
            shutil.copytree(current_dir, template_dst, ignore=self._template_copy_ignore)
            manifest = TemplateManifest(template_dst)
            manifest.data['name'] = template_name
            manifest.data['type'] = 'framework' if is_framework else 'files'
            manifest.data['description'] = input(f"Template description [{template_name} template]: ").strip() or f"{template_name} template"
            manifest.data['variables'] = self._collect_template_variables(template_dst) or manifest.data.get('variables', [])
            manifest.save()
            is_valid, errors = manifest.validate()
            if not is_valid:
                print("Template validation warnings:")
                for error in errors:
                    print(f"  • {error}")
            print(f"Template '{template_name}' created with manifest!")
            print(f"Template location: {template_dst}")
            print(f"View documentation: apd template info {template_name}")
            self.log_activity('info', f'Template created: {template_name}')
        except Exception as e:
            print(f"❌ Error creating template: {e}")

    def preview_template(self, template_name: str):
        """Preview template structure and variables."""
        manifest = self.get_template_manifest(template_name)
        template_dir = self.templates_dir / template_name
        if not template_dir.exists():
            print(f"❌ Template '{template_name}' not found!")
            return

        self._print_title(f"Template Preview: {template_name}")
        if manifest:
            self._render_pairs([
                ("Framework", manifest.data.get('framework', 'custom')),
                ("Type", manifest.data.get('type', 'files')),
                ("Description", manifest.data.get('description', '')),
                ("Variables", str(len(manifest.data.get('variables', [])))),
            ])
        else:
            self._render_pairs([
                ("Framework", self.detect_template_type(template_dir)),
                ("Type", "basic"),
            ])

        self._print_template_tree(template_dir)

    def _get_repo_info(self) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Get template repository connection info from config."""
        enabled = self.config.get('TEMPLATE_REPO', 'enabled', fallback='true')
        if enabled.lower() != 'true':
            return None, None, None, None
        owner = self.config.get('TEMPLATE_REPO', 'owner', fallback='IntellsGamer')
        repo = self.config.get('TEMPLATE_REPO', 'repo', fallback='ilia-cli')
        path = self.config.get('TEMPLATE_REPO', 'path', fallback='templates')
        branch = self.config.get('TEMPLATE_REPO', 'branch', fallback='main')
        return owner, repo, path, branch

    def _fetch_remote_template_list(self) -> List[Dict[str, Any]]:
        """Fetch list of available templates from the remote repository."""
        if not self.check_internet():
            return []
        owner, repo, path, branch = self._get_repo_info()
        if not owner or not repo:
            return []
        api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
        try:
            req = urllib.request.Request(api_url, headers={
                'User-Agent': f'APD/{self.version}',
                'Accept': 'application/vnd.github.v3+json'
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            templates = []
            for item in data:
                if item.get('type') == 'dir':
                    templates.append({
                        'name': item['name'],
                        'path': item['path'],
                        'api_url': item['url'],
                        'source': 'remote',
                    })
            return templates
        except Exception as e:
            self.log_activity('debug', f'Failed to fetch remote templates: {e}')
            return []

    def _fetch_remote_template_manifest(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Fetch a single template's manifest.json from the remote repo."""
        owner, repo, path, branch = self._get_repo_info()
        if not owner or not repo:
            return None
        raw_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}/{template_name}/manifest.json'
        try:
            req = urllib.request.Request(raw_url, headers={
                'User-Agent': f'APD/{self.version}'
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return None

    def _download_template_file_from_repo(self, file_path: str, template_name: str) -> Optional[bytes]:
        """Download a single file from the remote template directory."""
        owner, repo, path, branch = self._get_repo_info()
        if not owner or not repo:
            return None
        raw_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}/{template_name}/{file_path}'
        try:
            req = urllib.request.Request(raw_url, headers={
                'User-Agent': f'APD/{self.version}'
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read()
        except Exception as e:
            self.log_activity('debug', f'Failed to download {file_path}: {e}')
            return None

    def _fetch_remote_template_file_list(self, template_name: str) -> List[Dict[str, str]]:
        """Fetch the file tree for a specific template from the remote repo."""
        owner, repo, path, branch = self._get_repo_info()
        if not owner or not repo:
            return []
        api_url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1'
        try:
            req = urllib.request.Request(api_url, headers={
                'User-Agent': f'APD/{self.version}',
                'Accept': 'application/vnd.github.v3+json'
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                tree_data = json.loads(resp.read().decode())
            prefix = f'{path}/{template_name}/'
            files = []
            for entry in tree_data.get('tree', []):
                if entry['path'].startswith(prefix) and entry['type'] == 'blob':
                    rel_path = entry['path'][len(prefix):]
                    files.append({
                        'path': rel_path,
                        'mode': entry.get('mode', '100644'),
                    })
            return files
        except Exception as e:
            self.log_activity('debug', f'Failed to fetch template file list: {e}')
            return []

    def _get_repo_info(self) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Get template repository connection info from config."""
        enabled = self.config.get('TEMPLATE_REPO', 'enabled', fallback='true')
        if enabled.lower() != 'true':
            return None, None, None, None
        owner = self.config.get('TEMPLATE_REPO', 'owner', fallback='IntellsGamer')
        repo = self.config.get('TEMPLATE_REPO', 'repo', fallback='ilia-cli')
        path = self.config.get('TEMPLATE_REPO', 'path', fallback='templates')
        branch = self.config.get('TEMPLATE_REPO', 'branch', fallback='main')
        return owner, repo, path, branch

    def _fetch_remote_template_list(self) -> List[Dict[str, Any]]:
        """Fetch list of available templates from the remote repository."""
        if not self.check_internet():
            return []
        owner, repo, path, branch = self._get_repo_info()
        if not owner or not repo:
            return []
        api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
        try:
            req = urllib.request.Request(api_url, headers={
                'User-Agent': f'APD/{self.version}',
                'Accept': 'application/vnd.github.v3+json'
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            templates = []
            for item in data:
                if item.get('type') == 'dir':
                    templates.append({
                        'name': item['name'],
                        'path': item['path'],
                        'api_url': item['url'],
                        'source': 'remote',
                    })
            return templates
        except Exception as e:
            self.log_activity('debug', f'Failed to fetch remote templates: {e}')
            return []

    def _fetch_remote_template_manifest(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Fetch a single template's manifest.json from the remote repo."""
        owner, repo, path, branch = self._get_repo_info()
        if not owner or not repo:
            return None
        raw_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}/{template_name}/manifest.json'
        try:
            req = urllib.request.Request(raw_url, headers={
                'User-Agent': f'APD/{self.version}'
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return None

    def _download_template_file_from_repo(self, file_path: str, template_name: str) -> Optional[bytes]:
        """Download a single file from the remote template directory."""
        owner, repo, path, branch = self._get_repo_info()
        if not owner or not repo:
            return None
        raw_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}/{template_name}/{file_path}'
        try:
            req = urllib.request.Request(raw_url, headers={
                'User-Agent': f'APD/{self.version}'
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read()
        except Exception as e:
            self.log_activity('debug', f'Failed to download {file_path}: {e}')
            return None

    def _fetch_remote_template_file_list(self, template_name: str) -> List[Dict[str, str]]:
        """Fetch the file tree for a specific template from the remote repo."""
        owner, repo, path, branch = self._get_repo_info()
        if not owner or not repo:
            return []
        api_url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1'
        try:
            req = urllib.request.Request(api_url, headers={
                'User-Agent': f'APD/{self.version}',
                'Accept': 'application/vnd.github.v3+json'
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                tree_data = json.loads(resp.read().decode())
            prefix = f'{path}/{template_name}/'
            files = []
            for entry in tree_data.get('tree', []):
                if entry['path'].startswith(prefix) and entry['type'] == 'blob':
                    rel_path = entry['path'][len(prefix):]
                    files.append({
                        'path': rel_path,
                        'mode': entry.get('mode', '100644'),
                    })
            return files
        except Exception as e:
            self.log_activity('debug', f'Failed to fetch template file list: {e}')
            return []

    def search_templates(self, query: str, no_cache: bool = False):
        """Search templates locally and remotely (if internet available)."""
        needle = query.strip().lower()
        local_matches = []
        for template_name in self.list_available_templates():
            manifest = self.get_template_manifest(template_name)
            haystacks = [template_name.lower(), self.detect_template_type(self.templates_dir / template_name).lower()]
            if manifest:
                haystacks.extend([
                    str(manifest.data.get('framework', '')).lower(),
                    str(manifest.data.get('description', '')).lower(),
                    ' '.join(var.get('name', '') for var in manifest.data.get('variables', [])).lower(),
                ])
            if any(needle in field for field in haystacks):
                local_matches.append(template_name)

        remote_matches = []
        online = self.check_internet()
        if online:
            remote_templates = self._fetch_remote_template_list(use_cache=not no_cache)
            for rt in remote_templates:
                name = rt['name'].lower()
                manifest = self._fetch_remote_template_manifest(rt['name'])
                haystacks = [name]
                if manifest:
                    haystacks.extend([
                        str(manifest.get('framework', '')).lower(),
                        str(manifest.get('description', '')).lower(),
                        ' '.join(var.get('name', '') for var in manifest.get('variables', [])).lower(),
                    ])
                if any(needle in field for field in haystacks):
                    remote_matches.append(rt)

        self._print_title(f"Template Search: {query}")
        if not local_matches and not remote_matches:
            print("No matching templates found.")
            if not online:
                print(" (offline mode - remote templates not searched)")
            return

        if local_matches:
            print(self._style("\nLocal Templates:", bold=True))
            rows = []
            for template_name in local_matches:
                manifest = self.get_template_manifest(template_name)
                rows.append([
                    template_name,
                    manifest.data.get('framework', 'custom') if manifest else 'custom',
                    str(len(manifest.data.get('variables', []))) if manifest else '0',
                    manifest.data.get('description', '') if manifest else '',
                    'local',
                ])
            self._render_table(["Template", "Framework", "Vars", "Description", "Source"], rows)

        if remote_matches:
            print(self._style("\nRemote Templates:", bold=True))
            rows = []
            for rt in remote_matches:
                manifest = self._fetch_remote_template_manifest(rt['name'])
                rows.append([
                    rt['name'],
                    manifest.get('framework', 'custom') if manifest else 'custom',
                    str(len(manifest.get('variables', []))) if manifest else '0',
                    manifest.get('description', '') if manifest else '',
                    'remote (install with: apd templates install ' + rt['name'] + ')',
                ])
            self._render_table(["Template", "Framework", "Vars", "Description", "Source"], rows)

        if no_cache:
            print("\nℹ️  Fetched fresh (cache skipped)")
        elif online and self._is_cache_valid():
            print("\nℹ️  From cache (valid for 1 hour)")

    def install_template_from_repo(self, template_name: str, no_cache: bool = False):
        """Download and install a template from the remote repository."""
        template_name = template_name.strip()
        if not template_name:
            print("❌ Template name required")
            return
        dst = self.templates_dir / template_name
        if dst.exists():
            print(f"⚠️  Template '{template_name}' already exists locally.")
            overwrite = input("Overwrite? (y/N): ").strip().lower()
            if overwrite not in ('y', 'yes'):
                print("Operation cancelled.")
                return
            shutil.rmtree(dst)

        print(f"Looking up '{template_name}' in remote repository...")
        remote_list = self._fetch_remote_template_list(use_cache=not no_cache)
        found = None
        for rt in remote_list:
            if rt['name'].lower() == template_name.lower():
                found = rt
                break
        if not found:
            print(f"❌ Template '{template_name}' not found in remote repository.")
            print("Use 'apd templates search' to see available templates.")
            return

        print(f"Fetching file list for '{template_name}'...")
        files = self._fetch_remote_template_file_list(template_name)
        if not files:
            print(f"❌ Could not fetch template files from repository.")
            return

        dst.mkdir(parents=True, exist_ok=True)
        total = len(files)
        for i, file_info in enumerate(files, 1):
            rel_path = file_info['path']
            target_file = dst / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            print(f"  [{i}/{total}] Downloading {rel_path}...")
            content = self._download_template_file_from_repo(rel_path, template_name)
            if content is not None:
                target_file.write_bytes(content)
            else:
                print(f"  ⚠️  Failed to download {rel_path}")

        file_count = len(list(dst.rglob('*')))
        print(f"\n✅ Template '{template_name}' installed successfully!")
        print(f"   Files: {file_count}")
        manifest_file = dst / 'manifest.json'
        if manifest_file.exists():
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                print(f"   Framework: {manifest_data.get('framework', 'custom')}")
                print(f"   Description: {manifest_data.get('description', 'No description')}")
            except Exception:
                pass
        else:
            self._create_basic_manifest(dst, template_name)
        print(f"\n💡 Usage: apd new myproject --template {template_name}")
        self.log_activity('info', f'Template installed from repo: {template_name}')

        if no_cache:
            print("\nℹ️  Fetched fresh (cache skipped)")
        elif self._is_cache_valid():
            print("\nℹ️  Using cached template list")

    def clone_template(self, source_name: str, target_name: str):
        """Clone an installed template under a new name."""
        source_dir = self.templates_dir / source_name
        target_name = self._sanitize_template_name(target_name)
        target_dir = self.templates_dir / target_name

        if not source_dir.exists():
            print(f"❌ Template '{source_name}' not found!")
            return
        if not target_name:
            print("❌ Target template name required")
            return
        if target_dir.exists():
            print(f"❌ Template '{target_name}' already exists!")
            return

        shutil.copytree(source_dir, target_dir)
        manifest = self.get_template_manifest(target_name)
        if manifest:
            manifest.data['name'] = target_name
            manifest.data.setdefault('metadata', {})
            manifest.data['metadata']['cloned_from'] = source_name
            manifest.data['metadata']['modified'] = datetime.now().isoformat()
            manifest.save()

        print(f"Cloned template '{source_name}' to '{target_name}'.")
        self.log_activity('info', f'Template cloned: {source_name} -> {target_name}')

    def _extract_and_import(self, archive_path: Path, template_dst: Path, template_name: str, ext: str):
        """Extract archive and import as template with manifest validation."""
        print(f"Extracting {ext} archive...")
        temp_dir = Path(tempfile.mkdtemp(prefix='apd-import-'))

        try:
            if template_dst.exists():
                if template_dst.is_file():
                    raise FileExistsError(f"Destination exists as a file: {template_dst}")
                if any(template_dst.iterdir()):
                    raise FileExistsError(f"Destination directory is not empty: {template_dst}")
            else:
                template_dst.mkdir(parents=True, exist_ok=True)

            extracted_files = self._safe_extract_archive(archive_path, temp_dir, ext)
            print(f"Found {len(extracted_files)} archive entries")

            source_root = self._resolve_extracted_root(temp_dir, template_name)
            shutil.copytree(source_root, template_dst, dirs_exist_ok=True)

            extracted = list(template_dst.rglob('*'))
            file_count = len([f for f in extracted if f.is_file()])
            dir_count = len([f for f in extracted if f.is_dir()])
            print(f"Imported '{template_name}' successfully!")
            print(f"  Files: {file_count}")
            print(f"  Directories: {dir_count}")

            manifest_file = template_dst / "manifest.json"
            if manifest_file.exists():
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                print(f"Manifest found: {manifest_file.name}")
                print(f"  Name: {manifest_data.get('name', 'Unknown')}")
                print(f"  Version: {manifest_data.get('version', '1.0.0')}")
                print(f"  Type: {manifest_data.get('type', 'files')}")
                print(f"  Framework: {manifest_data.get('framework', 'custom')}")
                self._validate_imported_template(template_dst, manifest_data)
            else:
                print("No manifest.json found - creating a basic manifest")
                self._create_basic_manifest(template_dst, template_name)

            self._print_template_tree(template_dst)
            framework = self._detect_framework_from_files(template_dst)
            if framework:
                print(f"Detected framework: {framework}")
            print(f"\nTemplate ready! Use: apd new myproject --template {template_name}")
            self.log_activity('info', f'Template imported: {template_name} from {archive_path}')
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def export_template(self, template_name: str = None):
        """Export template as archive."""
        if not template_name:
            print("❌ Template name required")
            print("Usage: apd templates export <name>")
            return

        template_path = self.templates_dir / template_name
        if not template_path.exists():
            print(f"❌ Template '{template_name}' not found!")
            return

        export_dir = self.templates_dir / '_exports'
        export_dir.mkdir(parents=True, exist_ok=True)
        export_file = export_dir / f"{template_name}-template-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"

        try:
            with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in template_path.rglob('*'):
                    if file_path.is_file():
                        zipf.write(file_path, file_path.relative_to(template_path))
            size = export_file.stat().st_size
            print(f"Template exported: {export_file}")
            print(f"  Size: {self.format_size(size)}")
            print(f"  Files: {len(list(template_path.rglob('*')))}")
            self.send_telemetry("template_exported", template_name=template_name, export_size=size)
        except Exception as e:
            print(f"❌ Export failed: {e}")

    def list_projects(self):
        """List all created projects."""
        self.send_telemetry("projects_listed")
        projects = self._load_projects_db()

        if not projects:
            self._print_title("Projects")
            print("No projects found.")
            print()
            print("Create your first project:")
            print(f"  {self._style('apd new myproject --html', color='32')}")
            print(f"  {self._style('apd new myapi --flask', color='32')}")
            return

        self._print_title(f"Your Projects ({len(projects)})")
        rows = []
        for project in sorted(projects, key=lambda item: item.get('name', '').lower()):
            created = project.get('created', '')
            created_label = created[:10] if created else 'Unknown'
            exists = "Yes" if Path(project.get('path', '')).exists() else "No"
            rows.append([
                project.get('name', 'Unknown'),
                project.get('type', 'Unknown'),
                self.format_size(project.get('size', 0)),
                created_label,
                exists,
                project.get('path', ''),
            ])

        self._render_table(["Name", "Type", "Size", "Created", "Exists", "Path"], rows)
        self._print_section("Commands")
        print("  apd open <name>")
        print("  apd info <name>")
        print("  apd archive <name>")
        print("  apd delete <name>")
        print("  apd rename <old> <new>")
        print("  apd projects refresh")

    def get_project_info(self, project_name: str):
        """Get project information."""
        projects = self._load_projects_db()
        index = self._find_project_index(project_name, projects)
        return projects[index] if index >= 0 else None

    def register_project(self, project_dir: Path, project_name: str, project_type: str):
        """Register project in projects database."""
        try:
            projects = self._load_projects_db()
            project_info = {
                'name': project_name,
                'type': project_type,
                'path': str(project_dir),
                'created': datetime.now().isoformat(),
                'modified': datetime.now().isoformat(),
                'size': self.get_directory_size(project_dir),
                'exists': project_dir.exists(),
            }

            index = self._find_project_index(project_name, projects)
            if index >= 0:
                original_created = projects[index].get('created', project_info['created'])
                project_info['created'] = original_created
                projects[index] = project_info
            else:
                projects.append(project_info)

            self._save_projects_db(projects)
            self.log_activity('info', f'Project registered: {project_name}')
        except Exception as e:
            self.log_activity('error', f'Project registration failed: {e}')

    def refresh_projects(self, project_name: Optional[str] = None):
        """Refresh project metadata from disk."""
        projects = self._load_projects_db()
        if not projects:
            print("No registered projects to refresh.")
            return

        refreshed = 0
        for project in projects:
            if project_name and project.get('name', '').lower() != project_name.lower():
                continue
            project_path = Path(project.get('path', ''))
            project['exists'] = project_path.exists()
            project['modified'] = datetime.now().isoformat()
            project['size'] = self.get_directory_size(project_path) if project_path.exists() else 0
            refreshed += 1

        self._save_projects_db(projects)
        print(f"Refreshed {refreshed} project(s).")
        self.log_activity('info', f'Projects refreshed: {refreshed}')

    def search_projects(self, query: str):
        """Search projects by name, type, or path."""
        projects = self._load_projects_db()
        needle = query.strip().lower()
        matches = [
            project for project in projects
            if needle in project.get('name', '').lower()
            or needle in project.get('type', '').lower()
            or needle in project.get('path', '').lower()
        ]

        self._print_title(f"Project Search: {query}")
        if not matches:
            print("No matching projects found.")
            return

        rows = []
        for project in matches:
            rows.append([
                project.get('name', ''),
                project.get('type', ''),
                self.format_size(project.get('size', 0)),
                "Yes" if Path(project.get('path', '')).exists() else "No",
                project.get('path', ''),
            ])
        self._render_table(["Name", "Type", "Size", "Exists", "Path"], rows)

    def archive_project(self, project_name: str, destination: Optional[Path] = None):
        """Archive a registered project into a ZIP file."""
        project_info = self.get_project_info(project_name)
        if not project_info:
            print(f"❌ Project '{project_name}' not found!")
            return

        project_path = Path(project_info['path'])
        if not project_path.exists():
            print(f"❌ Project directory not found: {project_path}")
            return

        destination = destination or self._archive_output_dir() / f"{project_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
        destination.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in project_path.rglob('*'):
                if file_path.is_file():
                    zipf.write(file_path, file_path.relative_to(project_path))

        print(f"Archived project to: {destination}")
        self.send_telemetry("project_archived", project_name=project_name, archive_size=destination.stat().st_size)
        self.log_activity('info', f'Project archived: {project_name} -> {destination}')

    def delete_project(self, project_name: str, force: bool = False):
        """Delete a project from disk and registry."""
        projects = self._load_projects_db()
        index = self._find_project_index(project_name, projects)
        if index < 0:
            print(f"❌ Project '{project_name}' not found!")
            return

        project = projects[index]
        project_path = Path(project.get('path', ''))
        if not force:
            confirm = input(f"Delete project '{project_name}' at '{project_path}'? (y/N): ").strip().lower()
            if confirm not in {'y', 'yes'}:
                print("Operation cancelled.")
                return

        if project_path.exists():
            shutil.rmtree(project_path)

        del projects[index]
        self._save_projects_db(projects)
        print(f"Deleted project '{project_name}'.")
        self.send_telemetry("project_deleted", project_name=project_name)
        self.log_activity('info', f'Project deleted: {project_name}')

    def rename_project(self, old_name: str, new_name: str):
        """Rename a project and update its registry entry."""
        new_name = self._sanitize_project_name(new_name)
        if not self.validate_project_name(new_name):
            print("❌ Invalid new project name.")
            return

        projects = self._load_projects_db()
        old_index = self._find_project_index(old_name, projects)
        if old_index < 0:
            print(f"❌ Project '{old_name}' not found!")
            return
        if self._find_project_index(new_name, projects) >= 0:
            print(f"❌ A project named '{new_name}' already exists in the registry.")
            return

        project = projects[old_index]
        project_path = Path(project.get('path', ''))
        target_path = project_path.with_name(new_name)
        if project_path.exists():
            if target_path.exists():
                print(f"❌ Target path already exists: {target_path}")
                return
            project_path.rename(target_path)
            project['path'] = str(target_path)

        project['name'] = new_name
        project['modified'] = datetime.now().isoformat()
        self._save_projects_db(projects)
        print(f"Renamed project '{old_name}' to '{new_name}'.")
        self.log_activity('info', f'Project renamed: {old_name} -> {new_name}')

    def show_config(self):
        """Display current configuration."""
        self._print_title("Current Configuration")

        self._print_section("System")
        self._render_pairs([
            ("Version", self.version),
            ("Python", platform.python_version()),
            ("Platform", platform.platform()),
            ("Session ID", self.session_id),
        ])

        self._print_section("Paths")
        self._render_pairs([
            ("Config", str(self.config_dir)),
            ("Templates", str(self.templates_dir)),
            ("Projects", str(self.projects_dir)),
            ("Logs", str(self.logs_dir)),
        ])

        self._print_section("Features")
        self._render_pairs([
            ("PyPI Mirror", self._badge(self.config['MIRROR'].getboolean('enabled', False))),
            ("Auto-Update", self._badge(self.config['DEFAULT'].getboolean('auto_update', False))),
            ("Telemetry", self._badge(self.config['DEFAULT'].getboolean('telemetry', False))),
        ])

        self._print_section("Project Defaults")
        self._render_pairs([
            ("Default Template", self.config['DEFAULT']['default_template']),
            ("Default Editor", self.config['DEFAULT']['editor']),
            ("Auto Git", self._badge(self.config['PROJECT'].getboolean('auto_git'), "Yes", "No")),
            ("Auto VirtualEnv", self._badge(self.config['PROJECT'].getboolean('auto_venv'), "Yes", "No")),
            ("Auto Open", self._badge(self.config['PROJECT'].getboolean('auto_open'), "Yes", "No")),
            ("Author", self.config['PROJECT']['author']),
            ("License", self.config['PROJECT']['license']),
        ])

        self._print_section("Advanced")
        for section_name in ['DEFAULT', 'MIRROR', 'PATHS', 'PROJECT', 'SECURITY', 'TELEMETRY']:
            print(f"  [{section_name}]")
            section = self.config['DEFAULT'] if section_name == 'DEFAULT' else self.config[section_name]
            for key, value in section.items():
                print(f"    {key} = {value}")

        print()
        print(self._style(self._divider(), color="90"))

    def config_get(self, dotted_key: Optional[str] = None):
        """Print config values."""
        if not dotted_key:
            self.show_config()
            return

        value = self._get_config_value(dotted_key)
        if value is None:
            print(f"❌ Unknown config key: {dotted_key}")
            return
        print(value)

    def config_set(self, dotted_key: str, value: str):
        """Set a config value via SECTION.key notation."""
        if not self._set_config_value(dotted_key, value):
            print(f"❌ Unknown config key: {dotted_key}")
            return

        self.save_config()
        print(f"Updated {dotted_key} = {self._get_config_value(dotted_key)}")
        self.log_activity('info', f'Config updated: {dotted_key}')

    def _load_aliases(self) -> Dict[str, str]:
        """Load aliases from config."""
        aliases = {}
        if 'ALIASES' in self.config:
            for key, value in self.config['ALIASES'].items():
                aliases[key] = value
        return aliases

    def _save_aliases(self):
        """Save aliases to config."""
        if 'ALIASES' not in self.config:
            self.config['ALIASES'] = {}
        
        # Clear existing aliases
        self.config['ALIASES'].clear()
        
        # Add all aliases
        for key, value in self._aliases.items():
            self.config['ALIASES'][key] = value
        
        self.save_config()

    def _resolve_alias(self, command: str) -> str:
        """Resolve an alias to its full command."""
        if not command:
            return command
        
        # Check if the entire command is an alias
        if command in self._aliases:
            resolved = self._aliases[command]
            # Recursively resolve nested aliases (avoid infinite loops)
            if resolved in self._aliases and resolved != command:
                return self._resolve_alias(resolved)
            return resolved
        
        # Check if the command starts with an alias (e.g., "c myproject" -> "new myproject")
        parts = command.split()
        if parts and parts[0] in self._aliases:
            alias_target = self._aliases[parts[0]]
            # Recursively resolve the alias target (avoid infinite loops)
            if alias_target in self._aliases and alias_target != parts[0]:
                alias_target = self._resolve_alias(alias_target)
            # Replace the first word with the alias target
            return f"{alias_target} {' '.join(parts[1:])}".strip()
        
        return command

    def add_alias(self, alias: str, command: str, force: bool = False):
        """Add a new alias."""
        alias = alias.strip()
        command = command.strip()
        
        if not alias or not command:
            print("❌ Alias and command are required")
            return False
        
        # Prevent infinite alias loops
        if alias == command:
            print("❌ Alias cannot be the same as its command")
            return False
        
        # Check if alias already exists
        if alias in self._aliases and not force:
            print(f"⚠️  Alias '{alias}' already exists: {self._aliases[alias]}")
            overwrite = input("Overwrite? (y/N): ").strip().lower()
            if overwrite != 'y':
                return False
        
        self._aliases[alias] = command
        self._save_aliases()
        print(f"✅ Alias added: {alias} -> {command}")
        self.log_activity('info', f'Alias added: {alias} -> {command}')
        return True

    def remove_alias(self, alias: str):
        """Remove an alias."""
        alias = alias.strip()
        if not alias:
            print("❌ Alias name required")
            return False
        
        if alias not in self._aliases:
            print(f"❌ Alias '{alias}' not found")
            return False
        
        removed_command = self._aliases[alias]
        del self._aliases[alias]
        self._save_aliases()
        print(f"✅ Alias removed: {alias} (was -> {removed_command})")
        self.log_activity('info', f'Alias removed: {alias}')
        return True

    def list_aliases(self):
        """List all aliases."""
        if not self._aliases:
            print("No aliases configured")
            return
        
        self._print_title("Aliases")
        rows = []
        for alias, command in sorted(self._aliases.items()):
            rows.append([alias, command])
        self._render_table(["Alias", "Command"], rows)
        
        print(f"\n💡 Total: {len(self._aliases)} alias(es)")
        print("  apd alias add <alias> <command>  - Add a new alias")
        print("  apd alias remove <alias>         - Remove an alias")

    def show_alias_help(self):
        """Show alias management help."""
        print("\n📋 Alias Management")
        print("=" * 60)
        print("\nCommands:")
        print("  apd alias list                    - List all aliases")
        print("  apd alias add <alias> <command>   - Add a new alias")
        print("  apd alias remove <alias>          - Remove an alias")
        print("  apd alias help                    - Show this help")
        print("\nExamples:")
        print("  apd alias add c new               - 'c myproject' runs 'new myproject'")
        print("  apd alias add st status           - 'st' runs 'status'")
        print("  apd alias add g config            - 'g editor' runs 'config editor'")
        print("  apd alias add ls projects         - 'ls' runs 'projects'")
        print("  apd alias add rm delete           - 'rm' runs 'delete'")
        print("\n💡 Aliases can also be used as command prefixes:")
        print("  apd c myapp --flask               - Creates a new Flask project")
        print("  apd st                            - Shows system status")
        print("  apd ls                            - Lists all projects")
        print("\n⚠️  Avoid circular alias references (alias a -> b, alias b -> a)")

    def _resolve_project_target(self, target: str) -> Tuple[Optional[Path], str, Optional[Dict[str, Any]]]:
        """Resolve a registered project name or filesystem path."""
        if not target:
            return None, "", None

        project_info = self.get_project_info(target)
        if project_info:
            project_path = Path(project_info.get('path', ''))
            return project_path, project_info.get('name', project_path.name), project_info

        project_path = Path(target).expanduser()
        if not project_path.is_absolute():
            project_path = Path.cwd() / project_path
        return project_path, project_path.name, None

    def _project_skip_dirs(self) -> set:
        """Directories skipped by analysis, snapshots, and generated artifacts."""
        return {
            '.git', '.hg', '.svn', '__pycache__', '.pytest_cache', '.mypy_cache',
            '.ruff_cache', '.tox', '.venv', 'venv', 'env', 'node_modules',
            'dist', 'build', '.idea', '.vscode', '.next', '.nuxt', 'target',
            'coverage', '.coverage', 'htmlcov', '.apd'
        }

    def _iter_project_files(self, project_path: Path, max_size: int = 2 * 1024 * 1024):
        """Yield project files while skipping generated directories and huge files."""
        skip_dirs = self._project_skip_dirs()
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.endswith('.egg-info')]
            for filename in files:
                file_path = Path(root) / filename
                try:
                    if file_path.stat().st_size <= max_size:
                        yield file_path
                except Exception:
                    continue

    def _project_rel(self, project_path: Path, file_path: Path) -> str:
        """Return a stable relative path for reports."""
        try:
            return str(file_path.relative_to(project_path))
        except Exception:
            return str(file_path)

    def _read_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Read JSON safely."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _read_text_file(self, file_path: Path, limit: int = 300000) -> str:
        """Read a text file safely with a size limit."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read(limit)
        except Exception:
            return ""

    def _parse_requirements(self, requirements_file: Path) -> List[Dict[str, str]]:
        """Parse a requirements.txt-like file without external dependencies."""
        requirements = []
        for raw_line in self._read_text_file(requirements_file).splitlines():
            line = raw_line.lstrip('\ufeff').strip()
            if not line or line.startswith('#') or line.startswith('-'):
                continue
            name = re.split(r'[<>=!~;\[]', line, 1)[0].strip()
            requirements.append({
                'raw': line,
                'name': name,
                'pinned': '==' in line or '===' in line,
            })
        return requirements

    def _detect_project_stack(self, project_path: Path) -> Dict[str, Any]:
        """Detect languages, frameworks, commands, and dependency files."""
        stack = {
            'languages': {},
            'frameworks': [],
            'dependency_files': [],
            'run_commands': [],
            'test_commands': [],
            'package_manager': None,
            'entrypoints': [],
        }

        extension_languages = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.html': 'HTML',
            '.css': 'CSS',
            '.go': 'Go',
            '.rs': 'Rust',
            '.java': 'Java',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
        }
        for file_path in self._iter_project_files(project_path):
            language = extension_languages.get(file_path.suffix.lower())
            if language:
                stack['languages'][language] = stack['languages'].get(language, 0) + 1

        def add_framework(name: str):
            if name not in stack['frameworks']:
                stack['frameworks'].append(name)

        requirements_file = project_path / 'requirements.txt'
        if requirements_file.exists():
            stack['dependency_files'].append('requirements.txt')
            req_text = self._read_text_file(requirements_file).lower()
            if 'flask' in req_text:
                add_framework('Flask')
                stack['run_commands'].append('python app.py')
            if 'django' in req_text or (project_path / 'manage.py').exists():
                add_framework('Django')
                stack['run_commands'].append('python manage.py runserver')
            if 'fastapi' in req_text:
                add_framework('FastAPI')
                stack['run_commands'].append('uvicorn main:app --reload')
            has_pytest = 'pytest' in req_text or any((project_path / name).exists() for name in ['tests', 'test', 'pytest.ini'])
            if has_pytest:
                stack['test_commands'].append('python -m pytest')

        pyproject_file = project_path / 'pyproject.toml'
        if pyproject_file.exists():
            stack['dependency_files'].append('pyproject.toml')
            pyproject_text = self._read_text_file(pyproject_file).lower()
            if 'pytest' in pyproject_text or any((project_path / name).exists() for name in ['tests', 'test', 'pytest.ini']):
                stack['test_commands'].append('python -m pytest')

        package_file = project_path / 'package.json'
        if package_file.exists():
            stack['dependency_files'].append('package.json')
            package_data = self._read_json_file(package_file)
            dependencies = {}
            dependencies.update(package_data.get('dependencies', {}) or {})
            dependencies.update(package_data.get('devDependencies', {}) or {})
            dependency_names = {name.lower() for name in dependencies}
            if 'react' in dependency_names:
                add_framework('React')
            if 'vue' in dependency_names:
                add_framework('Vue')
            if '@angular/core' in dependency_names:
                add_framework('Angular')
            if 'next' in dependency_names:
                add_framework('Next.js')
            if 'vite' in dependency_names:
                add_framework('Vite')

            scripts = package_data.get('scripts', {}) or {}
            if 'start' in scripts:
                stack['run_commands'].append('npm start')
            elif 'dev' in scripts:
                stack['run_commands'].append('npm run dev')
            if 'test' in scripts:
                stack['test_commands'].append('npm test')

            if (project_path / 'pnpm-lock.yaml').exists():
                stack['package_manager'] = 'pnpm'
            elif (project_path / 'yarn.lock').exists():
                stack['package_manager'] = 'yarn'
            else:
                stack['package_manager'] = 'npm'

        if (project_path / 'go.mod').exists():
            stack['dependency_files'].append('go.mod')
            add_framework('Go')
            stack['run_commands'].append('go run .')
            stack['test_commands'].append('go test ./...')

        if (project_path / 'Cargo.toml').exists():
            stack['dependency_files'].append('Cargo.toml')
            add_framework('Rust')
            stack['run_commands'].append('cargo run')
            stack['test_commands'].append('cargo test')

        if (project_path / 'index.html').exists():
            add_framework('Static HTML')
            stack['run_commands'].append('python -m http.server 8000')

        for entrypoint in ['app.py', 'main.py', 'manage.py', 'index.html', 'package.json']:
            if (project_path / entrypoint).exists():
                stack['entrypoints'].append(entrypoint)

        stack['frameworks'] = stack['frameworks'] or ['Unknown']
        stack['run_commands'] = list(dict.fromkeys(stack['run_commands']))
        stack['test_commands'] = list(dict.fromkeys(stack['test_commands']))
        stack['dependency_files'] = list(dict.fromkeys(stack['dependency_files']))
        return stack

    def _discover_env_vars(self, project_path: Path) -> List[str]:
        """Find environment variable references across common languages."""
        patterns = [
            r'os\.environ(?:\.get)?\(\s*[\'"]([A-Z][A-Z0-9_]{2,})[\'"]',
            r'os\.getenv\(\s*[\'"]([A-Z][A-Z0-9_]{2,})[\'"]',
            r'process\.env\.([A-Z][A-Z0-9_]{2,})',
            r'import\.meta\.env\.([A-Z][A-Z0-9_]{2,})',
            r'env\([\'"]([A-Z][A-Z0-9_]{2,})[\'"]',
            r'\$\{([A-Z][A-Z0-9_]{2,})\}',
        ]
        variables = set()
        for file_path in self._iter_project_files(project_path):
            if not self._is_probably_text_file(file_path):
                continue
            content = self._read_text_file(file_path)
            for pattern in patterns:
                variables.update(re.findall(pattern, content))
        return sorted(variables)

    def _scan_secret_candidates(self, project_path: Path) -> List[Dict[str, str]]:
        """Find likely hard-coded secrets without sending data anywhere."""
        findings = []
        patterns = [
            ('private-key', r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
            ('aws-access-key', r'AKIA[0-9A-Z]{16}'),
            ('github-token', r'gh[pousr]_[A-Za-z0-9_]{20,}'),
            ('generic-secret', r'(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*[\'"]([^\'"\n]{8,})[\'"]'),
        ]
        for file_path in self._iter_project_files(project_path):
            if file_path.name.lower() in {'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml'}:
                continue
            if not self._is_probably_text_file(file_path):
                continue
            content = self._read_text_file(file_path)
            for label, pattern in patterns:
                for match in re.finditer(pattern, content):
                    line_no = content.count('\n', 0, match.start()) + 1
                    findings.append({
                        'type': label,
                        'file': self._project_rel(project_path, file_path),
                        'line': str(line_no),
                    })
        return findings[:50]

    def _audit_project_data(self, project_path: Path) -> Dict[str, Any]:
        """Build a practical local audit report."""
        stack = self._detect_project_stack(project_path)
        issues = []

        def issue(severity: str, message: str, file_path: str = ""):
            issues.append({'severity': severity, 'message': message, 'file': file_path})

        if not (project_path / 'README.md').exists() and not (project_path / 'readme.md').exists():
            issue('medium', 'Missing README.md')
        if not (project_path / '.gitignore').exists():
            issue('medium', 'Missing .gitignore')
        if not any((project_path / name).exists() for name in ['LICENSE', 'LICENSE.md', 'license.txt']):
            issue('low', 'Missing license file')

        requirements_file = project_path / 'requirements.txt'
        if requirements_file.exists():
            for req in self._parse_requirements(requirements_file):
                if not req['pinned']:
                    issue('medium', f"Unpinned Python dependency: {req['raw']}", 'requirements.txt')

        package_file = project_path / 'package.json'
        if package_file.exists():
            package_data = self._read_json_file(package_file)
            if not any((project_path / lock).exists() for lock in ['package-lock.json', 'pnpm-lock.yaml', 'yarn.lock']):
                issue('medium', 'package.json exists without a lockfile', 'package.json')
            scripts = package_data.get('scripts', {}) or {}
            if 'test' not in scripts:
                issue('low', 'package.json has no test script', 'package.json')

        if '.env' in [p.name for p in project_path.glob('.env*') if p.name != '.env.example']:
            issue('high', '.env file is present; make sure it is ignored and never committed')

        for finding in self._scan_secret_candidates(project_path):
            issue('high', f"Possible hard-coded secret ({finding['type']}) at line {finding['line']}", finding['file'])

        test_indicators = ['tests', 'test', '__tests__']
        if not any((project_path / name).exists() for name in test_indicators) and not stack['test_commands']:
            issue('low', 'No obvious tests or test command found')

        if not (project_path / 'Dockerfile').exists():
            issue('low', 'No Dockerfile found; run apd dockerize <project> to generate one')

        severity_cost = {'high': 20, 'medium': 8, 'low': 3}
        score = max(0, 100 - sum(severity_cost.get(item['severity'], 0) for item in issues))
        return {
            'path': str(project_path),
            'score': score,
            'stack': stack,
            'issues': issues,
            'env_vars': self._discover_env_vars(project_path),
        }

    def inspect_project(self, target: str):
        """Show detected stack, commands, and project shape."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        stack = self._detect_project_stack(project_path)
        files = list(self._iter_project_files(project_path, max_size=50 * 1024 * 1024))
        total_size = self.get_directory_size(project_path)
        largest = sorted(
            [p for p in files if p.is_file()],
            key=lambda p: p.stat().st_size if p.exists() else 0,
            reverse=True
        )[:5]

        self._print_title(f"Project Inspect: {project_name}")
        self._render_pairs([
            ("Path", str(project_path)),
            ("Frameworks", ', '.join(stack['frameworks'])),
            ("Languages", ', '.join(f"{k} ({v})" for k, v in sorted(stack['languages'].items())) or 'Unknown'),
            ("Dependency Files", ', '.join(stack['dependency_files']) or 'None'),
            ("Entrypoints", ', '.join(stack['entrypoints']) or 'None'),
            ("Size", self.format_size(total_size)),
        ])

        self._print_section("Run Commands")
        for command in stack['run_commands'] or ['No obvious run command detected']:
            print(f"  {command}")

        self._print_section("Test Commands")
        for command in stack['test_commands'] or ['No obvious test command detected']:
            print(f"  {command}")

        env_vars = self._discover_env_vars(project_path)
        self._print_section("Environment Variables")
        print("  " + (', '.join(env_vars) if env_vars else 'None detected'))

        self._print_section("Largest Files")
        for file_path in largest:
            print(f"  {self.format_size(file_path.stat().st_size):>10}  {self._project_rel(project_path, file_path)}")

    def audit_project(self, target: str, json_output: bool = False, fix: bool = False):
        """Run a local quality and security audit."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        report = self._audit_project_data(project_path)
        if fix:
            self._apply_project_fixes(project_path, report)
            report = self._audit_project_data(project_path)

        if json_output:
            print(json.dumps(report, indent=2))
            return

        self._print_title(f"Project Audit: {project_name}", f"Score: {report['score']}/100")
        if not report['issues']:
            print("No issues found.")
            return

        rows = []
        for item in report['issues']:
            rows.append([
                item['severity'].upper(),
                item.get('file', ''),
                item['message'],
            ])
        self._render_table(["Severity", "File", "Issue"], rows)

    def _apply_project_fixes(self, project_path: Path, report: Dict[str, Any]):
        """Apply safe audit fixes that do not overwrite existing files."""
        gitignore = project_path / '.gitignore'
        if not gitignore.exists():
            gitignore.write_text(
                "\n".join([
                    "__pycache__/",
                    "*.py[cod]",
                    ".env",
                    ".venv/",
                    "venv/",
                    "env/",
                    "node_modules/",
                    "dist/",
                    "build/",
                    ".DS_Store",
                    "",
                ]),
                encoding='utf-8',
            )
            print("Created .gitignore")

        env_example = project_path / '.env.example'
        if report.get('env_vars') and not env_example.exists():
            env_example.write_text(
                "\n".join(f"{name}=" for name in report['env_vars']) + "\n",
                encoding='utf-8',
            )
            print("Created .env.example")

    def generate_env_example(self, target: str, force: bool = False):
        """Generate .env.example from detected environment variables."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        env_vars = self._discover_env_vars(project_path)
        env_example = project_path / '.env.example'
        if env_example.exists() and not force:
            print(f".env.example already exists: {env_example}")
            print("Use --force to replace it.")
            return

        lines = [
            "# Generated by APD",
            f"# Project: {project_name}",
            "",
        ]
        if env_vars:
            lines.extend(f"{name}=" for name in env_vars)
        else:
            lines.append("# No environment variable references were detected.")

        env_example.write_text("\n".join(lines) + "\n", encoding='utf-8')
        print(f"Generated {env_example}")

    def export_project_blueprint(self, target: str, stdout: bool = False):
        """Export a reproducible project blueprint."""
        project_path, project_name, project_info = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        stack = self._detect_project_stack(project_path)
        blueprint = {
            'schema': 'apd.blueprint.v1',
            'name': project_name,
            'path': str(project_path),
            'generated_at': datetime.now().isoformat(),
            'registered': bool(project_info),
            'stack': stack,
            'env_vars': self._discover_env_vars(project_path),
            'audit_score': self._audit_project_data(project_path)['score'],
            'files': {
                'count': len(list(self._iter_project_files(project_path, max_size=50 * 1024 * 1024))),
                'size': self.get_directory_size(project_path),
            },
        }

        if stdout:
            print(json.dumps(blueprint, indent=2))
            return

        output_file = project_path / 'apd-blueprint.json'
        output_file.write_text(json.dumps(blueprint, indent=2) + "\n", encoding='utf-8')
        print(f"Blueprint exported: {output_file}")

    def dockerize_project(self, target: str, force: bool = False):
        """Generate Dockerfile and .dockerignore based on detected stack."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        dockerfile = project_path / 'Dockerfile'
        dockerignore = project_path / '.dockerignore'
        if dockerfile.exists() and not force:
            print(f"Dockerfile already exists: {dockerfile}")
            print("Use --force to replace it.")
            return

        stack = self._detect_project_stack(project_path)
        frameworks = {name.lower() for name in stack['frameworks']}
        if 'flask' in frameworks or 'django' in frameworks or 'fastapi' in frameworks or (project_path / 'requirements.txt').exists():
            port = '8000' if 'django' in frameworks or 'fastapi' in frameworks else '5000'
            command = 'python manage.py runserver 0.0.0.0:8000' if 'django' in frameworks else stack['run_commands'][0] if stack['run_commands'] else 'python app.py'
            content = f"""FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
COPY . .
EXPOSE {port}
CMD {json.dumps(command.split())}
"""
        elif (project_path / 'package.json').exists():
            run_command = 'npm start' if 'npm start' in stack['run_commands'] else 'npm run dev'
            content = f"""FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD {json.dumps(run_command.split())}
"""
        elif (project_path / 'index.html').exists():
            content = """FROM nginx:1.27-alpine
COPY . /usr/share/nginx/html
EXPOSE 80
"""
        else:
            content = """FROM alpine:3.20
WORKDIR /app
COPY . .
CMD ["sh"]
"""

        dockerfile.write_text(content, encoding='utf-8')
        if not dockerignore.exists() or force:
            dockerignore.write_text(
                "\n".join([
                    ".git",
                    "__pycache__/",
                    "*.pyc",
                    ".env",
                    ".venv/",
                    "venv/",
                    "env/",
                    "node_modules/",
                    "dist/",
                    "build/",
                    ".apd/",
                    "",
                ]),
                encoding='utf-8',
            )
        print(f"Generated Docker assets for {project_name}")
        print(f"  {dockerfile}")
        print(f"  {dockerignore}")

    def create_ci_workflow(self, target: str, force: bool = False):
        """Generate a GitHub Actions workflow from detected stack."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        workflow_dir = project_path / '.github' / 'workflows'
        workflow_file = workflow_dir / 'apd-ci.yml'
        if workflow_file.exists() and not force:
            print(f"Workflow already exists: {workflow_file}")
            print("Use --force to replace it.")
            return

        stack = self._detect_project_stack(project_path)
        steps = ["      - uses: actions/checkout@v4"]
        if (project_path / 'requirements.txt').exists() or (project_path / 'pyproject.toml').exists():
            steps.extend([
                "      - uses: actions/setup-python@v5",
                "        with:",
                "          python-version: '3.12'",
                "      - run: python -m pip install --upgrade pip",
                "      - run: if [ -f requirements.txt ]; then pip install -r requirements.txt; fi",
                "      - run: python -m compileall .",
            ])
            if stack['test_commands']:
                steps.append(f"      - run: {stack['test_commands'][0]}")
        if (project_path / 'package.json').exists():
            steps.extend([
                "      - uses: actions/setup-node@v4",
                "        with:",
                "          node-version: '20'",
                "      - run: npm install",
            ])
            if stack['test_commands']:
                steps.append(f"      - run: {stack['test_commands'][0]}")
        if (project_path / 'go.mod').exists():
            steps.extend([
                "      - uses: actions/setup-go@v5",
                "        with:",
                "          go-version: '1.22'",
                "      - run: go test ./...",
            ])
        if (project_path / 'Cargo.toml').exists():
            steps.extend([
                "      - run: cargo test",
            ])
        if len(steps) == 1:
            steps.append("      - run: echo \"No build system detected; repository checkout succeeded.\"")

        workflow = f"""name: APD CI

on:
  push:
  pull_request:

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
{chr(10).join(steps)}
"""
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_file.write_text(workflow, encoding='utf-8')
        print(f"Generated CI workflow for {project_name}: {workflow_file}")

    def snapshot_project(self, target: str, label: Optional[str] = None):
        """Create a restorable project snapshot."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        safe_label = self._sanitize_template_name(label or datetime.now().strftime('%Y%m%d-%H%M%S'))
        snapshot_dir = self.projects_dir / 'snapshots'
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_file = snapshot_dir / f"{project_name}-{safe_label}.zip"
        metadata = {
            'schema': 'apd.snapshot.v1',
            'project': project_name,
            'source': str(project_path),
            'created_at': datetime.now().isoformat(),
            'audit_score': self._audit_project_data(project_path)['score'],
        }

        skip_dirs = self._project_skip_dirs()
        with zipfile.ZipFile(snapshot_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('.apd-snapshot.json', json.dumps(metadata, indent=2))
            for root, dirs, files in os.walk(project_path):
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                for filename in files:
                    file_path = Path(root) / filename
                    zipf.write(file_path, file_path.relative_to(project_path))

        print(f"Snapshot created: {snapshot_file}")
        print(f"Size: {self.format_size(snapshot_file.stat().st_size)}")

    def restore_snapshot(self, snapshot_path: str, destination: Optional[str] = None, force: bool = False):
        """Restore a project snapshot safely."""
        archive_path = Path(snapshot_path).expanduser()
        if not archive_path.is_absolute():
            archive_path = Path.cwd() / archive_path
        if not archive_path.exists():
            print(f"Snapshot not found: {archive_path}")
            return

        if destination:
            target_dir = Path(destination).expanduser()
            if not target_dir.is_absolute():
                target_dir = Path.cwd() / target_dir
        else:
            target_dir = Path.cwd() / archive_path.stem

        if target_dir.exists() and not force:
            print(f"Destination already exists: {target_dir}")
            print("Use --force to replace it.")
            return
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path, 'r') as zipf:
            for info in zipf.infolist():
                relative = self._safe_relative_archive_path(info.filename)
                if relative is None:
                    continue
                target_path = target_dir / relative
                if info.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                    continue
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zipf.open(info, 'r') as src, open(target_path, 'wb') as dst:
                    shutil.copyfileobj(src, dst)

        print(f"Snapshot restored to: {target_dir}")

    def score_template_quality(self, template_name: str):
        """Score a template for contest-visible quality."""
        template_dir = self.templates_dir / template_name
        if not template_dir.exists():
            print(f"Template not found: {template_name}")
            return

        manifest = self.get_template_manifest(template_name)
        score = 100
        notes = []

        def penalty(points: int, message: str):
            nonlocal score
            score -= points
            notes.append([str(points), message])

        if not manifest or not (template_dir / 'manifest.json').exists():
            penalty(20, 'Missing manifest.json')
        else:
            if not manifest.data.get('description'):
                penalty(8, 'Manifest has no description')
            if not manifest.data.get('variables'):
                penalty(6, 'Manifest declares no variables')
            if not manifest.data.get('ignore_patterns'):
                penalty(6, 'Manifest has no ignore_patterns')
            is_valid, errors = manifest.validate()
            for error in errors:
                penalty(8, error)

        if not any((template_dir / name).exists() for name in ['README.md', 'readme.md']):
            penalty(8, 'No README.md in template')
        if any((template_dir / bad).exists() for bad in ['node_modules', 'venv', '.venv', '.git']):
            penalty(15, 'Template includes generated or repository directories')

        placeholder_count = 0
        for file_path in self._iter_project_files(template_dir):
            if file_path.name == 'manifest.json' or not self._is_probably_text_file(file_path):
                continue
            placeholder_count += len(self._extract_placeholders(self._read_text_file(file_path)))
        if placeholder_count == 0:
            penalty(8, 'No template placeholders found')

        score = max(0, score)
        self._print_title(f"Template Score: {template_name}", f"{score}/100")
        self._render_pairs([
            ("Path", str(template_dir)),
            ("Files", str(len(list(template_dir.rglob('*'))))),
            ("Placeholders", str(placeholder_count)),
            ("Framework", manifest.data.get('framework', 'custom') if manifest else 'custom'),
        ])
        if notes:
            self._print_section("Deductions")
            self._render_table(["Points", "Reason"], notes)
        else:
            print("No deductions.")

    def _command_exists(self, command: str) -> bool:
        """Return whether an executable is available."""
        return shutil.which(command) is not None

    def _run_project_command(self, project_path: Path, command: str, dry_run: bool = False) -> int:
        """Run a detected project command with shell-compatible parsing."""
        print(f"Project: {project_path}")
        print(f"Command: {command}")
        if dry_run:
            return 0

        try:
            if platform.system() == 'Windows':
                result = subprocess.run(command, cwd=project_path, shell=True)
            else:
                result = subprocess.run(shlex.split(command), cwd=project_path)
            return result.returncode
        except FileNotFoundError as e:
            print(f"Command not found: {e}")
            return 127
        except Exception as e:
            print(f"Command failed: {e}")
            return 1

    def _preferred_install_command(self, project_path: Path) -> Optional[str]:
        """Choose an install command for an existing project."""
        if (project_path / 'requirements.txt').exists():
            return f"{sys.executable} -m pip install -r requirements.txt"
        if (project_path / 'pyproject.toml').exists():
            return f"{sys.executable} -m pip install -e ."
        if (project_path / 'package.json').exists():
            if (project_path / 'pnpm-lock.yaml').exists():
                return "pnpm install"
            if (project_path / 'yarn.lock').exists():
                return "yarn install"
            return "npm install"
        if (project_path / 'go.mod').exists():
            return "go mod download"
        if (project_path / 'Cargo.toml').exists():
            return "cargo fetch"
        return None

    def onboard_project(self, target: str, install: bool = False):
        """Register and prepare an existing project folder."""
        project_path, project_name, project_info = self._resolve_project_target(target)
        if not project_path or not project_path.exists() or not project_path.is_dir():
            print(f"Project folder not found: {target}")
            return

        stack = self._detect_project_stack(project_path)
        project_type = stack['frameworks'][0].lower().replace(' ', '-') if stack['frameworks'] else 'custom'
        self.register_project(project_path, project_name, project_type)

        if not (project_path / '.gitignore').exists():
            self._apply_project_fixes(project_path, {'env_vars': self._discover_env_vars(project_path)})
        if self._discover_env_vars(project_path) and not (project_path / '.env.example').exists():
            self.generate_env_example(str(project_path))

        self._print_title(f"Onboarded: {project_name}")
        self._render_pairs([
            ("Path", str(project_path)),
            ("Detected", ', '.join(stack['frameworks'])),
            ("Registered", "Yes"),
            ("Install Command", self._preferred_install_command(project_path) or "None detected"),
        ])

        if install:
            install_command = self._preferred_install_command(project_path)
            if install_command:
                code = self._run_project_command(project_path, install_command)
                print(f"Install exited with code {code}")
            else:
                print("No install command detected.")

    def run_project(self, target: str, dry_run: bool = False):
        """Run a project with the best detected run command."""
        project_path, _, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        stack = self._detect_project_stack(project_path)
        if not stack['run_commands']:
            print("No run command detected.")
            print("Try apd inspect <project> to see what APD found.")
            return

        code = self._run_project_command(project_path, stack['run_commands'][0], dry_run=dry_run)
        if not dry_run:
            print(f"Run exited with code {code}")

    def test_project(self, target: str, dry_run: bool = False):
        """Run detected test command or a safe syntax check."""
        project_path, _, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        stack = self._detect_project_stack(project_path)
        command = stack['test_commands'][0] if stack['test_commands'] else None
        if not command and stack['languages'].get('Python'):
            command = f"{sys.executable} -m compileall ."
        if not command:
            print("No test or syntax-check command detected.")
            return

        code = self._run_project_command(project_path, command, dry_run=dry_run)
        if not dry_run:
            print(f"Test exited with code {code}")

    def generate_readme(self, target: str, force: bool = False):
        """Generate a useful README.md from detected project metadata."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        readme = project_path / 'README.md'
        if readme.exists() and not force:
            print(f"README.md already exists: {readme}")
            print("Use --force to replace it.")
            return

        stack = self._detect_project_stack(project_path)
        install_command = self._preferred_install_command(project_path)
        run_commands = stack['run_commands'] or ['No run command detected yet.']
        test_commands = stack['test_commands'] or ['No test command detected yet.']
        env_vars = self._discover_env_vars(project_path)

        content = [
            f"# {project_name}",
            "",
            "Generated by APD from the current project structure.",
            "",
            "## Stack",
            "",
            f"- Frameworks: {', '.join(stack['frameworks'])}",
            f"- Languages: {', '.join(f'{k} ({v})' for k, v in sorted(stack['languages'].items())) or 'Unknown'}",
            f"- Entrypoints: {', '.join(stack['entrypoints']) or 'None detected'}",
            "",
            "## Setup",
            "",
            f"```sh\n{install_command or '# No install command detected'}\n```",
            "",
            "## Run",
            "",
            "```sh",
            *run_commands,
            "```",
            "",
            "## Test",
            "",
            "```sh",
            *test_commands,
            "```",
            "",
        ]
        if env_vars:
            content.extend([
                "## Environment",
                "",
                "Create `.env` from `.env.example` and fill in:",
                "",
                *[f"- `{name}`" for name in env_vars],
                "",
            ])

        readme.write_text("\n".join(content), encoding='utf-8')
        print(f"Generated README: {readme}")

    def generate_license(self, target: str, license_name: str = "MIT", force: bool = False):
        """Generate a common license file."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        license_file = project_path / 'LICENSE'
        if license_file.exists() and not force:
            print(f"LICENSE already exists: {license_file}")
            print("Use --force to replace it.")
            return

        year = datetime.now().year
        author = self.config['PROJECT'].get('author', getpass.getuser())
        normalized = license_name.strip().lower()
        if normalized != 'mit':
            print("Only MIT generation is built in right now; writing MIT.")

        text = f"""MIT License

Copyright (c) {year} {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
        license_file.write_text(text, encoding='utf-8')
        print(f"Generated LICENSE: {license_file}")

    def generate_editorconfig(self, target: str, force: bool = False):
        """Generate a sensible .editorconfig."""
        project_path, _, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        editorconfig = project_path / '.editorconfig'
        if editorconfig.exists() and not force:
            print(f".editorconfig already exists: {editorconfig}")
            print("Use --force to replace it.")
            return

        editorconfig.write_text("""root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
indent_style = space
indent_size = 4
trim_trailing_whitespace = true

[*.{js,jsx,ts,tsx,json,css,html,yml,yaml,md}]
indent_size = 2

[*.md]
trim_trailing_whitespace = false
""", encoding='utf-8')
        print(f"Generated .editorconfig: {editorconfig}")

    def harden_project(self, target: str, force: bool = False):
        """Apply practical hardening files for a project."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        self._apply_project_fixes(project_path, {'env_vars': self._discover_env_vars(project_path)})
        if not (project_path / '.editorconfig').exists() or force:
            self.generate_editorconfig(str(project_path), force=force)
        if not (project_path / '.env.example').exists() or force:
            self.generate_env_example(str(project_path), force=force)
        if not (project_path / 'README.md').exists() or force:
            self.generate_readme(str(project_path), force=force)

        self._print_title(f"Hardened: {project_name}")
        self.audit_project(str(project_path))

    def doctor_fix(self):
        """Apply safe APD setup repairs."""
        self.ensure_directories()
        changed = []

        if 'DEFAULT' not in self.config:
            self.config['DEFAULT'] = {}
        if 'PROJECT' not in self.config:
            self.config['PROJECT'] = {}
        if 'MIRROR' not in self.config:
            self.config['MIRROR'] = {}

        defaults = {
            ('DEFAULT', 'default_template'): 'html',
            ('DEFAULT', 'editor'): self.detect_default_editor(),
            ('DEFAULT', 'telemetry'): 'false',
            ('DEFAULT', 'first_run'): 'false',
            ('PROJECT', 'auto_git'): 'false',
            ('PROJECT', 'auto_open'): 'false',
            ('PROJECT', 'auto_venv'): 'true',
            ('PROJECT', 'license'): 'MIT',
            ('PROJECT', 'author'): getpass.getuser(),
            ('PROJECT', 'email'): f"{getpass.getuser()}@localhost",
            ('MIRROR', 'enabled'): 'false',
            ('MIRROR', 'url'): 'https://mirror-pypi.runflare.com/simple',
            ('MIRROR', 'trusted_host'): 'mirror-pypi.runflare.com',
        }
        for (section, option), value in defaults.items():
            target = self.config['DEFAULT'] if section == 'DEFAULT' else self.config[section]
            if option not in target:
                target[option] = value
                changed.append(f"{section}.{option}")

        self.save_config()
        if changed:
            print("Repaired config keys:")
            for item in changed:
                print(f"  {item}")
        else:
            print("APD config already has required keys.")

        if not self.list_available_templates():
            print("No templates installed. Run apd --setup to install defaults.")
        else:
            print(f"Templates available: {len(self.list_available_templates())}")

    def show_dependencies(self, target: str):
        """Show dependency files and parsed dependencies."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        self._print_title(f"Dependencies: {project_name}")
        rows = []

        requirements_file = project_path / 'requirements.txt'
        if requirements_file.exists():
            for req in self._parse_requirements(requirements_file):
                rows.append(['Python', req['name'], req['raw'], 'Pinned' if req['pinned'] else 'Unpinned'])

        package_file = project_path / 'package.json'
        if package_file.exists():
            package_data = self._read_json_file(package_file)
            for group in ['dependencies', 'devDependencies', 'optionalDependencies']:
                for name, version in (package_data.get(group, {}) or {}).items():
                    rows.append(['Node', name, str(version), group])

        pyproject_file = project_path / 'pyproject.toml'
        if pyproject_file.exists():
            rows.append(['Python', 'pyproject.toml', 'Present', 'Build metadata'])

        if (project_path / 'go.mod').exists():
            rows.append(['Go', 'go.mod', 'Present', 'Module'])
        if (project_path / 'Cargo.toml').exists():
            rows.append(['Rust', 'Cargo.toml', 'Present', 'Package'])

        if rows:
            self._render_table(['Ecosystem', 'Name', 'Version/Spec', 'Status'], rows)
        else:
            print("No dependency files detected.")

    def list_project_scripts(self, target: str):
        """List package scripts and detected APD commands."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        stack = self._detect_project_stack(project_path)
        rows = []
        for command in stack['run_commands']:
            rows.append(['run', command])
        for command in stack['test_commands']:
            rows.append(['test', command])

        package_file = project_path / 'package.json'
        if package_file.exists():
            scripts = (self._read_json_file(package_file).get('scripts', {}) or {})
            for name, command in scripts.items():
                rows.append([f'npm:{name}', command])

        self._print_title(f"Scripts: {project_name}")
        if rows:
            self._render_table(['Name', 'Command'], rows)
        else:
            print("No scripts detected.")

    def find_project_ports(self, target: str):
        """Find likely ports referenced by project files."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        patterns = [
            r'\b(?:PORT|port)\s*[:=]\s*[\'"]?(\d{2,5})',
            r'\.listen\(\s*(\d{2,5})',
            r'app\.run\([^)]*port\s*=\s*(\d{2,5})',
            r'localhost:(\d{2,5})',
            r'127\.0\.0\.1:(\d{2,5})',
        ]
        ports = {}
        for file_path in self._iter_project_files(project_path):
            if not self._is_probably_text_file(file_path):
                continue
            content = self._read_text_file(file_path)
            for pattern in patterns:
                for port in re.findall(pattern, content):
                    port_int = int(port)
                    if 1 <= port_int <= 65535:
                        ports.setdefault(port, set()).add(self._project_rel(project_path, file_path))

        self._print_title(f"Ports: {project_name}")
        if not ports:
            print("No explicit ports detected.")
            return

        rows = []
        for port, files in sorted(ports.items(), key=lambda item: int(item[0])):
            rows.append([port, ', '.join(sorted(files)[:3])])
        self._render_table(['Port', 'Files'], rows)

    def check_environment(self, target: str):
        """Compare detected env vars with .env and .env.example."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        detected = set(self._discover_env_vars(project_path))
        declared = set()
        for env_file_name in ['.env.example', '.env']:
            env_file = project_path / env_file_name
            if env_file.exists():
                for line in self._read_text_file(env_file).splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith('#') or '=' not in stripped:
                        continue
                    declared.add(stripped.split('=', 1)[0].strip())

        missing = sorted(detected - declared)
        unused = sorted(declared - detected)

        self._print_title(f"Environment Check: {project_name}")
        self._render_pairs([
            ("Detected In Code", ', '.join(sorted(detected)) or 'None'),
            ("Declared In Env Files", ', '.join(sorted(declared)) or 'None'),
        ])
        if missing:
            self._print_section("Missing Declarations")
            for name in missing:
                print(f"  {name}")
        if unused:
            self._print_section("Declared But Not Detected")
            for name in unused:
                print(f"  {name}")
        if not missing and not unused:
            print("Environment declarations match detected references.")

    def _lock_data_for_project(self, project_path: Path, project_name: str) -> Dict[str, Any]:
        """Build APD lock data with file checksums."""
        files = []
        for file_path in self._iter_project_files(project_path, max_size=20 * 1024 * 1024):
            if not file_path.is_file():
                continue
            rel = self._project_rel(project_path, file_path)
            if rel in {'apd-lock.json'}:
                continue
            try:
                digest = hashlib.sha256()
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b''):
                        digest.update(chunk)
                files.append({
                    'path': rel,
                    'size': file_path.stat().st_size,
                    'sha256': digest.hexdigest(),
                })
            except Exception:
                continue

        return {
            'schema': 'apd.lock.v1',
            'project': project_name,
            'generated_at': datetime.now().isoformat(),
            'files': sorted(files, key=lambda item: item['path']),
        }

    def lock_project(self, target: str, force: bool = False):
        """Write apd-lock.json for reproducible file verification."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        lock_file = project_path / 'apd-lock.json'
        if lock_file.exists() and not force:
            print(f"apd-lock.json already exists: {lock_file}")
            print("Use --force to replace it.")
            return

        data = self._lock_data_for_project(project_path, project_name)
        lock_file.write_text(json.dumps(data, indent=2) + "\n", encoding='utf-8')
        print(f"Lock written: {lock_file}")
        print(f"Files tracked: {len(data['files'])}")

    def verify_project_lock(self, target: str):
        """Verify project files against apd-lock.json."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        lock_file = project_path / 'apd-lock.json'
        if not lock_file.exists():
            print(f"No apd-lock.json found in {project_path}")
            print("Run apd lock <project> first.")
            return

        expected = self._read_json_file(lock_file)
        current = self._lock_data_for_project(project_path, project_name)
        expected_map = {item['path']: item for item in expected.get('files', [])}
        current_map = {item['path']: item for item in current.get('files', [])}

        missing = sorted(set(expected_map) - set(current_map))
        added = sorted(set(current_map) - set(expected_map))
        changed = sorted(
            path for path in set(expected_map) & set(current_map)
            if expected_map[path].get('sha256') != current_map[path].get('sha256')
        )

        self._print_title(f"Lock Verify: {project_name}")
        self._render_pairs([
            ("Missing", str(len(missing))),
            ("Added", str(len(added))),
            ("Changed", str(len(changed))),
        ])
        for title, items in [('Missing', missing), ('Added', added), ('Changed', changed)]:
            if items:
                self._print_section(title)
                for item in items[:20]:
                    print(f"  {item}")
                if len(items) > 20:
                    print(f"  ... and {len(items) - 20} more")
        if not missing and not added and not changed:
            print("Project matches apd-lock.json.")

    def clean_project(self, target: str, dry_run: bool = False):
        """Remove common generated caches and build folders."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        names = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'htmlcov', 'dist', 'build'}
        candidates = []
        for root, dirs, files in os.walk(project_path):
            for dir_name in list(dirs):
                if dir_name in names:
                    candidates.append(Path(root) / dir_name)
            for file_name in files:
                if file_name.endswith(('.pyc', '.pyo')) or file_name == '.coverage':
                    candidates.append(Path(root) / file_name)

        self._print_title(f"Clean Project: {project_name}")
        if not candidates:
            print("Nothing to clean.")
            return
        for item in candidates:
            print(f"  {item}")
        if dry_run:
            print(f"Dry run: {len(candidates)} item(s) would be removed.")
            return

        removed = 0
        for item in candidates:
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                elif item.exists():
                    item.unlink()
                removed += 1
            except Exception as e:
                print(f"Could not remove {item}: {e}")
        print(f"Removed {removed} item(s).")

    def deploy_plan(self, target: str):
        """Print practical deployment steps for the detected project."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        stack = self._detect_project_stack(project_path)
        self._print_title(f"Deploy Plan: {project_name}")
        steps = []
        install_command = self._preferred_install_command(project_path)
        if install_command:
            steps.append(("Install", install_command))
        for command in stack['test_commands'] or ([f"{sys.executable} -m compileall ."] if stack['languages'].get('Python') else []):
            steps.append(("Verify", command))
        if not (project_path / 'Dockerfile').exists():
            steps.append(("Container", f"apd dockerize {project_path}"))
        else:
            steps.append(("Container", "docker build -t <image-name> ."))
        if not (project_path / '.github' / 'workflows' / 'apd-ci.yml').exists():
            steps.append(("CI", f"apd ci {project_path}"))
        if self._discover_env_vars(project_path) and not (project_path / '.env.example').exists():
            steps.append(("Environment", f"apd env {project_path}"))
        for command in stack['run_commands']:
            steps.append(("Run", command))

        if steps:
            self._render_table(['Stage', 'Action'], [[stage, action] for stage, action in steps])
        else:
            print("No deployment steps detected.")

    def _dependency_records(self, project_path: Path) -> List[Dict[str, str]]:
        """Collect dependencies in a simple SBOM-friendly shape."""
        records = []
        requirements_file = project_path / 'requirements.txt'
        if requirements_file.exists():
            for req in self._parse_requirements(requirements_file):
                version = ''
                if '==' in req['raw']:
                    version = req['raw'].split('==', 1)[1].split(';', 1)[0].strip()
                records.append({
                    'type': 'pypi',
                    'name': req['name'],
                    'version': version,
                    'source': 'requirements.txt',
                    'specifier': req['raw'],
                })

        package_file = project_path / 'package.json'
        if package_file.exists():
            package_data = self._read_json_file(package_file)
            for group in ['dependencies', 'devDependencies', 'optionalDependencies']:
                for name, version in (package_data.get(group, {}) or {}).items():
                    records.append({
                        'type': 'npm',
                        'name': name,
                        'version': str(version),
                        'source': f'package.json:{group}',
                        'specifier': str(version),
                    })
        return records

    def generate_sbom(self, target: str, output: Optional[str] = None, stdout: bool = False):
        """Generate a lightweight Software Bill of Materials JSON."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        sbom = {
            'schema': 'apd.sbom.v1',
            'project': project_name,
            'path': str(project_path),
            'generated_at': datetime.now().isoformat(),
            'components': self._dependency_records(project_path),
        }
        if stdout:
            print(json.dumps(sbom, indent=2))
            return

        output_path = Path(output).expanduser() if output else project_path / 'apd-sbom.json'
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        output_path.write_text(json.dumps(sbom, indent=2) + "\n", encoding='utf-8')
        print(f"SBOM written: {output_path}")
        print(f"Components: {len(sbom['components'])}")

    def dependency_graph(self, target: str, output: Optional[str] = None):
        """Generate a DOT dependency graph."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        safe_project = re.sub(r'[^A-Za-z0-9_]', '_', project_name)
        lines = [
            f'digraph {safe_project} {{',
            '  rankdir=LR;',
            f'  "{project_name}" [shape=box, style=filled, fillcolor="#dff3ff"];',
        ]
        for dep in self._dependency_records(project_path):
            label = dep['name']
            if dep.get('version'):
                label += f"\\n{dep['version']}"
            lines.append(f'  "{project_name}" -> "{label}";')
            lines.append(f'  "{label}" [shape=ellipse];')
        lines.append('}')
        graph = "\n".join(lines) + "\n"

        output_path = Path(output).expanduser() if output else project_path / 'apd-deps.dot'
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        output_path.write_text(graph, encoding='utf-8')
        print(f"Dependency graph written: {output_path}")

    def project_metrics(self, target: str):
        """Show project metrics useful for judging complexity."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        rows = []
        totals = {'files': 0, 'lines': 0, 'bytes': 0}
        by_ext = {}
        for file_path in self._iter_project_files(project_path, max_size=5 * 1024 * 1024):
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower() or '[none]'
            stat = file_path.stat()
            lines = 0
            if self._is_probably_text_file(file_path):
                lines = len(self._read_text_file(file_path).splitlines())
            data = by_ext.setdefault(ext, {'files': 0, 'lines': 0, 'bytes': 0})
            data['files'] += 1
            data['lines'] += lines
            data['bytes'] += stat.st_size
            totals['files'] += 1
            totals['lines'] += lines
            totals['bytes'] += stat.st_size

        self._print_title(f"Metrics: {project_name}")
        self._render_pairs([
            ("Files", str(totals['files'])),
            ("Text Lines", str(totals['lines'])),
            ("Size", self.format_size(totals['bytes'])),
        ])
        for ext, data in sorted(by_ext.items(), key=lambda item: item[1]['bytes'], reverse=True)[:12]:
            rows.append([ext, str(data['files']), str(data['lines']), self.format_size(data['bytes'])])
        if rows:
            self._render_table(['Ext', 'Files', 'Lines', 'Size'], rows)

    def compare_projects(self, left: str, right: str):
        """Compare two project folders by stack, dependencies, and files."""
        left_path, left_name, _ = self._resolve_project_target(left)
        right_path, right_name, _ = self._resolve_project_target(right)
        if not left_path or not left_path.exists():
            print(f"Project not found: {left}")
            return
        if not right_path or not right_path.exists():
            print(f"Project not found: {right}")
            return

        left_files = {self._project_rel(left_path, p) for p in self._iter_project_files(left_path)}
        right_files = {self._project_rel(right_path, p) for p in self._iter_project_files(right_path)}
        left_deps = {f"{d['type']}:{d['name']}" for d in self._dependency_records(left_path)}
        right_deps = {f"{d['type']}:{d['name']}" for d in self._dependency_records(right_path)}
        left_stack = self._detect_project_stack(left_path)
        right_stack = self._detect_project_stack(right_path)

        self._print_title(f"Compare: {left_name} vs {right_name}")
        self._render_pairs([
            ("Left frameworks", ', '.join(left_stack['frameworks'])),
            ("Right frameworks", ', '.join(right_stack['frameworks'])),
            ("Files only in left", str(len(left_files - right_files))),
            ("Files only in right", str(len(right_files - left_files))),
            ("Shared files", str(len(left_files & right_files))),
            ("Deps only in left", str(len(left_deps - right_deps))),
            ("Deps only in right", str(len(right_deps - left_deps))),
        ])

    def scaffold_tests(self, target: str, force: bool = False):
        """Create a minimal test scaffold for common project types."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        stack = self._detect_project_stack(project_path)
        created = []
        if stack['languages'].get('Python'):
            tests_dir = project_path / 'tests'
            test_file = tests_dir / 'test_smoke.py'
            if test_file.exists() and not force:
                print(f"Test already exists: {test_file}")
            else:
                tests_dir.mkdir(parents=True, exist_ok=True)
                test_file.write_text("""def test_smoke():
    assert True
""", encoding='utf-8')
                created.append(str(test_file))

        if (project_path / 'package.json').exists():
            test_dir = project_path / '__tests__'
            test_file = test_dir / 'smoke.test.js'
            if test_file.exists() and not force:
                print(f"Test already exists: {test_file}")
            else:
                test_dir.mkdir(parents=True, exist_ok=True)
                test_file.write_text("""test('smoke', () => {
  expect(true).toBe(true);
});
""", encoding='utf-8')
                created.append(str(test_file))

        if created:
            print(f"Created test scaffold for {project_name}:")
            for item in created:
                print(f"  {item}")
        else:
            print("No supported test scaffold target detected.")

    def release_project(self, target: str, label: Optional[str] = None):
        """Create a release ZIP with manifest, SBOM, and blueprint inside."""
        project_path, project_name, _ = self._resolve_project_target(target)
        if not project_path or not project_path.exists():
            print(f"Project not found: {target}")
            return

        release_label = self._sanitize_template_name(label or datetime.now().strftime('%Y%m%d-%H%M%S'))
        release_dir = self.projects_dir / 'releases'
        release_dir.mkdir(parents=True, exist_ok=True)
        release_file = release_dir / f"{project_name}-{release_label}.zip"
        audit = self._audit_project_data(project_path)
        sbom = {
            'schema': 'apd.sbom.v1',
            'project': project_name,
            'generated_at': datetime.now().isoformat(),
            'components': self._dependency_records(project_path),
        }
        manifest = {
            'schema': 'apd.release.v1',
            'project': project_name,
            'source': str(project_path),
            'created_at': datetime.now().isoformat(),
            'audit_score': audit['score'],
            'file_count': len(list(self._iter_project_files(project_path, max_size=50 * 1024 * 1024))),
        }
        skip_dirs = self._project_skip_dirs()
        with zipfile.ZipFile(release_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('APD-RELEASE.json', json.dumps(manifest, indent=2))
            zipf.writestr('APD-SBOM.json', json.dumps(sbom, indent=2))
            zipf.writestr('APD-AUDIT.json', json.dumps(audit, indent=2))
            for root, dirs, files in os.walk(project_path):
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                for filename in files:
                    file_path = Path(root) / filename
                    rel = file_path.relative_to(project_path)
                    if str(rel) == release_file.name:
                        continue
                    zipf.write(file_path, rel)
        print(f"Release created: {release_file}")
        print(f"Size: {self.format_size(release_file.stat().st_size)}")
        print(f"Audit score: {audit['score']}/100")

    def audit_all_projects(self):
        """Audit all registered projects and summarize scores."""
        projects = self._load_projects_db()
        if not projects:
            print("No registered projects.")
            return
        rows = []
        for project in projects:
            path = Path(project.get('path', ''))
            if not path.exists():
                rows.append([project.get('name', 'Unknown'), 'Missing', '0', 'Path not found'])
                continue
            report = self._audit_project_data(path)
            high = sum(1 for item in report['issues'] if item['severity'] == 'high')
            medium = sum(1 for item in report['issues'] if item['severity'] == 'medium')
            low = sum(1 for item in report['issues'] if item['severity'] == 'low')
            rows.append([project.get('name', path.name), str(report['score']), f"H{high}/M{medium}/L{low}", str(path)])
        self._print_title("Registered Project Audit")
        self._render_table(['Project', 'Score', 'Issues', 'Path'], rows)

    def launch_gui(self):
        """Launch the APD GUI application."""
        gui = EmbeddedAPDGUI(self)
        gui.run()

    def run(self, args):
        """Main CLI entry point."""
        if self.config['DEFAULT'].getboolean('first_run', True):
            self.first_run_setup()

        # Check for updates on boot (silently)
        last_check = int(self.config['DEFAULT'].get('last_update_check', '0'))
        if time.time() - last_check > 86400:  # Check once per day
            try:
                update_available = self.check_for_updates(silent=True)
                if update_available:
                    print("\n" + "=" * 60)
                    print(self._style("🔄 Update Available!", color="33", bold=True))
                    print("Run 'apd update' to download and install the latest version.")
                    print("=" * 60 + "\n")
            except Exception:
                pass  # Silent failure for boot check

        self.send_telemetry(
            "app_started",
            command=args[0] if args else None,
            args_count=len(args)
        )

        if len(args) == 0 or args[0] in ['-h', '--help', 'help']:
            if len(args) > 1 and args[1] in ['templates', 'template']:
                self.show_template_help(args[2] if len(args) > 2 else None)
            else:
                self.show_help()
            return

        # Resolve aliases BEFORE checking the command
        original_command = args[0]
        resolved_command = self._resolve_alias(original_command)
        if resolved_command != original_command:
            # Split resolved command into args
            resolved_parts = resolved_command.split()
            args = resolved_parts + args[1:]
            self.log_activity('debug', f'Alias resolved: {original_command} -> {resolved_command}')
            print(f"🔗 Alias: {original_command} -> {resolved_command}")
        else:
            # Also try to resolve the full command string for multi-word aliases
            full_command = ' '.join(args)
            resolved_full = self._resolve_alias(full_command)
            if resolved_full != full_command:
                args = resolved_full.split()
                self.log_activity('debug', f'Alias resolved: {full_command} -> {resolved_full}')
                print(f"🔗 Alias: {full_command} -> {resolved_full}")

        command = args[0]
        
        if command in ['gui', '--gui']:
            self.launch_gui()
            return

        if command in ['--version', 'version']:
            print(f"{self.app_name} v{self.version}")
            return

        if command in ['--setup', 'setup']:
            self.first_run_setup()
            return

        if command in ['--about', 'about']:
            self.show_about()
            return

        # Handle help for aliases
        if command in ['-h', '--help', 'help'] and len(args) > 1:
            # Check if the target is an alias (after resolving)
            target = args[1]
            if target in self._aliases:
                print(f"\n📋 Alias: {target} -> {self._aliases[target]}")
                print("Resolves to: apd " + self._resolve_alias(target))
                return
            # Check if any part of the command is an alias
            for i, arg in enumerate(args):
                if arg in self._aliases:
                    print(f"\n📋 Alias: {arg} -> {self._aliases[arg]}")
                    print("Resolves to: apd " + self._resolve_alias(arg))
                    return

        if command in ['init', 'new']:
            try:
                options = self._parse_new_project_options(args[1:])
            except ValueError as e:
                print(f"Error: {e}")
                return

            if command == 'new' and not options['project_name']:
                print("Error: Project name required")
                print("Usage: apd new <project-name> [--template <name>|--flask|--html]")
                return

            if not options['project_type']:
                options['project_type'] = self.config['DEFAULT']['default_template']

            self.init_project(
                project_type=options['project_type'],
                project_name=options['project_name'],
                cli_variables=options['variables'],
                interactive=options['interactive'],
                force=options['force'],
                auto_git=options['auto_git'],
                auto_venv=options['auto_venv'],
                auto_open=options['auto_open'],
                install_dependencies=options['install_dependencies'],
                target_dir=options['target_dir'],
                preview_only=options['preview'],
            )
            return

        if command == 'config':
            if len(args) == 1:
                self.show_config()
                return

            subcommand = args[1]
            if subcommand == 'mirror':
                self.configure_mirror(args[2] if len(args) > 2 else None)
            elif subcommand == 'editor':
                editor = args[2] if len(args) > 2 else None
                if editor:
                    self.config['DEFAULT']['editor'] = editor
                    self.save_config()
                    print(f"Default editor set to: {editor}")
                else:
                    print(self.config['DEFAULT']['editor'])
            elif subcommand == 'get':
                self.config_get(args[2] if len(args) > 2 else None)
            elif subcommand == 'set':
                if len(args) < 4:
                    print("❌ Usage: apd config set SECTION.key value")
                    return
                self.config_set(args[2], ' '.join(args[3:]))
            elif subcommand == 'path':
                print("\nConfiguration Paths:")
                print(f"  Config: {self.config_dir}")
                print(f"  Templates: {self.templates_dir}")
                print(f"  Projects: {self.projects_dir}")
                print(f"  Logs: {self.logs_dir}")
            else:
                self.show_config()
            return

        if command in ['template', 'templates']:
            if len(args) == 1:
                self.list_templates()
                return

            # Parse flags
            no_cache = '--no-cache' in args or '-nc' in args
            online = '--online' in args or '-o' in args
            # Remove flags from args list for subcommand processing
            clean_args = [arg for arg in args[1:] if arg not in ['--no-cache', '-nc', '--online', '-o']]

            if not clean_args:
                self.list_templates(online=online, no_cache=no_cache)
                return

            subcommand = clean_args[0]
            if subcommand == 'create':
                template_name = clean_args[1] if len(clean_args) > 1 else None
                if not template_name:
                    print("Error: Template name required")
                    return
                self.create_template_from_current(template_name, '--framework' in args)
            elif subcommand == 'list':
                self.list_templates(online=online, no_cache=no_cache)
            elif subcommand == 'info':
                template_name = clean_args[1] if len(clean_args) > 1 else None
                if not template_name:
                    print("Error: Template name required")
                    return
                self.generate_template_docs(template_name)
            elif subcommand == 'validate':
                template_name = clean_args[1] if len(clean_args) > 1 else None
                if not template_name:
                    print("Error: Template name required")
                    return
                manifest = self.get_template_manifest(template_name)
                if manifest:
                    is_valid, errors = manifest.validate()
                    if is_valid:
                        print(f"Template '{template_name}' is valid")
                    else:
                        print("Template validation failed:")
                        for error in errors:
                            print(f"  - {error}")
                else:
                    print(f"Error: Template '{template_name}' not found")
            elif subcommand == 'edit':
                template_name = clean_args[1] if len(clean_args) > 1 else None
                if not template_name:
                    print("Error: Template name required")
                    return
                manifest_file = self.templates_dir / template_name / 'manifest.json'
                if manifest_file.exists():
                    editor = self.config['DEFAULT']['editor']
                    subprocess.run([editor, str(manifest_file)])
                else:
                    print(f"Error: No manifest found for {template_name}")
                    print("Create one with: apd template create <name>")
            elif subcommand == 'preview':
                if len(clean_args) < 2:
                    print("Error: Usage: apd templates preview <name>")
                    return
                self.preview_template(clean_args[1])
            elif subcommand == 'search':
                if len(clean_args) < 2:
                    print("Error: Usage: apd templates search <term>")
                    return
                self.search_templates(' '.join(clean_args[1:]), no_cache=no_cache)
            elif subcommand == 'install':
                if len(clean_args) < 2:
                    print("Error: Usage: apd templates install <name>")
                    return
                self.install_template_from_repo(clean_args[1], no_cache=no_cache)
            elif subcommand == 'clone':
                if len(clean_args) < 3:
                    print("Error: Usage: apd templates clone <source> <target>")
                    return
                self.clone_template(clean_args[1], clean_args[2])
            elif subcommand == 'score':
                if len(clean_args) < 2:
                    print("Error: Usage: apd templates score <name>")
                    return
                self.score_template_quality(clean_args[1])
            else:
                self.manage_templates(subcommand, clean_args[1] if len(clean_args) > 1 else None, no_cache=no_cache, online=online)
            return

        if command == 'projects':
            if len(args) == 1:
                self.list_projects()
            elif args[1] == 'refresh':
                self.refresh_projects(args[2] if len(args) > 2 else None)
            elif args[1] == 'search':
                if len(args) < 3:
                    print("Error: Usage: apd projects search <term>")
                    return
                self.search_projects(' '.join(args[2:]))
            else:
                self.list_projects()
            return

        if command == 'open':
            if len(args) < 2:
                print("Error: Project name required")
                print("Usage: apd open <project-name>")
                return
            self.open_project(args[1])
            return

        if command == 'info':
            if len(args) < 2:
                print("Error: Project name required")
                print("Usage: apd info <project-name>")
                return
            self.show_project_info(args[1])
            return

        if command == 'inspect':
            if len(args) < 2:
                print("Error: Usage: apd inspect <project-name-or-path>")
                return
            self.inspect_project(args[1])
            return

        if command == 'audit':
            if len(args) < 2:
                print("Error: Usage: apd audit <project-name-or-path> [--fix|--json]")
                return
            self.audit_project(args[1], json_output='--json' in args, fix='--fix' in args)
            return

        if command == 'onboard':
            if len(args) < 2:
                print("Error: Usage: apd onboard <project-path> [--install]")
                return
            self.onboard_project(args[1], install='--install' in args)
            return

        if command == 'run':
            if len(args) < 2:
                print("Error: Usage: apd run <project-name-or-path> [--dry-run]")
                return
            self.run_project(args[1], dry_run='--dry-run' in args)
            return

        if command == 'test':
            if len(args) < 2:
                print("Error: Usage: apd test <project-name-or-path> [--dry-run]")
                return
            self.test_project(args[1], dry_run='--dry-run' in args)
            return

        if command == 'harden':
            if len(args) < 2:
                print("Error: Usage: apd harden <project-name-or-path> [--force]")
                return
            self.harden_project(args[1], force='--force' in args)
            return

        if command == 'readme':
            if len(args) < 2:
                print("Error: Usage: apd readme <project-name-or-path> [--force]")
                return
            self.generate_readme(args[1], force='--force' in args)
            return

        if command == 'license':
            if len(args) < 2:
                print("Error: Usage: apd license <project-name-or-path> [--force]")
                return
            license_name = 'MIT'
            for index, arg in enumerate(args):
                if arg == '--type' and index + 1 < len(args):
                    license_name = args[index + 1]
            self.generate_license(args[1], license_name=license_name, force='--force' in args)
            return

        if command == 'editorconfig':
            if len(args) < 2:
                print("Error: Usage: apd editorconfig <project-name-or-path> [--force]")
                return
            self.generate_editorconfig(args[1], force='--force' in args)
            return

        if command == 'deps':
            if len(args) < 2:
                print("Error: Usage: apd deps <project-name-or-path>")
                return
            self.show_dependencies(args[1])
            return

        if command == 'scripts':
            if len(args) < 2:
                print("Error: Usage: apd scripts <project-name-or-path>")
                return
            self.list_project_scripts(args[1])
            return

        if command == 'ports':
            if len(args) < 2:
                print("Error: Usage: apd ports <project-name-or-path>")
                return
            self.find_project_ports(args[1])
            return

        if command == 'env-check':
            if len(args) < 2:
                print("Error: Usage: apd env-check <project-name-or-path>")
                return
            self.check_environment(args[1])
            return

        if command == 'lock':
            if len(args) < 2:
                print("Error: Usage: apd lock <project-name-or-path> [--force]")
                return
            self.lock_project(args[1], force='--force' in args)
            return

        if command == 'verify':
            if len(args) < 2:
                print("Error: Usage: apd verify <project-name-or-path>")
                return
            self.verify_project_lock(args[1])
            return

        if command == 'clean-project':
            if len(args) < 2:
                print("Error: Usage: apd clean-project <project-name-or-path> [--dry-run]")
                return
            self.clean_project(args[1], dry_run='--dry-run' in args)
            return

        if command == 'plan':
            if len(args) < 2:
                print("Error: Usage: apd plan <project-name-or-path>")
                return
            self.deploy_plan(args[1])
            return

        if command == 'release':
            if len(args) < 2:
                print("Error: Usage: apd release <project-name-or-path> [label]")
                return
            label = args[2] if len(args) > 2 and not args[2].startswith('-') else None
            self.release_project(args[1], label=label)
            return

        if command == 'sbom':
            if len(args) < 2:
                print("Error: Usage: apd sbom <project-name-or-path> [--stdout]")
                return
            output = None
            for index, arg in enumerate(args):
                if arg == '--out' and index + 1 < len(args):
                    output = args[index + 1]
            self.generate_sbom(args[1], output=output, stdout='--stdout' in args)
            return

        if command == 'graph':
            if len(args) < 2:
                print("Error: Usage: apd graph <project-name-or-path> [--out file.dot]")
                return
            output = None
            for index, arg in enumerate(args):
                if arg == '--out' and index + 1 < len(args):
                    output = args[index + 1]
            self.dependency_graph(args[1], output=output)
            return

        if command == 'metrics':
            if len(args) < 2:
                print("Error: Usage: apd metrics <project-name-or-path>")
                return
            self.project_metrics(args[1])
            return

        if command == 'compare':
            if len(args) < 3:
                print("Error: Usage: apd compare <left-project> <right-project>")
                return
            self.compare_projects(args[1], args[2])
            return

        if command == 'scaffold-tests':
            if len(args) < 2:
                print("Error: Usage: apd scaffold-tests <project-name-or-path> [--force]")
                return
            self.scaffold_tests(args[1], force='--force' in args)
            return

        if command == 'audit-all':
            self.audit_all_projects()
            return

        if command == 'blueprint':
            if len(args) < 2:
                print("Error: Usage: apd blueprint <project-name-or-path> [--stdout]")
                return
            self.export_project_blueprint(args[1], stdout='--stdout' in args)
            return

        if command == 'env':
            if len(args) < 2:
                print("Error: Usage: apd env <project-name-or-path> [--force]")
                return
            self.generate_env_example(args[1], force='--force' in args)
            return

        if command == 'dockerize':
            if len(args) < 2:
                print("Error: Usage: apd dockerize <project-name-or-path> [--force]")
                return
            self.dockerize_project(args[1], force='--force' in args)
            return

        if command == 'ci':
            if len(args) < 2:
                print("Error: Usage: apd ci <project-name-or-path> [--force]")
                return
            self.create_ci_workflow(args[1], force='--force' in args)
            return

        if command == 'snapshot':
            if len(args) < 2:
                print("Error: Usage: apd snapshot <project-name-or-path> [label]")
                return
            label = args[2] if len(args) > 2 and not args[2].startswith('-') else None
            self.snapshot_project(args[1], label=label)
            return

        if command == 'restore':
            if len(args) < 2:
                print("Error: Usage: apd restore <snapshot.zip> [destination] [--force]")
                return
            destination = args[2] if len(args) > 2 and not args[2].startswith('-') else None
            self.restore_snapshot(args[1], destination=destination, force='--force' in args)
            return

        if command == 'archive':
            if len(args) < 2:
                print("Error: Project name required")
                print("Usage: apd archive <project-name>")
                return
            self.archive_project(args[1])
            return

        if command == 'delete':
            if len(args) < 2:
                print("Error: Project name required")
                print("Usage: apd delete <project-name>")
                return
            self.delete_project(args[1], force='--force' in args)
            return

        if command == 'rename':
            if len(args) < 3:
                print("Error: Usage: apd rename <old-name> <new-name>")
                return
            self.rename_project(args[1], args[2])
            return

        if command == 'doctor':
            if '--fix' in args:
                self.doctor_fix()
            else:
                self.run_doctor()
            return

        if command == 'alias':
            if len(args) == 1:
                self.list_aliases()
                return
            
            subcommand = args[1]
            if subcommand == 'list':
                self.list_aliases()
            elif subcommand == 'add':
                if len(args) < 4:
                    print("❌ Usage: apd alias add <alias> <command>")
                    print("Example: apd alias add c new")
                    return
                self.add_alias(args[2], ' '.join(args[3:]))
            elif subcommand == 'remove':
                if len(args) < 3:
                    print("❌ Usage: apd alias remove <alias>")
                    print("Example: apd alias remove c")
                    return
                self.remove_alias(args[2])
            elif subcommand == 'help':
                self.show_alias_help()
            else:
                print(f"❌ Unknown alias subcommand: {subcommand}")
                print("Available: list, add, remove, help")
            return

        if command == 'status':
            self.show_status()
            return

        if command == 'update':
            # Check if we need to perform the update or just check
            if '--force' in args or '-f' in args:
                self.perform_update()
            elif '--verify' in args:
                # Just check and show status
                self.check_for_updates(silent=False)
            else:
                # First check if update is available
                available = self.check_for_updates(silent=False)
                if available:
                    print("\n" + "=" * 60)
                    print(self._style("🔄 Update Available!", color="33", bold=True))
                    print("Run 'apd update --force' to download and install it.")
                    print("=" * 60)
                elif available is False:
                    print("\n✅ You already have the latest version.")
            return

        if command == 'logs':
            self.show_logs(len(args) > 1 and args[1] == '--tail')
            return

        if command == 'cleanup':
            self.cleanup()
            return

        if command == 'uninstall':
            self.uninstall()
            return

        print(f"Error: Unknown command: {command}")
        print("Try 'apd --help' for available commands")

class EmbeddedAPDGUI:
    """Embedded GUI for APD using tkinter."""
    
    def __init__(self, cli: ILIACLI):
        self.cli = cli
        self.root = None
        self.output_queue = queue.Queue()
        self.current_project = None
        self.current_template = None
        self.status_var = None
        self.output_text = None
        self.progress_var = None
        self.progress_bar = None
        
    def run(self):
        """Run the GUI main loop."""
        self.root = tk.Tk()
        self.root.title(f"APD - Advanced Project Deployer v{self.cli.version}")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
        # Set icon if available
        try:
            self.root.iconbitmap(default='apd.ico')
        except:
            pass
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors - Clean, modern light theme
        bg_color = "#f5f7fa"
        fg_color = "#2d3748"
        accent_color = "#4f8cf7"
        secondary_bg = "#e2e8f0"
        card_bg = "#ffffff"
        success_color = "#38a169"
        warning_color = "#d69e2e"
        error_color = "#e53e3e"
        border_color = "#cbd5e0"
        muted_text = "#718096"
        hover_color = "#edf2f7"
        
        self.root.configure(bg=bg_color)
        
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=0)  # Header
        main_frame.rowconfigure(1, weight=1)  # Content
        main_frame.rowconfigure(2, weight=0)  # Status
        
        # ===== HEADER =====
        header_frame = tk.Frame(main_frame, bg=card_bg, relief=tk.RIDGE, bd=1)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=5)
        
        # Title
        title_label = tk.Label(
            header_frame,
            text=f"APD v{self.cli.version}",
            font=("Segoe UI", 18, "bold"),
            bg=card_bg,
            fg=accent_color
        )
        title_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        # Quick action buttons
        button_frame = tk.Frame(header_frame, bg=card_bg)
        button_frame.pack(side=tk.RIGHT, padx=10)
        
        self._create_button(button_frame, "📁 New Project", self._new_project_dialog, "#4f8cf7", card_bg)
        self._create_button(button_frame, "📋 Templates", self._show_templates, "#38a169", card_bg)
        self._create_button(button_frame, "📊 Projects", self._show_projects, "#d69e2e", card_bg)
        self._create_button(button_frame, "⚙️ Config", self._show_config, "#e53e3e", card_bg)
        self._create_button(button_frame, "🔄 Refresh", self._refresh_all, "#6b46c1", card_bg)
        
        # ===== CONTENT =====
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        
        # Create tabs
        self.dashboard_tab = self._create_dashboard_tab()
        self.projects_tab = self._create_projects_tab()
        self.templates_tab = self._create_templates_tab()
        self.config_tab = self._create_config_tab()
        self.output_tab = self._create_output_tab()
        
        self.notebook.add(self.dashboard_tab, text="🏠 Dashboard")
        self.notebook.add(self.projects_tab, text="📁 Projects")
        self.notebook.add(self.templates_tab, text="📋 Templates")
        self.notebook.add(self.config_tab, text="⚙️ Config")
        self.notebook.add(self.output_tab, text="📄 Output")
        
        # ===== STATUS BAR =====
        status_frame = tk.Frame(main_frame, bg="white", relief=tk.RIDGE, bd=1, highlightbackground="#e2e8f0", highlightthickness=1)
        status_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0), padx=5)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 10),
            bg="white",
            fg="#4a5568"
        )
        status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            status_frame,
            variable=self.progress_var,
            maximum=100,
            length=200,
            style="TProgressbar"
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Style the progress bar
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", background="#4f8cf7", troughcolor="#e2e8f0", bordercolor="#4f8cf7", lightcolor="#4f8cf7", darkcolor="#4f8cf7")
        
        # Load initial data
        self._refresh_all()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Start the GUI
        self.root.mainloop()
    
    def _create_button(self, parent, text, command, color="#4f8cf7", bg="#ffffff"):
        """Create a styled button."""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 10, "bold"),
            bg=color,
            fg="white",
            padx=15,
            pady=8,
            relief=tk.RAISED,
            bd=0,
            cursor="hand2",
            activebackground=self._lighten_color(color),
            activeforeground="white"
        )
        btn.pack(side=tk.LEFT, padx=4)
        return btn
    
    def _lighten_color(self, hex_color, factor=0.3):
        """Lighten a hex color."""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def _create_dashboard_tab(self):
        """Create the dashboard tab."""
        tab = tk.Frame(self.notebook, bg="#f5f7fa")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=0)
        tab.rowconfigure(1, weight=1)
        
        # Stats row
        stats_frame = tk.Frame(tab, bg="#f5f7fa")
        stats_frame.grid(row=0, column=0, sticky="ew", pady=10, padx=10)
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)
        stats_frame.columnconfigure(3, weight=1)
        
        self.stats_labels = {}
        stats_data = [
            ("📁 Projects", "0", "#4f8cf7"),
            ("📋 Templates", "0", "#38a169"),
            ("📦 Dependencies", "0", "#d69e2e"),
            ("⚙️ Config", "OK", "#e53e3e")
        ]
        
        for i, (label, value, color) in enumerate(stats_data):
            frame = tk.Frame(stats_frame, bg="white", relief=tk.RIDGE, bd=1, highlightbackground="#e2e8f0", highlightthickness=1)
            frame.grid(row=0, column=i, sticky="nsew", padx=8, pady=8)
            
            tk.Label(
                frame,
                text=label,
                font=("Segoe UI", 11),
                bg="white",
                fg="#4a5568"
            ).pack(pady=(12, 0))
            
            val_label = tk.Label(
                frame,
                text=value,
                font=("Segoe UI", 24, "bold"),
                bg="white",
                fg=color
            )
            val_label.pack(pady=(4, 12))
            self.stats_labels[label] = val_label
        
        # Quick actions with custom tiles support
        quick_frame = tk.LabelFrame(tab, text=" Quick Actions ", font=("Segoe UI", 11, "bold"), bg="white", fg="#2d3748", padx=10, pady=10)
        quick_frame.grid(row=1, column=0, sticky="nsew", pady=10, padx=10)
        
        # Top row with controls
        control_frame = tk.Frame(quick_frame, bg="white")
        control_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(
            control_frame,
            text="Customize your quick access tiles:",
            font=("Segoe UI", 9),
            bg="white",
            fg="#718096"
        ).pack(side=tk.LEFT)
        
        tk.Button(
            control_frame,
            text="➕ Add Tile",
            command=self._add_custom_tile,
            bg="#4f8cf7",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief=tk.RAISED,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=2)
        
        tk.Button(
            control_frame,
            text="✏️ Edit Tiles",
            command=self._edit_tiles_mode,
            bg="#d69e2e",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief=tk.RAISED,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=2)
        
        tk.Button(
            control_frame,
            text="🔄 Reset Tiles",
            command=self._reset_tiles,
            bg="#e53e3e",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief=tk.RAISED,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=2)
        
        # Tile grid container
        self.tile_container = tk.Frame(quick_frame, bg="white")
        self.tile_container.pack(fill=tk.BOTH, expand=True)
        self.tile_container.columnconfigure(0, weight=1)
        self.tile_container.columnconfigure(1, weight=1)
        self.tile_container.columnconfigure(2, weight=1)
        
        # Load custom tiles or use defaults
        self.custom_tiles = self._load_custom_tiles()
        self.edit_mode = False
        self._render_tiles()
        
        return tab
    
    def _create_projects_tab(self):
        """Create the projects tab."""
        tab = tk.Frame(self.notebook, bg="#f5f7fa")
        tab.columnconfigure(0, weight=0)  # Sidebar
        tab.columnconfigure(1, weight=1)  # Content
        tab.rowconfigure(0, weight=1)
        
        # Sidebar with project list
        sidebar = tk.Frame(tab, bg="white", relief=tk.RIDGE, bd=1, highlightbackground="#e2e8f0", highlightthickness=1)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(5, 5), pady=5)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(0, weight=0)
        sidebar.rowconfigure(1, weight=1)
        
        tk.Label(
            sidebar,
            text="📁 Projects",
            font=("Segoe UI", 12, "bold"),
            bg="white",
            fg="#2d3748"
        ).grid(row=0, column=0, pady=8)
        
        # Project listbox
        list_frame = tk.Frame(sidebar, bg="white")
        list_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        self.project_listbox = tk.Listbox(
            list_frame,
            font=("Segoe UI", 10),
            bg="#f7fafc",
            fg="#2d3748",
            selectbackground="#4f8cf7",
            selectforeground="white",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0
        )
        self.project_listbox.grid(row=0, column=0, sticky="nsew")
        self.project_listbox.bind('<<ListboxSelect>>', self._on_project_select)
        
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.project_listbox.yview, bg="#e2e8f0")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.project_listbox.config(yscrollcommand=scrollbar.set)
        
        # Project actions
        action_frame = tk.Frame(sidebar, bg="white")
        action_frame.grid(row=2, column=0, sticky="ew", pady=5, padx=5)
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        
        tk.Button(action_frame, text="Open", command=self._open_selected_project, bg="#4f8cf7", fg="white", font=("Segoe UI", 10), relief=tk.RAISED, bd=0, padx=10, pady=5).grid(row=0, column=0, padx=2)
        tk.Button(action_frame, text="Delete", command=self._delete_selected_project, bg="#e53e3e", fg="white", font=("Segoe UI", 10), relief=tk.RAISED, bd=0, padx=10, pady=5).grid(row=0, column=1, padx=2)
        
        # Content area
        content = tk.Frame(tab, bg="#f5f7fa")
        content.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)
        
        self.project_info_text = scrolledtext.ScrolledText(
            content,
            font=("Consolas", 10),
            bg="white",
            fg="#2d3748",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightcolor="#e2e8f0"
        )
        self.project_info_text.grid(row=0, column=0, sticky="nsew")
        
        return tab
    
    def _create_templates_tab(self):
        """Create the templates tab."""
        tab = tk.Frame(self.notebook, bg="#f5f7fa")
        tab.columnconfigure(0, weight=0)  # Sidebar
        tab.columnconfigure(1, weight=1)  # Content
        tab.rowconfigure(0, weight=1)
        
        # Sidebar
        sidebar = tk.Frame(tab, bg="white", relief=tk.RIDGE, bd=1, highlightbackground="#e2e8f0", highlightthickness=1)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(5, 5), pady=5)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(0, weight=0)
        sidebar.rowconfigure(1, weight=1)
        sidebar.rowconfigure(2, weight=0)
        
        tk.Label(
            sidebar,
            text="📋 Templates",
            font=("Segoe UI", 12, "bold"),
            bg="white",
            fg="#2d3748"
        ).grid(row=0, column=0, pady=8)
        
        # Template list
        list_frame = tk.Frame(sidebar, bg="white")
        list_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        self.template_listbox = tk.Listbox(
            list_frame,
            font=("Segoe UI", 10),
            bg="#f7fafc",
            fg="#2d3748",
            selectbackground="#38a169",
            selectforeground="white",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0
        )
        self.template_listbox.grid(row=0, column=0, sticky="nsew")
        self.template_listbox.bind('<<ListboxSelect>>', self._on_template_select)
        
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.template_listbox.yview, bg="#e2e8f0")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.template_listbox.config(yscrollcommand=scrollbar.set)
        
        # Template actions
        action_frame = tk.Frame(sidebar, bg="white")
        action_frame.grid(row=2, column=0, sticky="ew", pady=5, padx=5)
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        
        tk.Button(action_frame, text="Preview", command=self._preview_template, bg="#38a169", fg="white", font=("Segoe UI", 10), relief=tk.RAISED, bd=0, padx=10, pady=5).grid(row=0, column=0, padx=2)
        tk.Button(action_frame, text="Export", command=self._export_template, bg="#d69e2e", fg="white", font=("Segoe UI", 10), relief=tk.RAISED, bd=0, padx=10, pady=5).grid(row=0, column=1, padx=2)
        
        # Content area
        content = tk.Frame(tab, bg="#f5f7fa")
        content.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)
        
        self.template_info_text = scrolledtext.ScrolledText(
            content,
            font=("Consolas", 10),
            bg="white",
            fg="#2d3748",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightcolor="#e2e8f0"
        )
        self.template_info_text.grid(row=0, column=0, sticky="nsew")
        
        return tab
    
    def _create_config_tab(self):
        """Create the config tab."""
        tab = tk.Frame(self.notebook, bg="#f5f7fa")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=0)
        tab.rowconfigure(1, weight=1)
        
        # Config sections
        sections_frame = tk.LabelFrame(tab, text=" Configuration ", font=("Segoe UI", 11, "bold"), bg="white", fg="#2d3748", padx=10, pady=10)
        sections_frame.grid(row=0, column=0, sticky="ew", pady=10, padx=10)
        sections_frame.columnconfigure(0, weight=1)
        sections_frame.columnconfigure(1, weight=1)
        sections_frame.columnconfigure(2, weight=1)
        
        # Config items
        config_items = [
            ("Default Template", "default_template", "html"),
            ("Default Editor", "editor", "code"),
            ("Auto Git", "auto_git", "false"),
            ("Auto Venv", "auto_venv", "true"),
            ("Auto Open", "auto_open", "false"),
            ("License", "license", "MIT"),
            ("Author", "author", ""),
            ("Email", "email", ""),
            ("Mirror Enabled", "mirror_enabled", "false"),
            ("Telemetry", "telemetry", "false"),
            ("Auto Update", "auto_update", "false"),
        ]
        
        self.config_entries = {}
        row = 0
        col = 0
        
        for label, key, default in config_items:
            frame = tk.Frame(sections_frame, bg="white")
            frame.grid(row=row, column=col, sticky="ew", padx=10, pady=5)
            sections_frame.columnconfigure(col, weight=1)
            
            tk.Label(
                frame,
                text=label,
                font=("Segoe UI", 10),
                bg="white",
                fg="#4a5568"
            ).pack(anchor=tk.W)
            
            # Get current value
            if key in ['mirror_enabled', 'telemetry', 'auto_update', 'auto_git', 'auto_venv', 'auto_open']:
                section = 'MIRROR' if key == 'mirror_enabled' else 'PROJECT' if key in ['auto_git', 'auto_venv', 'auto_open', 'license', 'author', 'email'] else 'DEFAULT'
                if key == 'mirror_enabled':
                    value = self.cli.config['MIRROR'].getboolean('enabled', False)
                elif key in ['auto_git', 'auto_venv', 'auto_open']:
                    value = self.cli.config['PROJECT'].getboolean(key, False)
                elif key in ['telemetry', 'auto_update']:
                    value = self.cli.config['DEFAULT'].getboolean(key, False)
                else:
                    value = self.cli.config['DEFAULT'].get(key, default)
                
                # Boolean as checkbox
                var = tk.BooleanVar(value=value)
                cb = ttk.Checkbutton(frame, variable=var)
                cb.pack(anchor=tk.W)
                self.config_entries[key] = var
            else:
                # Text entry
                if key == 'author':
                    value = self.cli.config['PROJECT'].get(key, default)
                elif key == 'email':
                    value = self.cli.config['PROJECT'].get(key, default)
                elif key == 'license':
                    value = self.cli.config['PROJECT'].get(key, default)
                else:
                    value = self.cli.config['DEFAULT'].get(key, default)
                
                entry = ttk.Entry(frame, width=25)
                entry.insert(0, str(value))
                entry.pack(anchor=tk.W, fill=tk.X)
                self.config_entries[key] = entry
            
            col += 1
            if col > 2:
                col = 0
                row += 1
        
        # Save button
        btn_frame = tk.Frame(tab, bg="#f5f7fa")
        btn_frame.grid(row=1, column=0, sticky="ew", pady=10)
        
        tk.Button(
            btn_frame,
            text="💾 Save Configuration",
            command=self._save_config,
            bg="#4f8cf7",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            relief=tk.RAISED,
            bd=0,
            padx=30,
            pady=10,
            cursor="hand2",
            activebackground=self._lighten_color("#4f8cf7"),
            activeforeground="white"
        ).pack()
        
        return tab
    
    def _create_output_tab(self):
        """Create the output/log tab."""
        tab = tk.Frame(self.notebook, bg="#f5f7fa")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(
            tab,
            font=("Consolas", 10),
            bg="white",
            fg="#2d3748",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightcolor="#e2e8f0"
        )
        self.output_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure tags for colors
        self.output_text.tag_configure("info", foreground="#4f8cf7")
        self.output_text.tag_configure("success", foreground="#38a169")
        self.output_text.tag_configure("warning", foreground="#d69e2e")
        self.output_text.tag_configure("error", foreground="#e53e3e")
        
        # Button frame
        btn_frame = tk.Frame(tab, bg="#f5f7fa")
        btn_frame.grid(row=1, column=0, sticky="ew", pady=5)
        tk.Button(btn_frame, text="Clear", command=self._clear_output, bg="#e2e8f0", fg="#2d3748", font=("Segoe UI", 10), relief=tk.RAISED, bd=0, padx=15, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Copy", command=self._copy_output, bg="#e2e8f0", fg="#2d3748", font=("Segoe UI", 10), relief=tk.RAISED, bd=0, padx=15, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        return tab
    
    def _log(self, message, tag="info"):
        """Log a message to the output tab."""
        if self.output_text:
            self.output_text.insert(tk.END, message + "\n", tag)
            self.output_text.see(tk.END)
            self.root.update_idletasks()
    
    def _clear_output(self):
        """Clear the output text."""
        if self.output_text:
            self.output_text.delete(1.0, tk.END)
    
    def _copy_output(self):
        """Copy output to clipboard."""
        if self.output_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.output_text.get(1.0, tk.END))
            self._log("📋 Output copied to clipboard", "success")
    
    def _set_status(self, message):
        """Set the status bar message."""
        if self.status_var:
            self.status_var.set(message)
            self.root.update_idletasks()
    
    def _set_progress(self, value):
        """Set the progress bar value."""
        if self.progress_var:
            self.progress_var.set(value)
            self.root.update_idletasks()
    
    def _refresh_all(self):
        """Refresh all data."""
        self._set_status("Refreshing...")
        self._refresh_projects()
        self._refresh_templates()
        self._update_stats()
        self._set_status("Ready")
    
    def _refresh_projects(self):
        """Refresh the project list."""
        self.project_listbox.delete(0, tk.END)
        projects = self.cli._load_projects_db()
        for project in projects:
            name = project.get('name', 'Unknown')
            self.project_listbox.insert(tk.END, name)
    
    def _refresh_templates(self):
        """Refresh the template list."""
        self.template_listbox.delete(0, tk.END)
        templates = self.cli.list_available_templates()
        for template in templates:
            self.template_listbox.insert(tk.END, template)
    
    def _load_custom_tiles(self):
        """Load custom tiles from config."""
        tiles_file = self.cli.config_dir / "custom_tiles.json"
        if tiles_file.exists():
            try:
                with open(tiles_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return self._get_default_tiles()
    
    def _get_default_tiles(self):
        """Get default tiles configuration."""
        return [
            {"label": "🚀 New Flask Project", "action": "new_flask", "color": "#4f8cf7"},
            {"label": "🌐 New HTML Project", "action": "new_html", "color": "#38a169"},
            {"label": "📁 Open Project", "action": "open_project", "color": "#d69e2e"},
            {"label": "📋 Import Template", "action": "import_template", "color": "#e53e3e"},
            {"label": "🔍 Run Doctor", "action": "run_doctor", "color": "#6b46c1"},
            {"label": "📊 Audit All", "action": "audit_all", "color": "#4f8cf7"},
        ]
    
    def _save_custom_tiles(self):
        """Save custom tiles to config."""
        tiles_file = self.cli.config_dir / "custom_tiles.json"
        try:
            with open(tiles_file, 'w') as f:
                json.dump(self.custom_tiles, f, indent=2)
        except Exception as e:
            self._log(f"❌ Error saving tiles: {e}", "error")
    
    def _render_tiles(self):
        """Render tiles in the grid with drag-drop support."""
        # Clear existing tiles
        for widget in self.tile_container.winfo_children():
            widget.destroy()
        
        # Configure grid columns
        for col in range(3):
            self.tile_container.columnconfigure(col, weight=1)
        
        # Calculate rows needed
        tile_count = len(self.custom_tiles)
        rows = (tile_count + 2) // 3
        
        for row in range(rows):
            self.tile_container.rowconfigure(row, weight=1)
        
        # Store tile references for drag-drop
        self.tile_frames = []
        self.tile_buttons = []
        
        for i, tile in enumerate(self.custom_tiles):
            row = i // 3
            col = i % 3
            
            tile_frame = tk.Frame(self.tile_container, bg="white", relief=tk.RAISED, bd=1)
            tile_frame.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            tile_frame.columnconfigure(0, weight=1)
            tile_frame.rowconfigure(0, weight=1)
            
            # Store reference for drag-drop
            self.tile_frames.append(tile_frame)
            
            if self.edit_mode:
                # Edit mode: show edit, delete and drag controls
                btn_frame = tk.Frame(tile_frame, bg="white")
                btn_frame.pack(fill=tk.BOTH, expand=True)
                
                # Main button - EDIT when in edit mode
                btn = tk.Button(
                    btn_frame,
                    text=tile["label"],
                    command=lambda idx=i: self._edit_tile(idx),
                    font=("Segoe UI", 11, "bold"),
                    bg=tile["color"],
                    fg="white",
                    padx=20,
                    pady=15,
                    relief=tk.RAISED,
                    bd=0,
                    cursor="hand2",
                    activebackground=self._lighten_color(tile["color"]),
                    activeforeground="white"
                )
                btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
                
                # Delete button
                delete_btn = tk.Button(
                    btn_frame,
                    text="✕",
                    command=lambda idx=i: self._delete_tile(idx),
                    bg="#e53e3e",
                    fg="white",
                    font=("Segoe UI", 10, "bold"),
                    relief=tk.RAISED,
                    bd=0,
                    padx=8,
                    pady=8,
                    cursor="hand2"
                )
                delete_btn.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Drag handle
                drag_handle = tk.Button(
                    btn_frame,
                    text="⠿",
                    bg="#e2e8f0",
                    fg="#718096",
                    font=("Segoe UI", 10),
                    relief=tk.FLAT,
                    bd=0,
                    padx=6,
                    pady=8,
                    cursor="fleur",
                    activebackground="#cbd5e0"
                )
                drag_handle.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 2))
                
                # Bind drag events to the drag handle and frame
                for widget in [drag_handle, tile_frame]:
                    widget.bind("<Button-1>", lambda e, idx=i: self._start_drag(e, idx))
                    widget.bind("<B1-Motion>", lambda e, idx=i: self._on_drag(e, idx))
                    widget.bind("<ButtonRelease-1>", lambda e, idx=i: self._end_drag(e, idx))
            else:
                # Normal mode
                btn = tk.Button(
                    tile_frame,
                    text=tile["label"],
                    command=lambda a=tile["action"]: self._execute_tile_action(a),
                    font=("Segoe UI", 11, "bold"),
                    bg=tile["color"],
                    fg="white",
                    padx=20,
                    pady=15,
                    relief=tk.RAISED,
                    bd=0,
                    cursor="hand2",
                    activebackground=self._lighten_color(tile["color"]),
                    activeforeground="white"
                )
                btn.pack(fill=tk.BOTH, expand=True)
                self.tile_buttons.append(btn)
    
    def _start_drag(self, event, index):
        """Start drag operation for tile."""
        self.drag_index = index
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        # Create a floating copy
        tile = self.custom_tiles[index]
        self.drag_window = tk.Toplevel(self.root)
        self.drag_window.overrideredirect(True)
        self.drag_window.attributes('-topmost', True)
        self.drag_window.configure(bg=tile["color"])
        
        label = tk.Label(
            self.drag_window,
            text=tile["label"],
            bg=tile["color"],
            fg="white",
            font=("Segoe UI", 11, "bold"),
            padx=20,
            pady=10
        )
        label.pack()
        self.drag_window.geometry(f"+{event.x_root-10}+{event.y_root-10}")
    
    def _on_drag(self, event, index):
        """Handle drag motion."""
        if hasattr(self, 'drag_window') and self.drag_window:
            self.drag_window.geometry(f"+{event.x_root-10}+{event.y_root-10}")
    
    def _end_drag(self, event, index):
        """End drag operation."""
        if hasattr(self, 'drag_window') and self.drag_window:
            self.drag_window.destroy()
            self.drag_window = None
        
        # Find which tile we dropped on
        drop_index = self._find_tile_at_position(event.x_root, event.y_root)
        if drop_index is not None and drop_index != self.drag_index:
            # Reorder tiles
            tile = self.custom_tiles.pop(self.drag_index)
            self.custom_tiles.insert(drop_index, tile)
            self._save_custom_tiles()
            self._render_tiles()
            self._log(f"🔄 Moved tile to position {drop_index+1}", "info")
        
        self.drag_index = None
    
    def _find_tile_at_position(self, x, y):
        """Find which tile frame is at the given screen position."""
        for i, frame in enumerate(self.tile_frames):
            # Get frame bounding box in screen coordinates
            x0 = frame.winfo_rootx()
            y0 = frame.winfo_rooty()
            x1 = x0 + frame.winfo_width()
            y1 = y0 + frame.winfo_height()
            if x0 <= x <= x1 and y0 <= y <= y1:
                return i
        return None
    
    def _resize_tile(self, index, size):
        """Resize a tile (removed - tiles are fixed size)."""
        pass
    
    def _execute_tile_action(self, action):
        """Execute a tile action."""
        if action == "new_flask":
            self._new_project_with_template("flask")
        elif action == "new_html":
            self._new_project_with_template("html")
        elif action == "open_project":
            self._open_project_dialog()
        elif action == "import_template":
            self._import_template_dialog()
        elif action == "run_doctor":
            self._run_doctor()
        elif action == "audit_all":
            self._audit_all()
        elif action.startswith("new_"):
            # Custom template quick action
            template_name = action.replace("new_", "")
            self._new_project_with_template(template_name)
        elif action.startswith("cmd_"):
            # Custom command action (may include 'apd' prefix)
            cmd = action.replace("cmd_", "")
            self._execute_custom_command(cmd)
        elif action.startswith("alias_"):
            # Execute an alias
            alias = action.replace("alias_", "")
            if alias in self.cli._aliases:
                resolved = self.cli._aliases[alias]
                self._execute_custom_command(f"apd {resolved}")
            else:
                self._log(f"❌ Alias not found: {alias}", "error")
    
    def _execute_custom_command(self, command):
        """Execute a custom shell command."""
        self.notebook.select(self.output_tab)
        self._set_status(f"Executing: {command}")
        self._log(f"⚙️ Executing: {command}", "info")
        
        def task():
            try:
                import subprocess
                # Check if command starts with "apd" - if so, use the CLI directly
                if command.startswith("apd "):
                    # Strip "apd " and pass to CLI
                    cli_args = command[4:].split()
                    # Run in a separate thread to avoid blocking
                    self.root.after(0, lambda: self._log(f"📢 Running APD command: {command}", "info"))
                    # Use the CLI instance directly
                    try:
                        # Capture output from CLI command
                        import io
                        import contextlib
                        with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                            self.cli.run(cli_args)
                            output = buf.getvalue()
                        if output:
                            self.root.after(0, lambda: self._log(output, "info"))
                        self.root.after(0, lambda: self._log(f"✅ APD command completed", "success"))
                    except Exception as e:
                        self.root.after(0, lambda: self._log(f"❌ APD command error: {e}", "error"))
                else:
                    # Regular shell command
                    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=Path.cwd())
                    if result.stdout:
                        self.root.after(0, lambda: self._log(result.stdout, "info"))
                    if result.stderr:
                        self.root.after(0, lambda: self._log(result.stderr, "error"))
                    if result.returncode == 0:
                        self.root.after(0, lambda: self._log(f"✅ Command completed successfully", "success"))
                    else:
                        self.root.after(0, lambda: self._log(f"❌ Command exited with code {result.returncode}", "error"))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"❌ Error: {e}", "error"))
            finally:
                self.root.after(0, lambda: self._set_status("Ready"))
        
        threading.Thread(target=task, daemon=True).start()
    
    def _add_custom_tile(self):
        """Show dialog to add a custom tile."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Custom Tile")
        dialog.geometry("550x550")
        dialog.minsize(500, 500)
        dialog.configure(bg="#f5f7fa")
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 550) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 550) // 2
        dialog.geometry(f"+{x}+{y}")
        
    def _add_custom_tile(self, edit_index=None):
        """Show dialog to add or edit a custom tile."""
        is_edit = edit_index is not None
        title = "✏️ Edit Custom Tile" if is_edit else "➕ Add Custom Tile"
        
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("600x620")
        dialog.minsize(550, 580)
        dialog.configure(bg="#f5f7fa")
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 600) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 620) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Main container with scroll
        main_container = tk.Frame(dialog, bg="#f5f7fa")
        main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=0)  # Button bar
        
        # Scrollable content area
        canvas_container = tk.Frame(main_container, bg="#f5f7fa")
        canvas_container.grid(row=0, column=0, sticky="nsew")
        canvas_container.columnconfigure(0, weight=1)
        canvas_container.rowconfigure(0, weight=1)
        
        canvas = tk.Canvas(canvas_container, bg="#f5f7fa", highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = tk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Content frame inside canvas
        frame = tk.Frame(canvas, bg="#f5f7fa")
        canvas.create_window((0, 0), window=frame, anchor="nw", width=canvas.winfo_width())
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(1, width=canvas.winfo_width())
        
        def on_canvas_configure(event):
            canvas.itemconfig(1, width=event.width)
        
        frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Content padding
        content_frame = tk.Frame(frame, bg="#f5f7fa")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        
        tk.Label(
            content_frame,
            text="✏️ Edit Custom Tile" if is_edit else "➕ Add Custom Tile",
            font=("Segoe UI", 18, "bold"),
            bg="#f5f7fa",
            fg="#4f8cf7"
        ).pack(pady=(0, 15))
        
        # Tile label
        label_frame = tk.Frame(content_frame, bg="#f5f7fa")
        label_frame.pack(fill=tk.X, pady=8)
        tk.Label(
            label_frame,
            text="Tile Label:",
            font=("Segoe UI", 10, "bold"),
            bg="#f5f7fa",
            fg="#2d3748"
        ).pack(anchor=tk.W)
        label_entry = tk.Entry(label_frame, font=("Segoe UI", 11), bg="white", fg="#2d3748", relief=tk.RIDGE, bd=1, highlightthickness=0)
        label_entry.pack(fill=tk.X, pady=5)
        
        # Tile type selection
        type_frame = tk.Frame(content_frame, bg="#f5f7fa")
        type_frame.pack(fill=tk.X, pady=8)
        tk.Label(
            type_frame,
            text="Tile Type:",
            font=("Segoe UI", 10, "bold"),
            bg="#f5f7fa",
            fg="#2d3748"
        ).pack(anchor=tk.W)
        
        tile_type_var = tk.StringVar(value="template")
        tk.Radiobutton(type_frame, text="🚀 Quick New Project (template)", variable=tile_type_var, value="template", bg="#f5f7fa", fg="#2d3748", font=("Segoe UI", 10), selectcolor="#f5f7fa").pack(anchor=tk.W, pady=3)
        tk.Radiobutton(type_frame, text="⚙️ APD Command", variable=tile_type_var, value="command", bg="#f5f7fa", fg="#2d3748", font=("Segoe UI", 10), selectcolor="#f5f7fa").pack(anchor=tk.W, pady=3)
        tk.Radiobutton(type_frame, text="💻 Shell Command", variable=tile_type_var, value="shell", bg="#f5f7fa", fg="#2d3748", font=("Segoe UI", 10), selectcolor="#f5f7fa").pack(anchor=tk.W, pady=3)
        
        # Template/Command selection
        selection_frame = tk.Frame(content_frame, bg="#f5f7fa")
        selection_frame.pack(fill=tk.X, pady=10)
        
        def update_selection_options(*args):
            for widget in selection_frame.winfo_children():
                widget.destroy()
            
            tile_type = tile_type_var.get()
            if tile_type == "template":
                tk.Label(
                    selection_frame,
                    text="Select Template:",
                    font=("Segoe UI", 10, "bold"),
                    bg="#f5f7fa",
                    fg="#2d3748"
                ).pack(anchor=tk.W)
                combo = ttk.Combobox(selection_frame, font=("Segoe UI", 11), height=8)
                templates = self.cli.list_available_templates()
                combo['values'] = templates
                if templates:
                    combo.set(templates[0])
                # If editing, set the template
                if is_edit and hasattr(self, '_edit_template_name') and self._edit_template_name:
                    if self._edit_template_name in templates:
                        combo.set(self._edit_template_name)
                combo.pack(fill=tk.X, pady=5)
                selection_frame.combo = combo
                # Bind key events for keyboard search
                combo.bind('<KeyRelease>', lambda e: self._filter_combobox(combo, e, templates))
                # Prevent scroll from propagating to parent
                combo.bind('<MouseWheel>', lambda e: "break")
                combo.bind('<Button-4>', lambda e: "break")
                combo.bind('<Button-5>', lambda e: "break")
            elif tile_type in ["command", "shell"]:
                tk.Label(
                    selection_frame,
                    text="Enter Command:",
                    font=("Segoe UI", 10, "bold"),
                    bg="#f5f7fa",
                    fg="#2d3748"
                ).pack(anchor=tk.W)
                
                # Show hint about APD auto-prepend
                if tile_type == "command":
                    tk.Label(
                        selection_frame,
                        text="💡 APD command will auto-prepend 'apd' (e.g., 'help' → 'apd help')",
                        font=("Segoe UI", 9),
                        bg="#f5f7fa",
                        fg="#718096"
                    ).pack(anchor=tk.W)
                else:
                    tk.Label(
                        selection_frame,
                        text="💡 Example: ls -la, python script.py, npm install",
                        font=("Segoe UI", 9),
                        bg="#f5f7fa",
                        fg="#718096"
                    ).pack(anchor=tk.W)
                
                entry = tk.Entry(selection_frame, font=("Segoe UI", 11), bg="white", fg="#2d3748", relief=tk.RIDGE, bd=1, highlightthickness=0)
                entry.pack(fill=tk.X, pady=5)
                
                # If editing, populate the command
                if is_edit and hasattr(self, '_edit_command') and self._edit_command:
                    entry.insert(0, self._edit_command)
                
                selection_frame.entry = entry
        
        tile_type_var.trace('w', update_selection_options)
        update_selection_options()
        
        # Color selection
        color_frame = tk.Frame(content_frame, bg="#f5f7fa")
        color_frame.pack(fill=tk.X, pady=10)
        tk.Label(
            color_frame,
            text="Tile Color:",
            font=("Segoe UI", 10, "bold"),
            bg="#f5f7fa",
            fg="#2d3748"
        ).pack(anchor=tk.W)
        
        color_var = tk.StringVar(value="#4f8cf7")
        colors = ["#4f8cf7", "#38a169", "#d69e2e", "#e53e3e", "#6b46c1", "#ed64a6", "#4299e1", "#48bb78", "#f6ad55", "#fc8181"]
        
        color_container = tk.Frame(color_frame, bg="#f5f7fa")
        color_container.pack(fill=tk.X, pady=5)
        
        for c in colors:
            rb = tk.Radiobutton(
                color_container,
                variable=color_var,
                value=c,
                bg=c,
                fg=c,
                selectcolor=c,
                indicatoron=0,
                width=4,
                height=2,
                relief=tk.RIDGE,
                bd=2,
                cursor="hand2"
            )
            rb.pack(side=tk.LEFT, padx=4, pady=4)
        
        # If editing, populate fields after color_var is defined
        if is_edit and edit_index is not None:
            tile = self.custom_tiles[edit_index]
            label_entry.insert(0, tile.get("label", ""))
            color_var.set(tile.get("color", "#4f8cf7"))
            
            # Parse action to determine type
            action = tile.get("action", "")
            if action.startswith("new_"):
                tile_type_var.set("template")
                template_name = action.replace("new_", "")
                self._edit_template_name = template_name
            elif action.startswith("cmd_"):
                # Check if it's an APD command or shell command
                cmd = action.replace("cmd_", "")
                if cmd.startswith("apd "):
                    tile_type_var.set("command")
                    self._edit_command = cmd.replace("apd ", "")
                else:
                    tile_type_var.set("shell")
                    self._edit_command = cmd
            else:
                tile_type_var.set("template")
                self._edit_template_name = ""
        
        # Preview
        preview_frame = tk.Frame(content_frame, bg="#f5f7fa")
        preview_frame.pack(fill=tk.X, pady=10)
        tk.Label(
            preview_frame,
            text="Preview:",
            font=("Segoe UI", 10, "bold"),
            bg="#f5f7fa",
            fg="#2d3748"
        ).pack(anchor=tk.W)
        
        preview_btn = tk.Button(
            preview_frame,
            text="🎯 Tile Preview",
            bg="#4f8cf7",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            relief=tk.RAISED,
            bd=0,
            padx=20,
            pady=10,
            state=tk.DISABLED
        )
        preview_btn.pack(fill=tk.X, pady=5)
        
        def update_preview(*args):
            label = label_entry.get().strip() or "Tile Preview"
            color = color_var.get()
            preview_btn.config(text=label, bg=color, state=tk.NORMAL)
        
        label_entry.bind('<KeyRelease>', update_preview)
        color_var.trace('w', lambda *args: update_preview())
        
        # Button bar at bottom
        btn_bar = tk.Frame(main_container, bg="white", relief=tk.RIDGE, bd=1, highlightbackground="#e2e8f0", highlightthickness=1)
        btn_bar.grid(row=1, column=0, sticky="ew", pady=(0, 0))
        btn_bar.columnconfigure(0, weight=1)
        btn_bar.columnconfigure(1, weight=1)
        
        def add_or_update_tile():
            label = label_entry.get().strip()
            if not label:
                messagebox.showerror("Error", "Tile label is required")
                return
            
            tile_type = tile_type_var.get()
            if tile_type == "template":
                if hasattr(selection_frame, 'combo'):
                    template = selection_frame.combo.get()
                    if not template:
                        messagebox.showerror("Error", "Template selection is required")
                        return
                    action = f"new_{template}"
                else:
                    messagebox.showerror("Error", "Template selection is required")
                    return
            elif tile_type == "command":
                if hasattr(selection_frame, 'entry'):
                    cmd = selection_frame.entry.get().strip()
                    if not cmd:
                        messagebox.showerror("Error", "Command is required")
                        return
                    # Auto-prepend 'apd' to the command
                    action = f"cmd_apd {cmd}"
                else:
                    messagebox.showerror("Error", "Command is required")
                    return
            elif tile_type == "shell":
                if hasattr(selection_frame, 'entry'):
                    cmd = selection_frame.entry.get().strip()
                    if not cmd:
                        messagebox.showerror("Error", "Command is required")
                        return
                    action = f"cmd_{cmd}"
                else:
                    messagebox.showerror("Error", "Command is required")
                    return
            else:
                messagebox.showerror("Error", "Invalid tile type")
                return
            
            color = color_var.get()
            
            # Use the edit_index from the outer scope
            nonlocal_edit_index = edit_index
            
            if nonlocal_edit_index is not None:
                # Update existing tile
                self.custom_tiles[nonlocal_edit_index] = {
                    "label": label,
                    "action": action,
                    "color": color
                }
                self._save_custom_tiles()
                self._render_tiles()
                dialog.destroy()
                self._log(f"✅ Updated tile: {label}", "success")
            else:
                # Add new tile
                self.custom_tiles.append({
                    "label": label,
                    "action": action,
                    "color": color
                })
                self._save_custom_tiles()
                self._render_tiles()
                dialog.destroy()
                self._log(f"✅ Added custom tile: {label}", "success")
        
        add_btn = tk.Button(
            btn_bar,
            text="💾 Save Tile" if is_edit else "➕ Add Tile",
            command=add_or_update_tile,
            bg="#4f8cf7",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief=tk.RAISED,
            bd=0,
            padx=40,
            pady=12,
            cursor="hand2",
            activebackground=self._lighten_color("#4f8cf7"),
            activeforeground="white"
        )
        add_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        cancel_btn = tk.Button(
            btn_bar,
            text="Cancel",
            command=dialog.destroy,
            bg="#e2e8f0",
            fg="#2d3748",
            font=("Segoe UI", 12),
            relief=tk.RAISED,
            bd=0,
            padx=40,
            pady=12,
            cursor="hand2",
            activebackground="#cbd5e0",
            activeforeground="#2d3748"
        )
        cancel_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Center the buttons in the bar
        btn_bar.columnconfigure(0, weight=1)
        btn_bar.columnconfigure(1, weight=1)
        
        # Initial preview update
        update_preview()
    
    def _delete_tile(self, index):
        """Delete a tile at the given index."""
        if 0 <= index < len(self.custom_tiles):
            tile = self.custom_tiles[index]
            confirm = messagebox.askyesno("Delete Tile", f"Delete '{tile['label']}'?")
            if confirm:
                del self.custom_tiles[index]
                self._save_custom_tiles()
                self._render_tiles()
                self._log(f"🗑️ Deleted tile: {tile['label']}", "warning")
    
    def _edit_tile(self, index):
        """Edit a tile at the given index."""
        if 0 <= index < len(self.custom_tiles):
            self._add_custom_tile(edit_index=index)
    
    def _edit_tiles_mode(self):
        """Toggle edit mode for tiles."""
        self.edit_mode = not self.edit_mode
        self._render_tiles()
        if self.edit_mode:
            self._log("✏️ Edit mode enabled - click ✕ on tiles to delete", "info")
        else:
            self._log("✅ Edit mode disabled", "info")
    
    def _reset_tiles(self):
        """Reset tiles to defaults."""
        confirm = messagebox.askyesno("Reset Tiles", "Reset all tiles to default?")
        if confirm:
            self.custom_tiles = self._get_default_tiles()
            self._save_custom_tiles()
            self.edit_mode = False
            self._render_tiles()
            self._log("🔄 Tiles reset to defaults", "info")

    def _filter_combobox(self, combobox, event, items):
        """Filter combobox items based on keyboard input."""
        # Ignore special keys
        if event.keysym in ['BackSpace', 'Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Caps_Lock', 'Tab', 'Return', 'Escape', 'Up', 'Down', 'Left', 'Right']:
            return
        
        # Get current typed text
        typed = combobox.get()
        
        # Filter items
        if typed:
            filtered = [item for item in items if typed.lower() in item.lower()]
            combobox['values'] = filtered
            if filtered:
                combobox.event_generate('<Down>')  # Open dropdown
        else:
            combobox['values'] = items
            combobox.event_generate('<Down>')
        
        # If only one match, autocomplete
        if len(filtered) == 1 and filtered[0].lower() == typed.lower():
            combobox.set(filtered[0])
            combobox.icursor(len(filtered[0]))
            combobox.event_generate('<Down>')

    def _update_stats(self):
        """Update the statistics on the dashboard."""
        projects = self.cli._load_projects_db()
        templates = self.cli.list_available_templates()
        
        # Count total dependencies across all projects
        total_deps = 0
        for project in projects:
            project_path = Path(project.get('path', ''))
            if project_path.exists():
                deps = self._count_dependencies(project_path)
                total_deps += deps
        
        if "📁 Projects" in self.stats_labels:
            self.stats_labels["📁 Projects"].config(text=str(len(projects)))
        if "📋 Templates" in self.stats_labels:
            self.stats_labels["📋 Templates"].config(text=str(len(templates)))
        if "📦 Dependencies" in self.stats_labels:
            self.stats_labels["📦 Dependencies"].config(text=str(total_deps))
        if "⚙️ Config" in self.stats_labels:
            self.stats_labels["⚙️ Config"].config(text="✅ OK")
    
    def _count_dependencies(self, project_path: Path) -> int:
        """Count total dependencies in a project."""
        count = 0
        
        # Count Python requirements
        req_file = project_path / 'requirements.txt'
        if req_file.exists():
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and not line.startswith('-'):
                            count += 1
            except:
                pass
        
        # Count Node.js dependencies
        package_file = project_path / 'package.json'
        if package_file.exists():
            try:
                import json
                with open(package_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    deps = data.get('dependencies', {})
                    dev_deps = data.get('devDependencies', {})
                    count += len(deps) + len(dev_deps)
            except:
                pass
        
        # Count Go dependencies
        if (project_path / 'go.mod').exists():
            try:
                with open(project_path / 'go.mod', 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('require'):
                            count += 1
            except:
                pass
        
        # Count Rust dependencies
        if (project_path / 'Cargo.toml').exists():
            try:
                with open(project_path / 'Cargo.toml', 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Rough count of dependencies
                    count += content.count('[dependencies]')
                    count += content.count('[dev-dependencies]')
            except:
                pass
        
        return count
    
    def _on_project_select(self, event):
        """Handle project selection."""
        selection = self.project_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        projects = self.cli._load_projects_db()
        if index < len(projects):
            project = projects[index]
            self._show_project_info(project)
    
    def _show_project_info(self, project):
        """Show project information in the info panel."""
        self.project_info_text.delete(1.0, tk.END)
        
        name = project.get('name', 'Unknown')
        ptype = project.get('type', 'Unknown')
        path = project.get('path', 'Unknown')
        created = project.get('created', 'Unknown')
        modified = project.get('modified', 'Unknown')
        size = project.get('size', 0)
        
        info = f"""
📁 Project: {name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Type: {ptype}
Path: {path}
Created: {created}
Modified: {modified}
Size: {self.cli.format_size(size)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        self.project_info_text.insert(1.0, info)
    
    def _on_template_select(self, event):
        """Handle template selection."""
        selection = self.template_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        templates = self.cli.list_available_templates()
        if index < len(templates):
            template_name = templates[index]
            self._show_template_info(template_name)
    
    def _show_template_info(self, template_name):
        """Show template information in the info panel."""
        self.template_info_text.delete(1.0, tk.END)
        
        manifest = self.cli.get_template_manifest(template_name)
        template_dir = self.cli.templates_dir / template_name
        
        info = f"""
📋 Template: {template_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Path: {template_dir}

"""
        if manifest:
            data = manifest.data
            info += f"""
Name: {data.get('name', 'Unknown')}
Version: {data.get('version', '1.0.0')}
Type: {data.get('type', 'files')}
Framework: {data.get('framework', 'custom')}
Description: {data.get('description', '')}

Variables:
"""
            for var in data.get('variables', []):
                required = " (required)" if var.get('required', False) else ""
                default = f" [default: {var.get('default', '')}]" if var.get('default') else ""
                info += f"  • {var.get('name', '')}: {var.get('description', '')}{required}{default}\n"
            
            info += f"""
Commands:
"""
            for cmd_type, cmds in data.get('commands', {}).items():
                if cmds:
                    info += f"  {cmd_type}:\n"
                    for cmd in cmds:
                        info += f"    • {cmd}\n"
        else:
            info += "No manifest found. Basic template."
        
        self.template_info_text.insert(1.0, info)
    
    def _new_project_dialog(self):
        """Show the new project dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("New Project")
        dialog.geometry("650x750")
        dialog.minsize(550, 600)
        dialog.configure(bg="#f5f7fa")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 500) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 400) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Main container with scroll
        main_container = tk.Frame(dialog, bg="#f5f7fa")
        main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=0)  # Button bar
        
        # Scrollable content area
        canvas_container = tk.Frame(main_container, bg="#f5f7fa")
        canvas_container.grid(row=0, column=0, sticky="nsew")
        canvas_container.columnconfigure(0, weight=1)
        canvas_container.rowconfigure(0, weight=1)
        
        canvas = tk.Canvas(canvas_container, bg="#f5f7fa", highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = tk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Content frame inside canvas
        frame = tk.Frame(canvas, bg="#f5f7fa")
        canvas.create_window((0, 0), window=frame, anchor="nw", width=canvas.winfo_width())
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(1, width=canvas.winfo_width())
        
        def on_canvas_configure(event):
            canvas.itemconfig(1, width=event.width)
        
        frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Content padding
        content_frame = tk.Frame(frame, bg="#f5f7fa")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=15)
        
        tk.Label(
            content_frame,
            text="🚀 Create New Project",
            font=("Segoe UI", 18, "bold"),
            bg="#f5f7fa",
            fg="#4f8cf7"
        ).pack(pady=(0, 15))
        
        # Project name
        name_frame = tk.Frame(content_frame, bg="#f5f7fa")
        name_frame.pack(fill=tk.X, pady=6)
        tk.Label(
            name_frame,
            text="Project Name:",
            font=("Segoe UI", 10, "bold"),
            bg="#f5f7fa",
            fg="#2d3748"
        ).pack(anchor=tk.W)
        name_entry = tk.Entry(name_frame, font=("Segoe UI", 11), bg="white", fg="#2d3748", relief=tk.RIDGE, bd=1, highlightthickness=0)
        name_entry.pack(fill=tk.X, pady=3)
        
        # Template selection
        template_frame = tk.Frame(content_frame, bg="#f5f7fa")
        template_frame.pack(fill=tk.X, pady=6)
        tk.Label(
            template_frame,
            text="Template:",
            font=("Segoe UI", 10, "bold"),
            bg="#f5f7fa",
            fg="#2d3748"
        ).pack(anchor=tk.W)
        
        template_var = tk.StringVar()
        template_combo = ttk.Combobox(template_frame, textvariable=template_var, font=("Segoe UI", 11), height=6)
        templates = self.cli.list_available_templates()
        template_combo['values'] = templates
        if templates:
            template_combo.set(templates[0])
        template_combo.pack(fill=tk.X, pady=3)
        # Bind key events for keyboard search in New Project dialog
        template_combo.bind('<KeyRelease>', lambda e: self._filter_combobox(template_combo, e, templates))
        # Prevent scroll from propagating to parent
        template_combo.bind('<MouseWheel>', lambda e: "break")
        template_combo.bind('<Button-4>', lambda e: "break")
        template_combo.bind('<Button-5>', lambda e: "break")
        
        # Variables frame (dynamic) - scrollable inside content
        variables_frame = tk.LabelFrame(content_frame, text=" Template Variables ", font=("Segoe UI", 10, "bold"), bg="white", fg="#2d3748", padx=12, pady=10)
        variables_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        variable_entries = {}
        
        # Initial population of template variables
        if templates:
            self._update_template_variables(content_frame, templates[0], variables_frame, variable_entries)
        
        template_combo.bind('<<ComboboxSelected>>', lambda e: self._update_template_variables(content_frame, template_var.get(), variables_frame, variable_entries))
        
        # Options
        options_frame = tk.LabelFrame(content_frame, text=" Options ", font=("Segoe UI", 10, "bold"), bg="white", fg="#2d3748", padx=12, pady=8)
        options_frame.pack(fill=tk.X, pady=5)
        
        git_var = tk.BooleanVar(value=self.cli.config['PROJECT'].getboolean('auto_git', False))
        venv_var = tk.BooleanVar(value=self.cli.config['PROJECT'].getboolean('auto_venv', True))
        open_var = tk.BooleanVar(value=self.cli.config['PROJECT'].getboolean('auto_open', False))
        
        tk.Checkbutton(options_frame, text="Initialize Git", variable=git_var, bg="white", fg="#2d3748", font=("Segoe UI", 10), selectcolor="#f5f7fa").pack(anchor=tk.W, pady=1)
        tk.Checkbutton(options_frame, text="Create Virtual Environment", variable=venv_var, bg="white", fg="#2d3748", font=("Segoe UI", 10), selectcolor="#f5f7fa").pack(anchor=tk.W, pady=1)
        tk.Checkbutton(options_frame, text="Open in Editor", variable=open_var, bg="white", fg="#2d3748", font=("Segoe UI", 10), selectcolor="#f5f7fa").pack(anchor=tk.W, pady=1)
        
        # Button bar at bottom (outside scroll area)
        btn_bar = tk.Frame(main_container, bg="white", relief=tk.RIDGE, bd=1, highlightbackground="#e2e8f0", highlightthickness=1)
        btn_bar.grid(row=1, column=0, sticky="ew", pady=(0, 0))
        btn_bar.columnconfigure(0, weight=1)
        btn_bar.columnconfigure(1, weight=1)
        
        def create_project():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Project name is required")
                return
            
            template = template_var.get()
            if not template:
                messagebox.showerror("Error", "Template is required")
                return
            
            # Collect variable values
            variables = {}
            for var_name, entry in variable_entries.items():
                value = entry.get().strip()
                if value:
                    variables[var_name] = value
                elif var_name == 'project_name':
                    variables[var_name] = name
            
            dialog.destroy()
            
            # Create the project
            self._set_status(f"Creating project: {name}")
            self._set_progress(0)
            
            def task():
                try:
                    self.cli.init_project(
                        project_type=template,
                        project_name=name,
                        interactive=False,
                        auto_git=git_var.get(),
                        auto_venv=venv_var.get(),
                        auto_open=open_var.get(),
                        cli_variables=variables
                    )
                    self.root.after(0, lambda: self._log(f"✅ Project '{name}' created successfully!", "success"))
                    self.root.after(0, self._refresh_all)
                except Exception as e:
                    self.root.after(0, lambda: self._log(f"❌ Error: {e}", "error"))
                    self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                finally:
                    self.root.after(0, lambda: self._set_progress(100))
                    self.root.after(0, lambda: self._set_status("Ready"))
            
            threading.Thread(target=task, daemon=True).start()
        
        # Create button with icon
        create_btn = tk.Button(
            btn_bar,
            text="✨ Create Project",
            command=create_project,
            bg="#4f8cf7",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief=tk.RAISED,
            bd=0,
            padx=40,
            pady=12,
            cursor="hand2",
            activebackground=self._lighten_color("#4f8cf7"),
            activeforeground="white"
        )
        create_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        cancel_btn = tk.Button(
            btn_bar,
            text="Cancel",
            command=dialog.destroy,
            bg="#e2e8f0",
            fg="#2d3748",
            font=("Segoe UI", 12),
            relief=tk.RAISED,
            bd=0,
            padx=40,
            pady=12,
            cursor="hand2",
            activebackground="#cbd5e0",
            activeforeground="#2d3748"
        )
        cancel_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Center the buttons in the bar
        btn_bar.columnconfigure(0, weight=1)
        btn_bar.columnconfigure(1, weight=1)
    
    def _new_project_with_template(self, template):
        """Create a new project with a specific template."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"New {template.capitalize()} Project")
        dialog.geometry("450x320")
        dialog.configure(bg="#f5f7fa")
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 320) // 2
        dialog.geometry(f"+{x}+{y}")
        
        frame = tk.Frame(dialog, bg="#f5f7fa")
        frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        tk.Label(
            frame,
            text=f"New {template.capitalize()} Project",
            font=("Segoe UI", 16, "bold"),
            bg="#f5f7fa",
            fg="#4f8cf7"
        ).pack(pady=(0, 15))
        
        name_frame = tk.Frame(frame, bg="#f5f7fa")
        name_frame.pack(fill=tk.X, pady=8)
        tk.Label(
            name_frame,
            text="Project Name:",
            font=("Segoe UI", 10, "bold"),
            bg="#f5f7fa",
            fg="#2d3748"
        ).pack(anchor=tk.W)
        name_entry = tk.Entry(name_frame, font=("Segoe UI", 11), bg="white", fg="#2d3748", relief=tk.RIDGE, bd=1, highlightthickness=0)
        name_entry.pack(fill=tk.X, pady=4)
        
        # Info label
        tk.Label(
            frame,
            text=f"Template: {template.capitalize()}",
            font=("Segoe UI", 10),
            bg="#f5f7fa",
            fg="#718096"
        ).pack(anchor=tk.W, pady=5)
        
        btn_frame = tk.Frame(frame, bg="#f5f7fa")
        btn_frame.pack(fill=tk.X, pady=15)
        
        def create():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Project name is required")
                return
            dialog.destroy()
            
            self._set_status(f"Creating {template} project: {name}")
            def task():
                try:
                    self.cli.init_project(
                        project_type=template,
                        project_name=name,
                        interactive=False
                    )
                    self.root.after(0, lambda: self._log(f"✅ {template.capitalize()} project '{name}' created!", "success"))
                    self.root.after(0, self._refresh_all)
                except Exception as e:
                    self.root.after(0, lambda: self._log(f"❌ Error: {e}", "error"))
                    self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                finally:
                    self.root.after(0, lambda: self._set_status("Ready"))
            
            threading.Thread(target=task, daemon=True).start()
        
        tk.Button(btn_frame, text="Create", command=create, bg="#4f8cf7", fg="white", font=("Segoe UI", 11, "bold"), relief=tk.RAISED, bd=0, padx=25, pady=10, cursor="hand2", activebackground=self._lighten_color("#4f8cf7"), activeforeground="white").pack(side=tk.RIGHT, padx=6)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, bg="#e2e8f0", fg="#2d3748", font=("Segoe UI", 11), relief=tk.RAISED, bd=0, padx=25, pady=10, cursor="hand2", activebackground="#cbd5e0", activeforeground="#2d3748").pack(side=tk.RIGHT, padx=6)
    
    def _open_project_dialog(self):
        """Open a project dialog."""
        selection = self.project_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Please select a project from the list")
            return
        self._open_selected_project()
    
    def _open_selected_project(self):
        """Open the selected project in the editor."""
        selection = self.project_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        projects = self.cli._load_projects_db()
        if index < len(projects):
            project = projects[index]
            name = project.get('name')
            if name:
                self._set_status(f"Opening project: {name}")
                self.cli.open_project(name)
                self._log(f"📂 Opened project: {name}", "info")
                self._set_status("Ready")
    
    def _delete_selected_project(self):
        """Delete the selected project."""
        selection = self.project_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        projects = self.cli._load_projects_db()
        if index < len(projects):
            project = projects[index]
            name = project.get('name')
            if name:
                confirm = messagebox.askyesno("Delete Project", f"Are you sure you want to delete '{name}'?")
                if confirm:
                    self._set_status(f"Deleting project: {name}")
                    self.cli.delete_project(name, force=True)
                    self._log(f"🗑️ Deleted project: {name}", "warning")
                    self._refresh_all()
                    self._set_status("Ready")
    
    def _show_templates(self):
        """Switch to the templates tab."""
        self.notebook.select(self.templates_tab)
        self._refresh_templates()
    
    def _show_projects(self):
        """Switch to the projects tab."""
        self.notebook.select(self.projects_tab)
        self._refresh_projects()
    
    def _show_config(self):
        """Switch to the config tab."""
        self.notebook.select(self.config_tab)
    
    def _import_template_dialog(self):
        """Show the import template dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Import Template")
        dialog.geometry("600x520")
        dialog.minsize(500, 450)
        dialog.configure(bg="#f5f7fa")
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 600) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 520) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Main container with scroll
        main_container = tk.Frame(dialog, bg="#f5f7fa")
        main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=0)  # Button bar
        
        # Scrollable content area
        canvas_container = tk.Frame(main_container, bg="#f5f7fa")
        canvas_container.grid(row=0, column=0, sticky="nsew")
        canvas_container.columnconfigure(0, weight=1)
        canvas_container.rowconfigure(0, weight=1)
        
        canvas = tk.Canvas(canvas_container, bg="#f5f7fa", highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = tk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Content frame inside canvas
        frame = tk.Frame(canvas, bg="#f5f7fa")
        canvas.create_window((0, 0), window=frame, anchor="nw", width=canvas.winfo_width())
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(1, width=canvas.winfo_width())
        
        def on_canvas_configure(event):
            canvas.itemconfig(1, width=event.width)
        
        frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Content padding
        content_frame = tk.Frame(frame, bg="#f5f7fa")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        
        tk.Label(
            content_frame,
            text="📥 Import Template",
            font=("Segoe UI", 18, "bold"),
            bg="#f5f7fa",
            fg="#38a169"
        ).pack(pady=(0, 15))
        
        # Source type selection
        source_frame = tk.Frame(content_frame, bg="#f5f7fa")
        source_frame.pack(fill=tk.X, pady=8)
        tk.Label(
            source_frame,
            text="Source:",
            font=("Segoe UI", 10, "bold"),
            bg="#f5f7fa",
            fg="#2d3748"
        ).pack(anchor=tk.W)
        
        source_var = tk.StringVar(value="url")
        tk.Radiobutton(source_frame, text="URL", variable=source_var, value="url", bg="#f5f7fa", fg="#2d3748", font=("Segoe UI", 10), selectcolor="#f5f7fa").pack(anchor=tk.W, pady=3)
        tk.Radiobutton(source_frame, text="Local File", variable=source_var, value="file", bg="#f5f7fa", fg="#2d3748", font=("Segoe UI", 10), selectcolor="#f5f7fa").pack(anchor=tk.W, pady=3)
        
        # Input
        input_frame = tk.Frame(content_frame, bg="#f5f7fa")
        input_frame.pack(fill=tk.X, pady=10)
        tk.Label(
            input_frame,
            text="URL or File Path:",
            font=("Segoe UI", 10, "bold"),
            bg="#f5f7fa",
            fg="#2d3748"
        ).pack(anchor=tk.W)
        input_entry = tk.Entry(input_frame, font=("Segoe UI", 11), bg="white", fg="#2d3748", relief=tk.RIDGE, bd=1, highlightthickness=0)
        input_entry.pack(fill=tk.X, pady=5)
        
        # Browse button (for file)
        def browse_file():
            file_path = filedialog.askopenfilename(
                title="Select Template Archive",
                filetypes=[("Archive files", "*.zip *.tar.gz *.tgz *.tar"), ("All files", "*.*")]
            )
            if file_path:
                input_entry.delete(0, tk.END)
                input_entry.insert(0, file_path)
        
        tk.Button(input_frame, text="📂 Browse", command=browse_file, bg="#e2e8f0", fg="#2d3748", font=("Segoe UI", 10), relief=tk.RAISED, bd=0, padx=20, pady=6, cursor="hand2", activebackground="#cbd5e0", activeforeground="#2d3748").pack(anchor=tk.W, pady=5)
        
        # Name
        name_frame = tk.Frame(content_frame, bg="#f5f7fa")
        name_frame.pack(fill=tk.X, pady=8)
        tk.Label(
            name_frame,
            text="Template Name (optional):",
            font=("Segoe UI", 10, "bold"),
            bg="#f5f7fa",
            fg="#2d3748"
        ).pack(anchor=tk.W)
        name_entry = tk.Entry(name_frame, font=("Segoe UI", 11), bg="white", fg="#2d3748", relief=tk.RIDGE, bd=1, highlightthickness=0)
        name_entry.pack(fill=tk.X, pady=5)
        
        # Info text
        info_frame = tk.Frame(content_frame, bg="#f5f7fa")
        info_frame.pack(fill=tk.X, pady=8)
        tk.Label(
            info_frame,
            text="💡 Supported formats: .zip, .tar.gz, .tgz, .tar",
            font=("Segoe UI", 9),
            bg="#f5f7fa",
            fg="#718096"
        ).pack(anchor=tk.W)
        
        # Button bar at bottom
        btn_bar = tk.Frame(main_container, bg="white", relief=tk.RIDGE, bd=1, highlightbackground="#e2e8f0", highlightthickness=1)
        btn_bar.grid(row=1, column=0, sticky="ew", pady=(0, 0))
        btn_bar.columnconfigure(0, weight=1)
        btn_bar.columnconfigure(1, weight=1)
        
        def import_template():
            source = input_entry.get().strip()
            if not source:
                messagebox.showerror("Error", "URL or file path is required")
                return
            
            template_name = name_entry.get().strip() or None
            
            dialog.destroy()
            self._set_status(f"Importing template from: {source}")
            
            def task():
                try:
                    self.cli.import_template(source)
                    self.root.after(0, lambda: self._log(f"✅ Template imported successfully!", "success"))
                    self.root.after(0, self._refresh_all)
                except Exception as e:
                    self.root.after(0, lambda: self._log(f"❌ Error: {e}", "error"))
                    self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                finally:
                    self.root.after(0, lambda: self._set_status("Ready"))
            
            threading.Thread(target=task, daemon=True).start()
        
        import_btn = tk.Button(
            btn_bar,
            text="📥 Import Template",
            command=import_template,
            bg="#38a169",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief=tk.RAISED,
            bd=0,
            padx=40,
            pady=12,
            cursor="hand2",
            activebackground=self._lighten_color("#38a169"),
            activeforeground="white"
        )
        import_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        cancel_btn = tk.Button(
            btn_bar,
            text="Cancel",
            command=dialog.destroy,
            bg="#e2e8f0",
            fg="#2d3748",
            font=("Segoe UI", 12),
            relief=tk.RAISED,
            bd=0,
            padx=40,
            pady=12,
            cursor="hand2",
            activebackground="#cbd5e0",
            activeforeground="#2d3748"
        )
        cancel_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Center the buttons in the bar
        btn_bar.columnconfigure(0, weight=1)
        btn_bar.columnconfigure(1, weight=1)
    
    def _preview_template(self):
        """Preview the selected template."""
        selection = self.template_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        templates = self.cli.list_available_templates()
        if index < len(templates):
            template_name = templates[index]
            self.cli.preview_template(template_name)
            self._log(f"📋 Previewed template: {template_name}", "info")
    
    def _export_template(self):
        """Export the selected template."""
        selection = self.template_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        templates = self.cli.list_available_templates()
        if index < len(templates):
            template_name = templates[index]
            save_path = filedialog.asksaveasfilename(
                title=f"Export Template: {template_name}",
                defaultextension=".zip",
                filetypes=[("ZIP files", "*.zip")]
            )
            if save_path:
                self._set_status(f"Exporting template: {template_name}")
                self.cli.export_template(template_name)
                self._log(f"📦 Exported template: {template_name}", "success")
                self._set_status("Ready")
    
    def _run_doctor(self):
        """Run the doctor command."""
        # Switch to output tab
        self.notebook.select(self.output_tab)
        self._set_status("Running doctor...")
        self._log("🔍 Running system doctor...", "info")
        
        def task():
            try:
                # Capture output
                import io
                import contextlib
                with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                    self.cli.run_doctor()
                    output = buf.getvalue()
                self.root.after(0, lambda: self._log(output, "info"))
                self.root.after(0, lambda: self._log("✅ Doctor completed", "success"))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"❌ Error: {e}", "error"))
            finally:
                self.root.after(0, lambda: self._set_status("Ready"))
        
        threading.Thread(target=task, daemon=True).start()
    
    def _audit_all(self):
        """Run audit on all projects."""
        # Switch to output tab
        self.notebook.select(self.output_tab)
        self._set_status("Auditing all projects...")
        self._log("🔍 Auditing all projects...", "info")
        
        def task():
            try:
                import io
                import contextlib
                with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                    self.cli.audit_all_projects()
                    output = buf.getvalue()
                self.root.after(0, lambda: self._log(output, "info"))
                self.root.after(0, lambda: self._log("✅ Audit completed", "success"))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"❌ Error: {e}", "error"))
            finally:
                self.root.after(0, lambda: self._set_status("Ready"))
        
        threading.Thread(target=task, daemon=True).start()
    
    def _update_template_variables(self, parent, template_name, variables_frame, variable_entries):
        """Update the template variables section based on selected template."""
        # Clear existing variable widgets
        for widget in variables_frame.winfo_children():
            widget.destroy()
        variable_entries.clear()
        
        if not template_name:
            tk.Label(
                variables_frame,
                text="Select a template to see variables",
                font=("Segoe UI", 10),
                bg="white",
                fg="#718096"
            ).pack(anchor=tk.W, pady=5)
            return
        
        manifest = self.cli.get_template_manifest(template_name)
        if not manifest:
            tk.Label(
                variables_frame,
                text="No manifest found for this template",
                font=("Segoe UI", 10),
                bg="white",
                fg="#718096"
            ).pack(anchor=tk.W, pady=5)
            return
        
        variables = manifest.data.get('variables', [])
        if not variables:
            tk.Label(
                variables_frame,
                text="No variables defined for this template",
                font=("Segoe UI", 10),
                bg="white",
                fg="#718096"
            ).pack(anchor=tk.W, pady=5)
            return
        
        # Render each variable as a labeled entry
        for var_info in variables:
            name = var_info.get('name', '')
            if not name:
                continue
                
            description = var_info.get('description', name)
            default = var_info.get('default', '')
            required = var_info.get('required', False)
            
            if name == 'project_name':
                continue  # Skip project_name as it's already handled separately
            
            var_frame = tk.Frame(variables_frame, bg="white")
            var_frame.pack(fill=tk.X, pady=5)
            
            label_text = f"{name}"
            if required:
                label_text += " *"
            label = tk.Label(
                var_frame,
                text=label_text,
                font=("Segoe UI", 10, "bold" if required else "normal"),
                bg="white",
                fg="#e53e3e" if required else "#2d3748"
            )
            label.pack(anchor=tk.W)
            
            # Description as small text
            if description and description != name:
                tk.Label(
                    var_frame,
                    text=description,
                    font=("Segoe UI", 9),
                    bg="white",
                    fg="#718096"
                ).pack(anchor=tk.W)
            
            entry = tk.Entry(var_frame, font=("Segoe UI", 10), bg="white", fg="#2d3748", relief=tk.RIDGE, bd=1, highlightthickness=0)
            if default:
                entry.insert(0, default)
            entry.pack(fill=tk.X, pady=3)
            variable_entries[name] = entry
        
        # If no variables were added (other than project_name), show a message
        if not variable_entries:
            tk.Label(
                variables_frame,
                text="All variables are pre-configured",
                font=("Segoe UI", 10),
                bg="white",
                fg="#718096"
            ).pack(anchor=tk.W, pady=5)
    
    def _save_config(self):
        """Save the configuration."""
        try:
            # Save text entries
            text_keys = ['default_template', 'editor', 'license', 'author', 'email']
            for key in text_keys:
                if key in self.config_entries:
                    entry = self.config_entries[key]
                    value = entry.get()
                    if key in ['author', 'email', 'license']:
                        self.cli.config['PROJECT'][key] = value
                    else:
                        self.cli.config['DEFAULT'][key] = value
            
            # Save boolean values
            bool_keys = ['auto_git', 'auto_venv', 'auto_open', 'telemetry', 'auto_update', 'mirror_enabled']
            for key in bool_keys:
                if key in self.config_entries:
                    var = self.config_entries[key]
                    if key == 'mirror_enabled':
                        self.cli.config['MIRROR']['enabled'] = 'true' if var.get() else 'false'
                    elif key in ['auto_git', 'auto_venv', 'auto_open']:
                        self.cli.config['PROJECT'][key] = 'true' if var.get() else 'false'
                    else:
                        self.cli.config['DEFAULT'][key] = 'true' if var.get() else 'false'
            
            self.cli.save_config()
            self._log("✅ Configuration saved!", "success")
            self._set_status("Configuration saved")
            messagebox.showinfo("Success", "Configuration saved successfully!")
        except Exception as e:
            self._log(f"❌ Error saving config: {e}", "error")
            messagebox.showerror("Error", f"Failed to save config: {e}")
    
    def _on_close(self):
        """Handle window close."""
        if messagebox.askokcancel("Quit", "Do you want to quit APD?"):
            self.root.destroy()

def create_wrapper_scripts():
    """Create wrapper scripts for apd command"""
    
    # Windows batch file
    batch_content = """@echo off
:: apd.bat - Wrapper for APD
:: Version: 3.0.0

setlocal enabledelayedexpansion

:: Check if Python is available
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.7 or higher.
    pause
    exit /b 1
)

:: Get script directory
set "SCRIPT_DIR=%~dp0"

:: Run apd.py with arguments
python "%SCRIPT_DIR%\\apd.py" %*

:: Preserve exit code
exit /b %errorlevel%
"""
    
    # PowerShell script
    ps_content = """# apd.ps1 - PowerShell wrapper for APD
# Version: 3.0.0

param([string[]]$Arguments)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$pythonScript = Join-Path $scriptDir "apd.py"

# Check if Python is available
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $python) {
    Write-Host "❌ Python not found. Please install Python 3.7 or higher." -ForegroundColor Red
    exit 1
}

if (Test-Path $pythonScript) {
    & $python.Source $pythonScript $Arguments
    exit $LASTEXITCODE
} else {
    Write-Host "❌ Error: Could not find apd.py" -ForegroundColor Red
    exit 1
}
"""
    
    # Bash script for Unix-like systems
    bash_content = """#!/bin/bash
# apd.sh - Bash wrapper for APD
# Version: 3.0.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/apd.py"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python not found. Please install Python 3.7 or higher."
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# Check if script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Error: Could not find apd.py"
    exit 1
fi

# Run apd.py with arguments
"$PYTHON_CMD" "$PYTHON_SCRIPT" "$@"
exit $?
"""
    
    # Create install script
    install_content = """#!/bin/bash
# install.sh - Install APD wrapper
# Version: 3.0.0

echo "🔧 Installing APD wrapper..."

# Determine platform
case "$(uname -s)" in
    Linux*)     PLATFORM="linux";;
    Darwin*)    PLATFORM="macos";;
    CYGWIN*|MINGW*|MSYS*) PLATFORM="windows";;
    *)          PLATFORM="unknown";;
esac

echo "Platform: $PLATFORM"

# Check Python
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python not found. Please install Python 3.7 or higher."
        exit 1
    fi
fi

# Copy wrapper to appropriate location
if [ "$PLATFORM" = "windows" ]; then
    # Windows
    if [ -d "$HOME/bin" ]; then
        cp apd.bat "$HOME/bin/"
        echo "✅ Copied apd.bat to $HOME/bin/"
    elif [ -d "/usr/local/bin" ]; then
        cp apd.bat "/usr/local/bin/"
        echo "✅ Copied apd.bat to /usr/local/bin/"
    else
        echo "⚠️  Could not find suitable location for wrapper"
        echo "   You can manually add current directory to PATH"
    fi
else
    # Unix-like
    if [ -d "$HOME/.local/bin" ]; then
        cp apd.sh "$HOME/.local/bin/apd"
        chmod +x "$HOME/.local/bin/apd"
        echo "✅ Installed apd to $HOME/.local/bin/apd"
    elif [ -d "/usr/local/bin" ]; then
        sudo cp apd.sh "/usr/local/bin/apd"
        sudo chmod +x "/usr/local/bin/apd"
        echo "✅ Installed apd to /usr/local/bin/apd"
    else
        echo "⚠️  Could not find suitable location for wrapper"
        echo "   You can manually add current directory to PATH"
    fi
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "To use apd:"
echo "  1. Open a new terminal"
echo "  2. Run: apd --help"
echo ""
echo "If 'apd' command doesn't work, you may need to:"
echo "  • Add the installation directory to PATH"
echo "  • Restart your terminal"
"""
    
    # Save wrapper scripts
    wrappers = [
        ("apd.bat", batch_content),
        ("apd.ps1", ps_content, None, True),
        ("apd.sh", bash_content, 0o755),
        ("install.sh", install_content, 0o755)
    ]
    
    print("\n🔧 Creating wrapper scripts...")
    
    for wrapper in wrappers:
        filename = wrapper[0]
        content = wrapper[1]
        
        if len(wrapper) > 2:
            mode = wrapper[2]
        else:
            mode = None
            
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if mode:
            os.chmod(filename, mode)
        
        print(f"✅ Created: {filename}")
    
    print("\n📋 Wrapper scripts created successfully!")
    print("\n📝 To install apd system-wide:")
    print("  Linux/macOS: ./install.sh")
    print("  Windows: Copy apd.bat to a directory in PATH")
    print("\n💡 Or add current directory to PATH and use:")
    print("  apd --help")

def main():
    """Main entry point"""
    # Create wrapper scripts if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--create-wrappers':
        create_wrapper_scripts()
        return
    
    # Normal CLI execution
    cli = ILIACLI()
    cli.run(sys.argv[1:])

if __name__ == "__main__":
    main()
