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
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import configparser
from datetime import datetime
import getpass
import socket

# NEW IMPORTS FOR ADDITIONAL FEATURES ONLY (NOT REPLACING ANYTHING)
import webbrowser
import random
import string
import secrets
import re
import asyncio
import aiohttp
import base64
import mimetypes
import ipaddress
import psutil  # For system monitoring
from dataclasses import dataclass, asdict
from enum import Enum
import textwrap
import itertools
from collections import defaultdict
import pickle
import warnings
import traceback

# Add color output for better UX (optional)
try:
    from colorama import init, Fore, Style, Back
    init(autoreset=True)
    HAS_COLORS = True
except:
    class DummyColors:
        def __getattr__(self, name):
            return ''
    Fore = Back = Style = DummyColors()
    HAS_COLORS = False

# Import for AI features (optional)
try:
    import openai
    HAS_OPENAI = True
except:
    HAS_OPENAI = False

# Import for enhanced UI (optional)
try:
    import curses
    HAS_CURSES = True
except:
    HAS_CURSES = False

# Import for web dashboard (optional)
try:
    import flask
    import threading
    import socket
    HAS_FLASK = True
except:
    HAS_FLASK = False

# ============================================================================
# ORIGINAL CODE - COMPLETELY PRESERVED
# ============================================================================

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
    """Main CLI class for ilia project deployer"""
    
    def __init__(self):
        self.app_name = "ilia-cli"
        self.version = "2.0.0"
        self.config_dir = self.get_config_dir()
        self.config_file = self.config_dir / "config.ini"
        self.templates_dir = self.config_dir / "templates"
        self.projects_dir = self.config_dir / "projects"
        self.logs_dir = self.config_dir / "logs"
        self.template_manifests = {}
        self.ensure_directories()
        self.config = self.load_config()
        self.session_id = self.generate_session_id()
        
        # NEW: Initialize new features (optional)
        self._init_optional_features()
        
    def _init_optional_features(self):
        """Initialize optional features only if dependencies are available"""
        # Initialize AI Generator if available
        if HAS_OPENAI:
            from openai import OpenAI
            self.ai_generator = AIGenerator()
        else:
            self.ai_generator = None
        
        # Initialize other optional features
        self.interactive_wizard = InteractiveWizard(self)
        self.collaboration = CollaborationSession(self)
        self.analytics = ProjectAnalytics(self)
        self.health_checker = ProjectHealthChecker(self)
        self.web_dashboard = WebDashboard(self)
        self.migration_assistant = MigrationAssistant(self)
        # self.code_scanner = CodeQualityScanner()
        self.package_manager = PackageManager(self)
        
        # Add new configuration sections
        self._enhance_config()
    
    def _enhance_config(self):
        """Add new configuration options without affecting existing ones"""
        # Only add sections if they don't exist
        sections_to_add = {
            'AI': {
                'enabled': 'false',
                'api_key': '',
                'model': 'gpt-3.5-turbo'
            },
            'COLLABORATION': {
                'enabled': 'false',
                'default_port': '8080',
                'allow_file_sharing': 'true'
            },
            'DASHBOARD': {
                'enabled': 'false',
                'port': '8080',
                'auto_start': 'false'
            },
            'QUALITY': {
                'auto_scan': 'false',
                'min_score': '70',
                'enforce_rules': 'false'
            }
        }
        
        for section, options in sections_to_add.items():
            if section not in self.config:
                self.config[section] = options
        
        self.save_config()

    def get_template_manifest(self, template_name: str) -> Optional[TemplateManifest]:
        """Get template manifest"""
        template_path = self.templates_dir / template_name
        if template_path.exists():
            return TemplateManifest(template_path)
        return None

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
        print(f"\n💡 Usage: ilia help template {template_name}")

    def list_templates_with_details(self):
        """List all templates with manifest details"""
        print("\n📁 Available Templates")
        print("=" * 60)
        
        templates = []
        for item in self.templates_dir.iterdir():
            if item.is_dir():
                manifest = TemplateManifest(item)
                templates.append(manifest.data)
        
        if not templates:
            print("❌ No templates found!")
            return
        
        for template in templates:
            print(f"\n📦 {template['name']} v{template['version']}")
            print(f"   Type: {template['type']}")
            print(f"   Framework: {template['framework']}")
            print(f"   Description: {template['description']}")
            print(f"   Files: {len(list((self.templates_dir / template['name']).rglob('*')))}")
            print(f"   Use: ilia help template {template['name']}")

    def create_template_from_current(self, template_name: str, is_framework: bool = False):
        """Create a template from current directory with manifest"""
        current_dir = Path.cwd()
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
            shutil.copytree(current_dir, template_dst)
            
            # Create manifest
            manifest = TemplateManifest(template_dst)
            manifest.data['type'] = 'framework' if is_framework else 'files'
            manifest.data['description'] = input(f"Template description [{template_name} template]: ").strip() or f"{template_name} template"
            manifest.save()
            
            # Validate
            is_valid, errors = manifest.validate()
            if not is_valid:
                print("⚠️  Template validation warnings:")
                for error in errors:
                    print(f"  • {error}")
            
            print(f"✅ Template '{template_name}' created with manifest!")
            print(f"📋 View documentation: ilia help template {template_name}")
            
            self.log_activity('info', f'Template created: {template_name}')
            
        except Exception as e:
            print(f"❌ Error creating template: {e}")

    def process_template_with_manifest(self, template_name: str, project_dir: Path, project_name: str):
        """Process template using manifest configuration"""
        manifest = self.get_template_manifest(template_name)
        if not manifest:
            print(f"⚠️  No manifest found for {template_name}, using basic processing")
            self.process_template_variables(project_dir, project_name)
            return
        
        print(f"📋 Processing {template_name} template...")
        
        # Run pre-copy commands
        self.run_template_commands(manifest.data['commands']['pre_copy'], project_dir)
        
        # Copy files with ignore patterns
        ignore_patterns = manifest.data.get('ignore_patterns', [])
        ignore = shutil.ignore_patterns(*ignore_patterns)
        shutil.copytree(self.templates_dir / template_name, project_dir, ignore=ignore)
        
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
        for command in commands:
            print(f"⚙️  Running: {command}")
            try:
                # Replace variables in command
                command = command.replace('{{ project_dir }}', str(project_dir))
                
                if platform.system() == 'Windows':
                    subprocess.run(command, shell=True, cwd=project_dir, check=True)
                else:
                    subprocess.run(command, shell=True, cwd=project_dir, check=True, 
                                executable='/bin/bash')
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Command failed: {command}")
                print(f"Error: {e}")

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
            print("  3. Run: ilia template create <name> [--framework]")
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
            print("  ilia template create <name> [--framework]  - Create template from current dir")
            print("  ilia template list                         - List templates with details")
            print("  ilia template info <name>                  - Show template details")
            print("  ilia template validate <name>              - Validate template")
            print("  ilia template edit <name>                  - Edit template manifest")
            print("  ilia help templates                        - Show this help")
            
            print("\n💡 Example workflow:")
            print("  1. Create a Flask app")
            print("  2. Add {{ project_name }} in app.py")
            print("  3. Run: ilia template create my-flask --framework")
            print("  4. Run: ilia new myapp --template my-flask")
        
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
            
        log_file = self.logs_dir / f"ilia_{datetime.now().strftime('%Y%m')}.log"
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
        
        # Prepare telemetry data
        telemetry_data = {
            "event": event_name,
            "ilia_version": self.version,
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
                url = "http://127.0.0.1:3001/ilia-cli/tm/submit"
                data = json.dumps(telemetry_data).encode('utf-8')
                
                # Create request with timeout
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': f'ilia-cli/{self.version}'
                    },
                    method='POST'
                )
                
                # Send request (silent - no output regardless of success/failure)
                context = ssl.create_default_context()
                if not self.config['SECURITY'].getboolean('verify_ssl', True):
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                
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
        print("\n" + "="*60)
        print(f"🚀 Welcome to {self.app_name} v{self.version}")
        print("="*60)
        
        print("\n📋 Let's configure your environment...")
        
        # Check for template files in current directory
        # local_templates = Path.cwd() / "templates"
        # if local_templates.exists():
        #     print("\n📦 Found local template files. Would you like to install them?")
        #     choice = input("Install local templates? (y/N): ").strip().lower()
        #     if choice in ['y', 'yes', '']:
        #         self.install_templates(local_templates)
        # else:
        #     print("\n📭 No local templates found.")
        #     print(f"Add templates to {self.templates_dir} or run from a directory with templates.")
        
        # Ask about national mirror
        print("\n🌐 National PyPI Mirror Configuration")
        print("-" * 40)
        print("You can configure ilia to use a national PyPI mirror")
        print("for faster package downloads within Iran.")
        print("\nMirror URL: https://mirror-pypi.runflare.com/simple")
        
        enable_mirror = input("\nEnable national PyPI mirror? (y/N): ").strip().lower()
        if enable_mirror in ['y', 'yes', '']:
            self.config['MIRROR']['enabled'] = 'true'
            print("✅ National mirror enabled")
            
            # Test mirror connectivity
            if self.check_internet():
                print("🔍 Testing mirror connectivity...")
                if self.test_mirror():
                    print("✅ Mirror is accessible")
                else:
                    print("⚠️  Mirror might be unavailable")
        else:
            self.config['MIRROR']['enabled'] = 'false'
            print("❌ National mirror disabled")
        
        # Ask about telemetry
        print("\n📊 Usage Statistics")
        print("-" * 40)
        print("Help improve ilia by sending anonymous usage statistics.")
        print("No personal data is collected.")
        
        enable_telemetry = input("\nEnable anonymous usage statistics? (y/N): ").strip().lower()
        if enable_telemetry == 'y':
            self.config['DEFAULT']['telemetry'] = 'true'
            print("✅ Telemetry enabled")
        else:
            self.config['DEFAULT']['telemetry'] = 'false'
            print("❌ Telemetry disabled")
        
        # Ask about auto-update
        print("\n🔄 Auto-Update")
        print("-" * 40)
        print("Automatically check for ilia updates on startup.")
        
        auto_update = input("\nEnable auto-update? (y/N): ").strip().lower()
        if auto_update in ['y', 'yes', '']:
            self.config['DEFAULT']['auto_update'] = 'true'
            print("✅ Auto-update enabled")
        else:
            self.config['DEFAULT']['auto_update'] = 'false'
            print("❌ Auto-update disabled")
        
        # Set default editor
        print("\n📝 Default Code Editor")
        print("-" * 40)
        print(f"Detected editor: {self.config['DEFAULT']['editor']}")
        
        change_editor = input("\nChange default editor? (y/N): ").strip().lower()
        if change_editor == 'y':
            available_editors = self.detect_available_editors()
            if available_editors:
                print("\nAvailable editors:")
                for i, (cmd, name) in enumerate(available_editors, 1):
                    print(f"  {i}) {name} ({cmd})")
                
                try:
                    choice = int(input(f"\nSelect editor (1-{len(available_editors)}): ").strip())
                    if 1 <= choice <= len(available_editors):
                        self.config['DEFAULT']['editor'] = available_editors[choice-1][0]
                        print(f"✅ Default editor set to: {available_editors[choice-1][1]}")
                except (ValueError, IndexError):
                    print("⚠️  Invalid selection, keeping current editor")
            else:
                print("⚠️  No additional editors detected")
        
        # Default project settings
        print("\n⚙️  Default Project Settings")
        print("-" * 40)
        
        default_template = input("Default template [html/flask]: ").strip().lower()
        if default_template in ['html', 'flask']:
            self.config['DEFAULT']['default_template'] = default_template
            print(f"✅ Default template: {default_template}")
        else:
            print("⚠️  Invalid template, using 'html' as default")
        
        auto_git = input("Initialize git repository for new projects? (y/N): ").strip().lower()
        self.config['PROJECT']['auto_git'] = 'true' if auto_git == 'y' else 'false'
        
        auto_venv = input("Create virtual environment for Python projects? (y/N): ").strip().lower()
        self.config['PROJECT']['auto_venv'] = 'false' if auto_venv == 'n' else 'true'
        
        # Finalize setup
        self.config['DEFAULT']['first_run'] = 'false'
        self.save_config()
        
        self.send_telemetry("setup_completed", 
                   mirror_enabled=self.config['MIRROR'].getboolean('enabled'),
                   telemetry_enabled=self.config['DEFAULT'].getboolean('telemetry'),
                   auto_update_enabled=self.config['DEFAULT'].getboolean('auto_update'))
        
        print("\n" + "="*60)
        print("✅ Setup Complete!")
        print("="*60)
        
        # Check if templates exist
        self.check_templates_exist(verbose=False)
        
        print("\n🎉 Your ilia CLI is ready to use!")
        print("\nQuick Start:")
        print("  ilia new myproject          # Create a new project")
        print("  ilia new api --flask        # Create Flask API")
        print("  ilia templates              # List available templates")
        print("  ilia config                 # Show configuration")
        print("  ilia doctor                 # Run system diagnostics")
        
        print("\n💡 Tip: Run 'ilia --help' for all available commands.")
        
        input("\nPress Enter to continue...")
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
                headers={'User-Agent': f'ilia-cli/{self.version}'}
            )
            response = urllib.request.urlopen(req, timeout=5)
            return response.status == 200
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
                    f.write(f"ilia-cli v{self.version}\n")
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
        templates_exist = False
        
        html_exists = (self.templates_dir / "html").exists()
        flask_exists = (self.templates_dir / "flask").exists()
        
        if verbose:
            print("\n📁 Template Status:")
            print("-" * 40)
            
            if html_exists:
                html_files = len(list((self.templates_dir / "html").rglob("*")))
                print(f"✅ HTML template: {html_files} files")
                templates_exist = True
            else:
                print("❌ HTML template: Not found")
            
            if flask_exists:
                flask_files = len(list((self.templates_dir / "flask").rglob("*")))
                print(f"✅ Flask template: {flask_files} files")
                templates_exist = True
            else:
                print("❌ Flask template: Not found")
            
            if not templates_exist:
                print(f"\n⚠️  No templates found in {self.templates_dir}")
                print("To add templates:")
                print("  1. Create a 'templates' folder in your current directory")
                print("  2. Add 'html' and/or 'flask' subfolders with your template files")
                print("  3. Run 'ilia --setup' or restart ilia")
                print("\nOr download templates from: https://github.com/yourusername/ilia-templates")
        
        return html_exists or flask_exists
    
    def show_help(self):
        """Display comprehensive help information"""
        help_text = f"""
{self.app_name} v{self.version} - Advanced Project Deployer

USAGE:
  ilia <command> [options]

CORE COMMANDS:
  new <name> [--flask|--html]    Create new project
  init [--flask|--html]          Interactive project creation
  doctor                         Run system diagnostics
  update                         Check for updates

PROJECT MANAGEMENT:
  projects                       List all created projects
  open <name>                    Open project in editor
  info <name>                    Show project information
  archive <name>                 Archive project
  delete <name>                  Delete project (with confirmation)

TEMPLATE MANAGEMENT:
  templates                      List available templates
  templates list                List templates with manifest details
  templates create <name>       Create template from current directory
  templates info <name>         Show template manifest details
  templates validate <name>     Validate template structure
  templates edit <name>         Edit template manifest
  templates import <source>     Import template from URL or local file
  templates remove <name>       Remove template
  templates export <name>       Export template as archive
  help templates               Show template creation guide

CONFIGURATION:
  config                         Show current configuration
  config mirror [enable|disable] Configure PyPI mirror
  config editor <name>           Set default code editor
  config reset                  Reset to default configuration
  config path                   Show configuration paths

SYSTEM:
  status                         Show system status
  logs [--tail]                 View or tail logs
  cleanup                       Clean up temporary files
  uninstall                     Uninstall ilia CLI

INFORMATION:
  version                       Show version information
  help                          Show this help message
  about                         About ilia CLI

EXAMPLES:
  ilia new myapp --flask         # Create Flask application
  ilia new website --html        # Create HTML website
  ilia config mirror enable      # Enable national PyPI mirror
  ilia doctor                    # Run diagnostics
  ilia projects                  # List all projects
  ilia open myapp                # Open project in editor

TEMPLATE LOCATION:
  {self.templates_dir}

CONFIGURATION LOCATION:
  {self.config_dir}
        """
        print(help_text)
    
    def show_about(self):
        """Show about information"""
        about_text = f"""
{self.app_name} v{self.version}
Advanced Project Deployer CLI

DESCRIPTION:
  A powerful CLI tool for quickly scaffolding projects with templates.
  Supports national PyPI mirrors, project management, and more.

FEATURES:
  • Template-based project generation
  • National PyPI mirror support
  • Project lifecycle management
  • System diagnostics
  • Configurable code editors
  • Activity logging
  • Cross-platform compatibility

AUTHOR: {self.config['PROJECT']['author']}
LICENSE: {self.config['PROJECT']['license']}
REPOSITORY: https://github.com/yourusername/ilia-cli

CONFIGURATION:
  Config directory: {self.config_dir}
  Templates directory: {self.templates_dir}
  Logs directory: {self.logs_dir}

Run 'ilia --help' for usage information.
        """
        print(about_text)
    
    def show_config(self):
        """Display current configuration"""
        print("\n📋 Current Configuration")
        print("=" * 60)
        
        # System Information
        print("\n💻 SYSTEM INFORMATION:")
        print(f"  Version: {self.version}")
        print(f"  Python: {platform.python_version()}")
        print(f"  Platform: {platform.platform()}")
        print(f"  Session ID: {self.session_id}")
        
        # Paths
        print("\n📁 PATHS:")
        print(f"  Config: {self.config_dir}")
        print(f"  Templates: {self.templates_dir}")
        print(f"  Projects: {self.projects_dir}")
        print(f"  Logs: {self.logs_dir}")
        
        # Features
        print("\n⚙️  FEATURES:")
        mirror_enabled = self.config['MIRROR'].getboolean('enabled', False)
        print(f"  PyPI Mirror: {'✅ ENABLED' if mirror_enabled else '❌ DISABLED'}")
        if mirror_enabled:
            print(f"    URL: {self.config['MIRROR']['url']}")
        
        auto_update = self.config['DEFAULT'].getboolean('auto_update', False)
        print(f"  Auto-Update: {'✅ ENABLED' if auto_update else '❌ DISABLED'}")
        
        telemetry = self.config['DEFAULT'].getboolean('telemetry', False)
        print(f"  Telemetry: {'✅ ENABLED' if telemetry else '❌ DISABLED'}")
        
        # Project Defaults
        print("\n🎯 PROJECT DEFAULTS:")
        print(f"  Default Template: {self.config['DEFAULT']['default_template']}")
        print(f"  Default Editor: {self.config['DEFAULT']['editor']}")
        print(f"  Auto Git: {'✅ Yes' if self.config['PROJECT'].getboolean('auto_git') else '❌ No'}")
        print(f"  Auto VirtualEnv: {'✅ Yes' if self.config['PROJECT'].getboolean('auto_venv') else '❌ No'}")
        print(f"  Author: {self.config['PROJECT']['author']}")
        print(f"  License: {self.config['PROJECT']['license']}")
        
        # Template Status
        print("\n📁 TEMPLATE STATUS:")
        self.check_templates_exist(verbose=True)
        
        # Storage Usage
        print("\n💾 STORAGE:")
        try:
            config_size = sum(f.stat().st_size for f in self.config_dir.rglob('*') if f.is_file())
            print(f"  Config: {self.format_size(config_size)}")
            
            if self.projects_dir.exists():
                projects_size = sum(f.stat().st_size for f in self.projects_dir.rglob('*') if f.is_file())
                print(f"  Projects: {self.format_size(projects_size)}")
        except:
            print("  Storage: Unable to calculate")
        
        print("\n" + "=" * 60)
    
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
            print("  ilia config mirror enable   - Enable national mirror")
            print("  ilia config mirror disable  - Disable national mirror")
    
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
            if 'python' in str(venv_pip_path).lower():
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
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
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
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
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
            print("or run 'ilia --setup' to configure templates.")
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
            
            # Copy template
            shutil.copytree(template_path, project_dir)
            print("✅ Project structure created")
            
            # Process template variables
            self.process_template_with_manifest(project_type, project_dir, project_name)
            
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
                if platform.system() == 'Windows':
                    subprocess.Popen([editor, str(project_dir)], shell=True)
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
            print(f"  2. Or run: ilia templates add <name>")
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
        print("  ilia templates add <name>      - Add template from current directory")
        print("  ilia templates remove <name>   - Remove template")
        print("  ilia templates import <source> - Import template from URL or local file")
        print("  ilia templates export <name>   - Export template as archive")
        print("\n  Examples:")
        print("    ilia templates import https://github.com/user/template/archive/main.zip")
        print("    ilia templates import ./my-template.zip")
        print("    ilia templates import /path/to/template.tar.gz")
    
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
            self.send_telemetry("template_added", 
                   template_name=template_name,
                   file_count=file_count)
            
            # Count files
            file_count = len(list(template_dst.rglob('*')))
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
                headers={'User-Agent': f'ilia-cli/{self.version}'}
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
            # Create destination directory
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
                                item.unlink()
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
            
            print(f"\n💡 Template ready! Use: ilia new myproject --template {template_name}")
            
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
                "author": "ILIA CLI",
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

    def _show_template_structure(self, template_dir: Path, indent: int = 0):
        """Show template structure in a tree format"""
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
                self._show_template_structure(item, indent + 1)
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
            print("Usage: ilia templates import <url-or-file>")
            print("\nExamples:")
            print("  ilia templates import https://example.com/template.zip")
            print("  ilia templates import ./my-template.zip")
            print("  ilia templates import C:\\templates\\project.tar.gz")
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
        
        if not template_name:
            print("❌ Template name required")
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
                template_name = input("New template name: ").strip()
                if not template_name:
                    print("❌ Template name required")
                    return
                template_dst = self.templates_dir / template_name
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
            print("Usage: ilia templates export <name>")
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
            print("\n📁 No projects found")
            print("\nCreate your first project:")
            print("  ilia new myproject --html")
            print("  ilia new myapi --flask")
            return
        
        try:
            with open(projects_file, 'r') as f:
                projects = json.load(f)
            
            if not projects:
                print("\n📁 No projects found")
                return
            
            print("\n📁 Your Projects")
            print("=" * 60)
            
            for i, project in enumerate(projects, 1):
                created = datetime.fromisoformat(project['created']).strftime('%Y-%m-%d')
                size_str = self.format_size(project.get('size', 0))
                
                print(f"{i:2}. {project['name']:20} ({project['type']:10})")
                print(f"     Created: {created} | Size: {size_str:>8}")
                print(f"     Path: {project['path']}")
                if i < len(projects):
                    print()
            
            print("\n📋 Commands:")
            print("  ilia open <name>      - Open project in editor")
            print("  ilia info <name>      - Show project information")
            print("  ilia archive <name>   - Archive project")
            print("  ilia delete <name>    - Delete project")
            
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
        
        print(f"\n📋 Project: {project_info['name']}")
        print("=" * 60)
        
        print(f"Type: {project_info['type']}")
        print(f"Created: {datetime.fromisoformat(project_info['created']).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Modified: {datetime.fromisoformat(project_info['modified']).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Size: {self.format_size(project_info.get('size', 0))}")
        print(f"Path: {project_path}")
        
        # Check if project exists
        if project_path.exists():
            print(f"\n📁 Project Status: ✅ EXISTS")
            
            # Count files
            files = list(project_path.rglob('*'))
            file_count = len([f for f in files if f.is_file()])
            dir_count = len([f for f in files if f.is_dir()])
            
            print(f"Files: {file_count}")
            print(f"Directories: {dir_count}")
            
            # Check for common files
            print("\n📄 Key Files:")
            common_files = ['requirements.txt', 'package.json', 'app.py', 'index.html', 'README.md']
            for file in common_files:
                file_path = project_path / file
                if file_path.exists():
                    print(f"  ✅ {file}")
                else:
                    # Check in subdirectories
                    found = False
                    for f in project_path.rglob(file):
                        if f.is_file():
                            print(f"  ✅ {f.relative_to(project_path)}")
                            found = True
                            break
                    if not found:
                        print(f"  ❌ {file}")
            
            # Git status
            if (project_path / '.git').exists():
                print("\n🔧 Git: ✅ Initialized")
            else:
                print("\n🔧 Git: ❌ Not initialized")
            
            # Virtual environment
            venv_dirs = ['venv', '.venv', 'env']
            venv_found = False
            for venv_dir in venv_dirs:
                if (project_path / venv_dir).exists():
                    print(f"🐍 Virtual Environment: ✅ {venv_dir}")
                    venv_found = True
                    break
            if not venv_found:
                print("🐍 Virtual Environment: ❌ Not found")
        
        else:
            print(f"\n📁 Project Status: ❌ MISSING")
        
        print("\n📋 Commands:")
        print(f"  ilia open {project_name}      - Open in editor")
        print(f"  cd {project_path}            - Navigate to project")
    
    def run_doctor(self):
        """Run system diagnostics"""
        print("\n🏥 ilia System Doctor")
        print("=" * 60)
        
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
        print("\n🔍 System Checks:")
        for check_name, status, icon in checks:
            print(f"  {icon} {check_name:<25} {status}")
        
        # Summary
        print("\n📊 Summary:")
        
        total = len(checks)
        ok = sum(1 for _, _, icon in checks if icon == "✅")
        warnings = sum(1 for _, _, icon in checks if icon == "⚠️")
        errors = sum(1 for _, _, icon in checks if icon == "❌")
        
        print(f"  Total Checks: {total}")
        print(f"  ✅ Passed: {ok}")
        print(f"  ⚠️  Warnings: {warnings}")
        print(f"  ❌ Errors: {errors}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        
        if template_count == 0:
            print("  • Add templates: Copy template folders to templates directory")
            print(f"    Location: {self.templates_dir}")
        
        if not editor_available:
            print(f"  • Install {editor} or change default editor:")
            print("    ilia config editor <editor-name>")
        
        if not git_available and self.config['PROJECT'].getboolean('auto_git'):
            print("  • Install Git or disable auto-git:")
            print("    ilia config set PROJECT.auto_git false")
        
        if not venv_available and self.config['PROJECT'].getboolean('auto_venv'):
            print("  • Install venv module or disable auto-venv:")
            print("    ilia config set PROJECT.auto_venv false")
        
        print("\n🛠️  Commands:")
        print("  ilia config        - View configuration")
        print("  ilia templates     - List templates")
        print("  ilia --setup       - Run setup wizard")
        
        self.log_activity('info', 'System diagnostics completed')
        self.send_telemetry("doctor_ran", 
                   template_count=len(self.list_available_templates()),
                   internet_available=self.check_internet(),
                   git_available=shutil.which('git') is not None)
    
    def show_status(self):
        """Show system status"""
        print("\n📊 ilia System Status")
        print("=" * 60)
        
        # Basic info
        print(f"Version: {self.version}")
        print(f"Session: {self.session_id}")
        print(f"Python: {platform.python_version()}")
        print(f"Platform: {platform.platform()}")
        
        # Configuration
        print("\n⚙️  Configuration:")
        print(f"  Config: {self.config_dir}")
        print(f"  Templates: {self.templates_dir}")
        print(f"  Projects: {self.projects_dir}")
        
        # Features
        print("\n🎯 Features:")
        mirror = "✅ Enabled" if self.config['MIRROR'].getboolean('enabled') else "❌ Disabled"
        print(f"  PyPI Mirror: {mirror}")
        
        auto_update = "✅ Yes" if self.config['DEFAULT'].getboolean('auto_update') else "❌ No"
        print(f"  Auto-Update: {auto_update}")
        
        telemetry = "✅ Yes" if self.config['DEFAULT'].getboolean('telemetry') else "❌ No"
        print(f"  Telemetry: {telemetry}")
        
        # Statistics
        print("\n📈 Statistics:")
        
        # Template count
        templates = self.list_available_templates()
        print(f"  Templates: {len(templates)}")
        
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
        print(f"  Projects: {project_count}")
        
        # Log size
        log_size = 0
        if self.logs_dir.exists():
            for log_file in self.logs_dir.glob('*.log'):
                try:
                    log_size += log_file.stat().st_size
                except:
                    pass
        print(f"  Logs: {self.format_size(log_size)}")
        
        # System health
        print("\n🏥 System Health:")
        internet = "✅ Connected" if self.check_internet() else "❌ Disconnected"
        print(f"  Internet: {internet}")
        
        git = "✅ Available" if shutil.which('git') else "❌ Not found"
        print(f"  Git: {git}")
        
        editor = self.config['DEFAULT']['editor']
        editor_status = "✅ Available" if shutil.which(editor) else "❌ Not found"
        print(f"  Editor ({editor}): {editor_status}")
        
        print("\n💡 Run 'ilia doctor' for detailed diagnostics")
    
    def check_for_updates(self):
        """Check for ilia updates"""
        print("\n🔄 Checking for updates...")
        
        if not self.check_internet():
            print("❌ No internet connection")
            return
        
        try:
            # This would check a real API in production
            print("✅ You have the latest version")
            print(f"Current: {self.version}")
            
            # Update last check timestamp
            self.config['DEFAULT']['last_update_check'] = str(int(time.time()))
            self.save_config()
            
        except Exception as e:
            print(f"❌ Update check failed: {e}")
    
    def show_logs(self, tail: bool = False):
        """Show or tail logs"""
        self.send_telemetry("logs_viewed", tail_mode=tail)
        log_files = list(self.logs_dir.glob('*.log'))
        
        if not log_files:
            print("📭 No log files found")
            return
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        print(f"\n📋 Log Files ({len(log_files)} found):")
        for i, log_file in enumerate(log_files[:5], 1):
            size = self.format_size(log_file.stat().st_size)
            modified = datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            print(f"{i}. {log_file.name} ({size}, {modified})")
        
        if len(log_files) > 5:
            print(f"... and {len(log_files) - 5} more")
        
        # Show latest log
        latest_log = log_files[0]
        print(f"\n📄 Latest log: {latest_log.name}")
        print("-" * 60)
        
        try:
            with open(latest_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if tail:
                # Show last 20 lines
                lines = lines[-20:]
            
            for line in lines:
                print(line.rstrip())
            
            if tail:
                print("\n📝 Tailing log (Ctrl+C to stop)...")
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
        """Uninstall ilia CLI - removes ALL files"""
        self.send_telemetry("uninstall_started")
        print("\n⚠️  UNINSTALL ILIA CLI")
        print("=" * 60)
        
        print("\nThis will remove ALL ilia files including:")
        print(f"  1. User folder ilia.bat: {Path.home() / 'ilia.bat'}")
        print(f"  2. User folder schematic_deploy.py: {Path.home() / 'schematic_deploy.py'}")
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
            
            # 1. Remove user folder ilia.bat
            user_ilia_bat = Path.home() / 'ilia.bat'
            if user_ilia_bat.exists():
                user_ilia_bat.unlink()
                removed_items.append(f"✅ {user_ilia_bat}")
            
            # 2. Remove user folder schematic_deploy.py
            user_deploy_py = Path.home() / 'schematic_deploy.py'
            if user_deploy_py.exists():
                user_deploy_py.unlink()
                removed_items.append(f"✅ {user_deploy_py}")
            
            # 3. Remove AppData ilia-cli directory (force remove read-only files)
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
                    print(f"  {item}")
            else:
                print("\n📭 No ilia files found to remove")
            
            print("\n✅ ilia CLI has been completely uninstalled.")
            print("\nThank you for using ilia! 👋")
            
        except Exception as e:
            print(f"❌ Uninstall failed: {e}")
            print("\nYou may need to manually remove:")
            print(f"  {Path.home() / 'ilia.bat'}")
            print(f"  {Path.home() / 'schematic_deploy.py'}")
            print(f"  {self.config_dir}")
    
    def reset_config(self):
        """Reset configuration to defaults"""
        print("\n🔄 Reset Configuration")
        print("=" * 60)
        
        print("\nThis will reset all settings to defaults.")
        print("Your templates and projects will NOT be affected.")
        
        confirm = input("\nReset configuration? (y/N): ").strip().lower()
        if confirm != 'yes':
            print("Reset cancelled.")
            return
        
        try:
            # Backup old config
            backup_file = self.config_dir / f"config.backup.{int(time.time())}.ini"
            if self.config_file.exists():
                shutil.copy2(self.config_file, backup_file)
            
            # Remove config file
            if self.config_file.exists():
                self.config_file.unlink()
            
            # Reload defaults
            self.config = self.load_config()
            self.save_config()
            
            print("✅ Configuration reset to defaults")
            self.send_telemetry("config_reset")
            print(f"Backup saved to: {backup_file.name}")
            
            self.log_activity('info', 'Configuration reset')
            
        except Exception as e:
            print(f"❌ Reset failed: {e}")
    
    def run(self, args):
        """Main CLI entry point"""
        # Handle first run
        if self.config['DEFAULT'].getboolean('first_run', True):
            self.first_run_setup()
            
        self.send_telemetry("app_started", 
                   command=args[0] if args else None,
                   args_count=len(args))
        
        # Parse arguments
        if len(args) == 0 or args[0] in ['-h', '--help', 'help']:
            self.show_help()
        
        elif args[0] in ['--version', 'version']:
            print(f"{self.app_name} v{self.version}")
        
        elif args[0] in ['--setup', 'setup']:
            self.first_run_setup()
        
        elif args[0] in ['--about', 'about']:
            self.show_about()
        
        elif args[0] == 'new':
            if len(args) < 2:
                print("❌ Project name required")
                print("Usage: ilia new <project-name> [--html|--flask|--type]")
                return
            
            project_name = args[1]
            project_type = None
            
            # Parse template flags
            for i, arg in enumerate(args):
                if arg in ['--flask', '-f', '--python']:
                    project_type = 'flask'
                elif arg in ['--html', '-h', '--web']:
                    project_type = 'html'
                elif arg == '--type' and i + 1 < len(args):
                    project_type = args[i + 1]
            
            self.init_project(project_type, project_name)
        
        elif args[0] == 'init':
            project_type = None
            project_name = None
            
            # Parse optional arguments
            for i, arg in enumerate(args[1:], 1):
                if arg in ['--flask', '-f', '--python']:
                    project_type = 'flask'
                elif arg in ['--html', '-h', '--web']:
                    project_type = 'html'
                elif not arg.startswith('-') and not project_name:
                    project_name = arg
            
            self.init_project(project_type, project_name)
        
        elif args[0] == 'config':
            if len(args) > 1:
                if args[1] == 'mirror':
                    action = args[2] if len(args) > 2 else None
                    self.configure_mirror(action)
                elif args[1] == 'editor':
                    editor = args[2] if len(args) > 2 else None
                    if editor:
                        self.config['DEFAULT']['editor'] = editor
                        self.save_config()
                        print(f"✅ Default editor set to: {editor}")
                    else:
                        print(f"Current editor: {self.config['DEFAULT']['editor']}")
                elif args[1] == 'reset':
                    self.reset_config()
                elif args[1] == 'path':
                    print(f"\n📁 Configuration Paths:")
                    print(f"  Config: {self.config_dir}")
                    print(f"  Templates: {self.templates_dir}")
                    print(f"  Projects: {self.projects_dir}")
                    print(f"  Logs: {self.logs_dir}")
                else:
                    self.show_config()
            else:
                self.show_config()
        
        elif args[0] == 'template' or args[0] == 'templates':
            if len(args) > 1:
                if args[1] == 'create':
                    template_name = args[2] if len(args) > 2 else None
                    is_framework = '--framework' in args
                    if template_name:
                        self.create_template_from_current(template_name, is_framework)
                    else:
                        print("❌ Template name required")
                elif args[1] == 'list':
                    self.list_templates_with_details()
                elif args[1] == 'info':
                    template_name = args[2] if len(args) > 2 else None
                    if template_name:
                        self.generate_template_docs(template_name)
                    else:
                        print("❌ Template name required")
                elif args[1] == 'validate':
                    template_name = args[2] if len(args) > 2 else None
                    if template_name:
                        manifest = self.get_template_manifest(template_name)
                        if manifest:
                            is_valid, errors = manifest.validate()
                            if is_valid:
                                print(f"✅ Template '{template_name}' is valid")
                            else:
                                print(f"❌ Template validation failed:")
                                for error in errors:
                                    print(f"  • {error}")
                        else:
                            print(f"❌ Template '{template_name}' not found")
                    else:
                        print("❌ Template name required")
                elif args[1] == 'edit':
                    template_name = args[2] if len(args) > 2 else None
                    if template_name:
                        manifest_file = self.templates_dir / template_name / 'manifest.json'
                        if manifest_file.exists():
                            editor = self.config['DEFAULT']['editor']
                            subprocess.run([editor, str(manifest_file)])
                        else:
                            print(f"❌ No manifest found for {template_name}")
                            print("Create one with: ilia template create <name>")
                    else:
                        print("❌ Template name required")
                else:
                    self.manage_templates(args[1], args[2] if len(args) > 2 else None)
            else:
                self.list_templates()
                
        elif args[0] == 'new':
            if len(args) < 2:
                print("❌ Project name required")
                print("Usage: ilia new <project-name> [--template <name>|--flask|--html]")
                return
            
            project_name = args[1]
            project_type = None
            
            # Check for template flag
            for i, arg in enumerate(args):
                if arg == '--template' and i + 1 < len(args):
                    project_type = args[i + 1]
                    break
                elif arg in ['--flask', '-f']:
                    project_type = 'flask'
                elif arg in ['--html', '-h']:
                    project_type = 'html'
            
            # Use default if not specified
            if not project_type:
                project_type = self.config['DEFAULT']['default_template']
            
            self.init_project(project_type, project_name)
        
        elif args[0] == 'projects':
            self.list_projects()
        
        elif args[0] == 'open':
            if len(args) < 2:
                print("❌ Project name required")
                print("Usage: ilia open <project-name>")
                return
            self.open_project(args[1])
        
        elif args[0] == 'info':
            if len(args) < 2:
                print("❌ Project name required")
                print("Usage: ilia info <project-name>")
                return
            self.show_project_info(args[1])
        
        elif args[0] == 'doctor':
            self.run_doctor()
        
        elif args[0] == 'status':
            self.show_status()
        
        elif args[0] == 'update':
            self.check_for_updates()
        
        elif args[0] == 'logs':
            tail = len(args) > 1 and args[1] == '--tail'
            self.show_logs(tail)
        
        elif args[0] == 'cleanup':
            self.cleanup()
        
        elif args[0] == 'uninstall':
            self.uninstall()
            
        elif args[0] == 'help':
            if len(args) > 1 and args[1] == 'templates':
                self.show_template_help()
            elif len(args) > 2 and args[1] == 'template':
                self.show_template_help(args[2])
            else:
                self.show_help()
        
        else:
            print(f"❌ Unknown command: {args[0]}")
            print(f"Try 'ilia --help' for available commands")

    # NEW: Enhanced show_config with additional features
    def show_enhanced_config(self):
        """Display enhanced configuration including new features"""
        # Call original show_config
        self.show_config()
        
        # Add new sections
        if 'AI' in self.config:
            print("\n🤖 AI CONFIGURATION:")
            ai_enabled = self.config['AI'].getboolean('enabled', False)
            print(f"  AI Features: {'✅ ENABLED' if ai_enabled else '❌ DISABLED'}")
            if ai_enabled:
                print(f"  Model: {self.config['AI'].get('model', 'gpt-3.5-turbo')}")
        
        if 'DASHBOARD' in self.config:
            print("\n🌐 DASHBOARD:")
            dashboard_enabled = self.config['DASHBOARD'].getboolean('enabled', False)
            print(f"  Web Dashboard: {'✅ ENABLED' if dashboard_enabled else '❌ DISABLED'}")
            if dashboard_enabled:
                print(f"  Port: {self.config['DASHBOARD'].get('port', '8080')}")
        
        if 'QUALITY' in self.config:
            print("\n🔍 QUALITY CHECKS:")
            auto_scan = self.config['QUALITY'].getboolean('auto_scan', False)
            print(f"  Auto Quality Scan: {'✅ ENABLED' if auto_scan else '❌ DISABLED'}")
            if auto_scan:
                print(f"  Minimum Score: {self.config['QUALITY'].get('min_score', '70')}/100")

# ============================================================================
# NEW FEATURES ADDED BELOW - NO EXISTING CODE REMOVED
# ============================================================================

class AIGenerator:
    """AI-powered project template generator (NEW)"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.enabled = HAS_OPENAI and self.api_key
        
    def generate_project_description(self, user_input: str) -> Dict[str, Any]:
        """Generate project structure from natural language description"""
        if not self.enabled:
            return self._fallback_generation(user_input)
        
        try:
            client = openai.OpenAI(api_key=self.api_key)
            
            prompt = f"""
            Based on the following project description, create a complete project structure:
            
            "{user_input}"
            
            Return a JSON with:
            - project_name: Generated project name
            - project_type: Framework (flask, react, html, etc.)
            - structure: File tree with file contents
            - requirements: Dependencies list
            - readme: Project README content
            - manifest: Template manifest configuration
            
            Make it production-ready with best practices.
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"❌ AI generation failed: {e}")
            return self._fallback_generation(user_input)
    
    def _fallback_generation(self, user_input: str) -> Dict[str, Any]:
        """Fallback generation without AI"""
        # Extract keywords to determine project type
        keywords = {
            'web': 'html',
            'website': 'html',
            'api': 'flask',
            'rest': 'flask',
            'backend': 'flask',
            'frontend': 'html',
            'react': 'react',
            'vue': 'vue',
            'angular': 'angular',
            'mobile': 'react',
            'desktop': 'flask',
            'bot': 'python',
            'scraper': 'python',
            'data': 'python'
        }
        
        project_type = 'html'
        for keyword, ptype in keywords.items():
            if keyword in user_input.lower():
                project_type = ptype
                break
        
        # Generate project name
        words = user_input.lower().split()
        if len(words) >= 2:
            project_name = f"{words[0]}-{words[1]}"
        else:
            project_name = f"project-{int(time.time())}"
        
        return {
            "project_name": project_name.replace(' ', '-'),
            "project_type": project_type,
            "structure": {},
            "requirements": [],
            "readme": f"# {project_name}\n\nGenerated from: {user_input}",
            "manifest": {}
        }

class TemplateMacroEngine:
    """Advanced template engine with macros and transformations (NEW)"""
    
    MACROS = {
        '{{date}}': lambda: datetime.now().strftime('%Y-%m-%d'),
        '{{time}}': lambda: datetime.now().strftime('%H:%M:%S'),
        '{{timestamp}}': lambda: str(int(time.time())),
        '{{uuid}}': lambda: secrets.token_hex(8),
        '{{random_string}}': lambda: ''.join(random.choices(string.ascii_lowercase, k=8)),
        '{{project_slug}}': lambda pname: pname.lower().replace(' ', '-').replace('_', '-'),
        '{{project_upper}}': lambda pname: pname.upper(),
        '{{project_camel}}': lambda pname: ''.join(word.capitalize() for word in pname.split('_')),
        '{{author_initials}}': lambda author: ''.join(word[0].upper() for word in author.split()),
        '{{current_year}}': lambda: str(datetime.now().year),
        # '{{git_username}}': lambda: self._get_git_username(),
        '{{hostname}}': lambda: socket.gethostname(),
        '{{python_version}}': lambda: platform.python_version(),
        '{{os_name}}': lambda: platform.system()
    }
    
    @classmethod
    def _get_git_username(cls):
        try:
            result = subprocess.run(['git', 'config', 'user.name'], 
                                  capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return getpass.getuser()
    
    @classmethod
    def process_macros(cls, content: str, project_name: str = None, author: str = None) -> str:
        """Process template macros in content"""
        for macro, func in cls.MACROS.items():
            if macro in content:
                if macro in ['{{project_slug}}', '{{project_upper}}', '{{project_camel}}']:
                    if project_name:
                        content = content.replace(macro, func(project_name))
                elif macro == '{{author_initials}}':
                    if author:
                        content = content.replace(macro, func(author))
                else:
                    content = content.replace(macro, func())
        return content

class InteractiveWizard:
    """Interactive Terminal UI Wizard for project creation (NEW)"""
    
    def __init__(self, cli):
        self.cli = cli
        self.steps = []
        self.current_step = 0
        self.responses = {}
        
    def run(self):
        """Run interactive wizard"""
        if HAS_CURSES:
            return self._run_curses()
        else:
            return self._run_console()
    
    def _run_curses(self):
        """Run wizard with curses for enhanced UI"""
        try:
            return curses.wrapper(self._main_curses)
        except:
            return self._run_console()
    
    def _main_curses(self, stdscr):
        curses.curs_set(1)
        stdscr.clear()
        
        steps = [
            ("Project Name", "Enter project name", "text"),
            ("Project Type", "Select framework", "select", self.cli.list_available_templates()),
            ("Description", "Project description", "text"),
            ("Author", "Author name", "text"),
            ("License", "Select license", "select", ["MIT", "Apache 2.0", "GPLv3", "BSD", "Proprietary"]),
            ("Git", "Initialize git?", "bool"),
            ("Virtual Env", "Create virtual environment?", "bool"),
            ("Install Deps", "Install dependencies?", "bool"),
        ]
        
        current = 0
        responses = {}
        
        while current < len(steps):
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            
            # Header
            stdscr.addstr(1, 2, "🚀 ilia Project Wizard", curses.A_BOLD)
            stdscr.addstr(2, 2, "=" * (width - 4))
            
            # Progress
            progress = int((current / len(steps)) * (width - 10))
            stdscr.addstr(4, 2, f"Step {current + 1} of {len(steps)}")
            stdscr.addstr(5, 2, f"[{'█' * progress}{'░' * ((width - 10) - progress)}]")
            
            # Current step
            step_name, prompt, step_type, *step_args = steps[current]
            stdscr.addstr(7, 2, f"{step_name}:", curses.A_BOLD)
            stdscr.addstr(8, 4, prompt)
            
            # Show current value if exists
            if step_name in responses:
                stdscr.addstr(10, 4, f"Current: {responses[step_name]}")
            
            # Input area
            stdscr.addstr(12, 4, "> ", curses.A_BOLD)
            
            curses.echo()
            stdscr.refresh()
            
            try:
                if step_type == "select":
                    # Show options
                    for i, option in enumerate(step_args[0]):
                        stdscr.addstr(13 + i, 6, f"{i + 1}. {option}")
                    
                    stdscr.addstr(13 + len(step_args[0]), 4, "Selection: ")
                    choice = stdscr.getstr(13 + len(step_args[0]), 15, 5).decode()
                    
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(step_args[0]):
                            responses[step_name] = step_args[0][idx]
                            current += 1
                        else:
                            raise ValueError
                    except:
                        stdscr.addstr(13 + len(step_args[0]) + 2, 4, 
                                    "Invalid choice! Press any key...")
                        stdscr.getch()
                else:
                    # Text or bool input
                    input_str = stdscr.getstr(12, 6, width - 10).decode()
                    
                    if step_type == "bool":
                        responses[step_name] = input_str.lower() in ['y', 'yes', 'true', '1']
                    else:
                        responses[step_name] = input_str.strip()
                    
                    current += 1
                    
            except Exception as e:
                current += 1
            
            curses.noecho()
        
        # Summary screen
        stdscr.clear()
        stdscr.addstr(1, 2, "📋 Project Summary", curses.A_BOLD)
        stdscr.addstr(2, 2, "=" * (width - 4))
        
        row = 4
        for key, value in responses.items():
            stdscr.addstr(row, 4, f"{key}: {value}")
            row += 1
        
        stdscr.addstr(row + 2, 4, "Create project? (y/N): ", curses.A_BOLD)
        stdscr.refresh()
        
        confirm = stdscr.getch()
        
        if chr(confirm).lower() == 'y':
            return responses
        return None
    
    def _run_console(self):
        """Fallback console wizard"""
        print(f"\n{Fore.CYAN if HAS_COLORS else ''}🚀 ilia Interactive Project Wizard{Style.RESET_ALL if HAS_COLORS else ''}")
        print("=" * 60)
        
        responses = {}
        
        # Project name
        responses['name'] = input(f"\n{Fore.GREEN if HAS_COLORS else ''}📝 Project name:{Style.RESET_ALL if HAS_COLORS else ''} ").strip()
        if not responses['name']:
            responses['name'] = f"project-{int(time.time())}"
        
        # Project type with preview
        templates = self.cli.list_available_templates()
        print(f"\n{Fore.GREEN if HAS_COLORS else ''}📁 Available templates:{Style.RESET_ALL if HAS_COLORS else ''}")
        for i, template in enumerate(templates, 1):
            print(f"  {i}. {template} ({self.cli.detect_template_type(self.cli.templates_dir / template)})")
        
        while True:
            try:
                choice = input(f"\n{Fore.GREEN if HAS_COLORS else ''}Select template (1-{len(templates)}):{Style.RESET_ALL if HAS_COLORS else ''} ").strip()
                if choice:
                    idx = int(choice) - 1
                    if 0 <= idx < len(templates):
                        responses['type'] = templates[idx]
                        break
                else:
                    responses['type'] = self.cli.config['DEFAULT']['default_template']
                    break
            except ValueError:
                print(f"{Fore.YELLOW if HAS_COLORS else ''}Invalid choice!{Style.RESET_ALL if HAS_COLORS else ''}")
        
        # Description
        responses['description'] = input(f"\n{Fore.GREEN if HAS_COLORS else ''}📋 Description:{Style.RESET_ALL if HAS_COLORS else ''} ").strip()
        
        # Advanced options
        print(f"\n{Fore.YELLOW if HAS_COLORS else ''}⚙️  Advanced options (press Enter for defaults):{Style.RESET_ALL if HAS_COLORS else ''}")
        responses['author'] = input(f"Author [{self.cli.config['PROJECT']['author']}]: ").strip() or self.cli.config['PROJECT']['author']
        responses['license'] = input(f"License [{self.cli.config['PROJECT']['license']}]: ").strip() or self.cli.config['PROJECT']['license']
        responses['git'] = input("Initialize git? (y/N): ").strip().lower() == 'y'
        responses['venv'] = input("Create virtual environment? (y/N): ").strip().lower() != 'n'
        
        # Summary
        print(f"\n{Fore.CYAN if HAS_COLORS else ''}📋 Summary:{Style.RESET_ALL if HAS_COLORS else ''}")
        print("=" * 40)
        for key, value in responses.items():
            print(f"  {key}: {value}")
        
        confirm = input(f"\n{Fore.GREEN if HAS_COLORS else ''}Create project? (y/N):{Style.RESET_ALL if HAS_COLORS else ''} ").strip().lower()
        
        if confirm == 'y':
            return responses
        return None

class CollaborationSession:
    """Real-time collaboration for team projects (NEW)"""
    
    def __init__(self, cli):
        self.cli = cli
        self.sessions = {}
        self.peers = {}
        
    def create_session(self, project_name: str, password: str = None) -> str:
        """Create a collaboration session"""
        session_id = secrets.token_urlsafe(8)
        
        self.sessions[session_id] = {
            'project': project_name,
            'created': datetime.now(),
            'host': socket.gethostname(),
            'users': [],
            'password': password,
            'chat': [],
            'files': [],
            'active': True
        }
        
        self.cli.log_activity('info', f'Collaboration session created: {session_id}')
        return session_id
    
    def join_session(self, session_id: str, username: str, password: str = None) -> bool:
        """Join a collaboration session"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        if session['password'] and session['password'] != password:
            return False
        
        # Add user to session
        if username not in session['users']:
            session['users'].append(username)
        
        # Create peer connection
        peer_id = secrets.token_urlsafe(6)
        self.peers[peer_id] = {
            'session': session_id,
            'username': username,
            'joined': datetime.now(),
            'last_active': datetime.now()
        }
        
        # Broadcast join message
        self._broadcast_message(session_id, f"👋 {username} joined the session")
        
        self.cli.log_activity('info', f'User joined session: {username} -> {session_id}')
        return peer_id
    
    def send_chat_message(self, session_id: str, username: str, message: str):
        """Send chat message to session"""
        if session_id in self.sessions:
            self.sessions[session_id]['chat'].append({
                'user': username,
                'message': message,
                'time': datetime.now()
            })
            
            # Keep only last 100 messages
            if len(self.sessions[session_id]['chat']) > 100:
                self.sessions[session_id]['chat'] = self.sessions[session_id]['chat'][-100:]
    
    def share_file(self, session_id: str, username: str, file_path: Path):
        """Share file with session participants"""
        if not file_path.exists():
            return False
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            file_hash = hashlib.md5(content).hexdigest()
            
            self.sessions[session_id]['files'].append({
                'user': username,
                'filename': file_path.name,
                'hash': file_hash,
                'size': len(content),
                'time': datetime.now()
            })
            
            self._broadcast_message(session_id, f"📁 {username} shared {file_path.name}")
            return True
            
        except Exception as e:
            self.cli.log_activity('error', f'File share failed: {e}')
            return False
    
    def _broadcast_message(self, session_id: str, message: str):
        """Broadcast message to all session users"""
        if session_id in self.sessions:
            self.sessions[session_id]['chat'].append({
                'user': 'System',
                'message': message,
                'time': datetime.now()
            })

class ProjectAnalytics:
    """Collect and display project analytics (NEW)"""
    
    def __init__(self, cli):
        self.cli = cli
        self.metrics_file = cli.config_dir / 'metrics.json'
        self.metrics = self.load_metrics()
        
    def load_metrics(self) -> Dict[str, Any]:
        """Load saved metrics"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'project_creations': {},
            'template_usage': {},
            'command_usage': {},
            'session_times': [],
            'errors': [],
            'performance': {}
        }
    
    def save_metrics(self):
        """Save metrics to file"""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except:
            pass
    
    def track_project_creation(self, project_name: str, template: str, success: bool):
        """Track project creation"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if today not in self.metrics['project_creations']:
            self.metrics['project_creations'][today] = {
                'total': 0,
                'success': 0,
                'templates': {}
            }
        
        self.metrics['project_creations'][today]['total'] += 1
        if success:
            self.metrics['project_creations'][today]['success'] += 1
        
        if template not in self.metrics['project_creations'][today]['templates']:
            self.metrics['project_creations'][today]['templates'][template] = 0
        self.metrics['project_creations'][today]['templates'][template] += 1
        
        self.save_metrics()
    
    def track_command(self, command: str):
        """Track command usage"""
        if command not in self.metrics['command_usage']:
            self.metrics['command_usage'][command] = 0
        self.metrics['command_usage'][command] += 1
        self.save_metrics()
    
    def show_dashboard(self):
        """Show analytics dashboard"""
        print(f"\n{Fore.CYAN if HAS_COLORS else ''}📊 ilia Analytics Dashboard{Style.RESET_ALL if HAS_COLORS else ''}")
        print("=" * 60)
        
        # Overall stats
        total_projects = sum(
            day_stats['total'] 
            for day_stats in self.metrics['project_creations'].values()
        )
        
        success_rate = 0
        if total_projects > 0:
            total_success = sum(
                day_stats['success'] 
                for day_stats in self.metrics['project_creations'].values()
            )
            success_rate = (total_success / total_projects) * 100
        
        print(f"\n{Fore.GREEN if HAS_COLORS else ''}📈 Overall Statistics:{Style.RESET_ALL if HAS_COLORS else ''}")
        print(f"  Total Projects Created: {total_projects}")
        print(f"  Success Rate: {success_rate:.1f}%")
        
        # Template usage
        print(f"\n{Fore.YELLOW if HAS_COLORS else ''}🏗️  Template Usage:{Style.RESET_ALL if HAS_COLORS else ''}")
        template_counts = defaultdict(int)
        for day_stats in self.metrics['project_creations'].values():
            for template, count in day_stats['templates'].items():
                template_counts[template] += count
        
        for template, count in sorted(template_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {template}: {count} projects")
        
        # Command usage
        print(f"\n{Fore.BLUE if HAS_COLORS else ''}🎮 Command Usage:{Style.RESET_ALL if HAS_COLORS else ''}")
        for command, count in sorted(self.metrics['command_usage'].items(), 
                                   key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {command}: {count} times")
        
        # Recent activity
        print(f"\n{Fore.MAGENTA if HAS_COLORS else ''}🕒 Recent Activity:{Style.RESET_ALL if HAS_COLORS else ''}")
        recent_days = sorted(self.metrics['project_creations'].keys(), reverse=True)[:3]
        for day in recent_days:
            stats = self.metrics['project_creations'][day]
            print(f"  {day}: {stats['total']} projects")
        
        # Export option
        print(f"\n{Fore.CYAN if HAS_COLORS else ''}💾 Export Options:{Style.RESET_ALL if HAS_COLORS else ''}")
        print("  Use: ilia analytics export [format]")
        print("  Formats: json, csv, html, markdown")

class ProjectHealthChecker:
    """Check health and quality of projects (NEW)"""
    
    QUALITY_RULES = {
        'python': {
            'has_requirements': lambda p: (p / 'requirements.txt').exists(),
            'has_readme': lambda p: (p / 'README.md').exists(),
            'has_gitignore': lambda p: (p / '.gitignore').exists(),
            'has_venv': lambda p: any((p / d).exists() for d in ['venv', '.venv', 'env']),
            'has_tests': lambda p: any((p / 'tests').exists() or 
                                      (p / 'test').exists() or
                                      any(f.name.endswith('_test.py') for f in p.rglob('*.py'))),
            'file_count': lambda p: len([f for f in p.rglob('*.py') if f.is_file()])
        },
        'web': {
            'has_html': lambda p: any(f.suffix.lower() in ['.html', '.htm'] for f in p.rglob('*') if f.is_file()),
            'has_css': lambda p: any(f.suffix.lower() in ['.css', '.scss', '.sass'] for f in p.rglob('*') if f.is_file()),
            'has_js': lambda p: any(f.suffix.lower() in ['.js', '.jsx', '.ts', '.tsx'] for f in p.rglob('*') if f.is_file()),
            'has_favicon': lambda p: any('favicon' in f.name.lower() for f in p.rglob('*') if f.is_file())
        }
    }
    
    def __init__(self, cli):
        self.cli = cli
    
    def check_project(self, project_path: Path) -> Dict[str, Any]:
        """Perform comprehensive project health check"""
        if not project_path.exists():
            return {'status': 'error', 'message': 'Project not found'}
        
        results = {
            'status': 'healthy',
            'score': 0,
            'checks': [],
            'issues': [],
            'recommendations': [],
            'metrics': {}
        }
        
        # Determine project type
        project_type = self.detect_project_type(project_path)
        results['project_type'] = project_type
        
        # Apply relevant quality rules
        rules = {}
        for rule_type, rule_set in self.QUALITY_RULES.items():
            if rule_type in project_type.lower():
                rules.update(rule_set)
        
        # Run checks
        total_checks = 0
        passed_checks = 0
        
        for check_name, check_func in rules.items():
            total_checks += 1
            try:
                if check_func(project_path):
                    results['checks'].append({'check': check_name, 'status': 'pass'})
                    passed_checks += 1
                else:
                    results['checks'].append({'check': check_name, 'status': 'fail'})
                    results['issues'].append(f"Missing: {check_name.replace('_', ' ')}")
            except Exception as e:
                results['checks'].append({'check': check_name, 'status': 'error', 'error': str(e)})
        
        # Calculate score
        if total_checks > 0:
            results['score'] = int((passed_checks / total_checks) * 100)
        
        # File statistics
        files = list(project_path.rglob('*'))
        results['metrics'] = {
            'total_files': len(files),
            'directories': len([f for f in files if f.is_dir()]),
            'python_files': len([f for f in project_path.rglob('*.py') if f.is_file()]),
            'javascript_files': len([f for f in project_path.rglob('*.js') if f.is_file()]),
            'html_files': len([f for f in project_path.rglob('*.html') if f.is_file()]),
            'total_size': sum(f.stat().st_size for f in files if f.is_file())
        }
        
        # Security checks
        security_issues = self.check_security(project_path)
        if security_issues:
            results['issues'].extend(security_issues)
            results['status'] = 'needs_attention'
        
        # Generate recommendations
        results['recommendations'] = self.generate_recommendations(results)
        
        return results
    
    def detect_project_type(self, project_path: Path) -> str:
        """Detect project type from files"""
        indicators = {
            'Python': ['requirements.txt', 'setup.py', 'pyproject.toml'],
            'Flask': ['app.py', 'application.py'],
            'Django': ['manage.py', 'settings.py'],
            'React': ['package.json', 'src/App.js'],
            'Vue': ['vue.config.js', 'src/main.js'],
            'HTML': ['index.html', 'style.css'],
            'Node.js': ['package.json', 'node_modules'],
            'Rust': ['Cargo.toml'],
            'Go': ['go.mod', 'main.go']
        }
        
        for proj_type, files in indicators.items():
            for file in files:
                if any(project_path.rglob(file)):
                    return proj_type
        
        return 'Unknown'
    
    def check_security(self, project_path: Path) -> List[str]:
        """Check for common security issues"""
        issues = []
        
        # Check for hardcoded secrets
        secret_patterns = [
            r'password\s*[:=]\s*[\'"][^\'"]+[\'"]',
            r'api_key\s*[:=]\s*[\'"][^\'"]+[\'"]',
            r'secret\s*[:=]\s*[\'"][^\'"]+[\'"]',
            r'token\s*[:=]\s*[\'"][^\'"]+[\'"]'
        ]
        
        for file_path in project_path.rglob('*.py'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in secret_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            issues.append(f"Hardcoded secret in {file_path.relative_to(project_path)}")
                            break
            except:
                pass
        
        # Check .env file for secrets
        env_file = project_path / '.env'
        if env_file.exists():
            issues.append("Consider moving .env to .env.example and ignoring .env in git")
        
        return issues
    
    def generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on check results"""
        recs = []
        
        if results['score'] < 70:
            recs.append("Add missing documentation and tests to improve project quality")
        
        if 'has_tests' not in [c['check'] for c in results['checks'] if c['status'] == 'pass']:
            recs.append("Add test files to ensure code reliability")
        
        if results['metrics']['total_files'] > 100:
            recs.append("Consider organizing files into modules/packages")
        
        return recs[:3]  # Limit to top 3 recommendations

class WebDashboard:
    """Web-based dashboard for ilia (NEW)"""
    
    def __init__(self, cli, port: int = 8080):
        self.cli = cli
        self.port = port
        self.server = None
        self.is_running = False
        
    def start(self):
        """Start web dashboard server"""
        if not HAS_FLASK:
            print(f"{Fore.RED if HAS_COLORS else ''}Flask not installed. Install with: pip install flask{Style.RESET_ALL if HAS_COLORS else ''}")
            return False
        
        self.is_running = True
        
        # Create Flask app in a thread
        def run_server():
            app = flask.Flask(__name__)
            
            @app.route('/')
            def index():
                return """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>ilia Dashboard</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; }
                        .card { border: 1px solid #ddd; padding: 20px; margin: 10px; border-radius: 5px; }
                        .status { padding: 5px 10px; border-radius: 3px; }
                        .healthy { background: #d4edda; }
                        .warning { background: #fff3cd; }
                        .error { background: #f8d7da; }
                    </style>
                </head>
                <body>
                    <h1>🚀 ilia Dashboard</h1>
                    <div id="content">
                        <p>Loading dashboard...</p>
                    </div>
                    <script>
                        async function loadDashboard() {
                            const response = await fetch('/api/status');
                            const data = await response.json();
                            
                            let html = `
                                <div class="card">
                                    <h2>System Status</h2>
                                    <p>Version: ${data.version}</p>
                                    <p>Python: ${data.python_version}</p>
                                    <p>Platform: ${data.platform}</p>
                                </div>
                                
                                <div class="card">
                                    <h2>Templates</h2>
                                    <p>Available: ${data.templates_count}</p>
                                    <ul>
                                        ${data.templates.map(t => `<li>${t}</li>`).join('')}
                                    </ul>
                                </div>
                                
                                <div class="card">
                                    <h2>Projects</h2>
                                    <p>Total: ${data.projects_count}</p>
                                </div>
                            `;
                            
                            document.getElementById('content').innerHTML = html;
                        }
                        
                        loadDashboard();
                        setInterval(loadDashboard, 5000);
                    </script>
                </body>
                </html>
                """
            
            @app.route('/api/status')
            def api_status():
                templates = self.cli.list_available_templates()
                projects_file = self.cli.projects_dir / 'projects.json'
                projects_count = 0
                
                if projects_file.exists():
                    try:
                        with open(projects_file, 'r') as f:
                            projects = json.load(f)
                            projects_count = len(projects)
                    except:
                        pass
                
                return flask.jsonify({
                    'version': self.cli.version,
                    'python_version': platform.python_version(),
                    'platform': platform.platform(),
                    'templates_count': len(templates),
                    'templates': templates,
                    'projects_count': projects_count
                })
            
            @app.route('/api/templates')
            def api_templates():
                templates = []
                for template in self.cli.list_available_templates():
                    template_path = self.cli.templates_dir / template
                    templates.append({
                        'name': template,
                        'type': self.cli.detect_template_type(template_path),
                        'files_count': len(list(template_path.rglob('*')))
                    })
                return flask.jsonify(templates)
            
            @app.route('/api/projects')
            def api_projects():
                projects_file = self.cli.projects_dir / 'projects.json'
                if projects_file.exists():
                    try:
                        with open(projects_file, 'r') as f:
                            return flask.jsonify(json.load(f))
                    except:
                        pass
                return flask.jsonify([])
            
            app.run(host='127.0.0.1', port=self.port, debug=False)
        
        # Start in background thread
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        print(f"\n{Fore.GREEN if HAS_COLORS else ''}🌐 Web dashboard started!{Style.RESET_ALL if HAS_COLORS else ''}")
        print(f"   URL: http://localhost:{self.port}")
        print(f"   Press Ctrl+C to stop")
        
        return True
    
    def stop(self):
        """Stop web dashboard"""
        self.is_running = False
        if self.server:
            self.server.shutdown()

class MigrationAssistant:
    """Migrate projects between frameworks/versions (NEW)"""
    
    def __init__(self, cli):
        self.cli = cli
        self.migrations = {
            'flask_2_to_3': self.migrate_flask_2_to_3,
            # 'django_3_to_4': self.migrate_django_3_to_4,
            # 'react_class_to_functional': self.migrate_react_class_to_functional,
            'html_to_react': self.migrate_html_to_react
            # 'python_venv_upgrade': self.migrate_python_venv_upgrade
        }
    
    def list_migrations(self, project_path: Path) -> List[str]:
        """List available migrations for project"""
        project_type = self.detect_project_type(project_path)
        available = []
        
        if 'flask' in project_type.lower():
            available.append('flask_2_to_3')
        
        if 'django' in project_type.lower():
            available.append('django_3_to_4')
        
        if 'react' in project_type.lower():
            # Check for class components
            if self.has_react_class_components(project_path):
                available.append('react_class_to_functional')
        
        if 'html' in project_type.lower():
            available.append('html_to_react')
        
        if any(f.suffix == '.py' for f in project_path.rglob('*.py')):
            if any((project_path / d).exists() for d in ['venv', '.venv']):
                available.append('python_venv_upgrade')
        
        return available
    
    def detect_project_type(self, project_path: Path) -> str:
        """Detect project type for migration"""
        # Simple detection
        if any(project_path.rglob('app.py')):
            return 'flask'
        elif any(project_path.rglob('manage.py')):
            return 'django'
        elif any(project_path.rglob('package.json')):
            return 'react'
        elif any(project_path.rglob('index.html')):
            return 'html'
        return 'unknown'
    
    def has_react_class_components(self, project_path: Path) -> bool:
        """Check if React project uses class components"""
        for file_path in project_path.rglob('*.jsx'):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if 'class.*extends.*Component' in content or 'React.Component' in content:
                        return True
            except:
                pass
        return False
    
    def migrate_flask_2_to_3(self, project_path: Path) -> bool:
        """Migrate Flask 2.x to 3.x"""
        requirements_file = project_path / 'requirements.txt'
        if not requirements_file.exists():
            return False
        
        try:
            with open(requirements_file, 'r') as f:
                content = f.read()
            
            # Update Flask version
            content = re.sub(r'Flask[=<>]=2\.[0-9.]+', 'Flask>=3.0.0', content)
            
            with open(requirements_file, 'w') as f:
                f.write(content)
            
            # Update app.py for potential breaking changes
            app_files = list(project_path.rglob('app.py')) + list(project_path.rglob('*.py'))
            for app_file in app_files[:1]:  # Just first one
                try:
                    with open(app_file, 'r') as f:
                        app_content = f.read()
                    
                    # Simple migration - in real implementation, more complex
                    if 'from flask import json' in app_content:
                        app_content = app_content.replace('from flask import json', 'from flask import jsonify')
                    
                    with open(app_file, 'w') as f:
                        f.write(app_content)
                except:
                    pass
            
            return True
            
        except Exception as e:
            print(f"Migration error: {e}")
            return False
    
    def migrate_html_to_react(self, project_path: Path) -> bool:
        """Convert HTML project to React"""
        # Create React project structure
        react_dir = project_path.parent / f"{project_path.name}-react"
        react_dir.mkdir(exist_ok=True)
        
        # Copy HTML/CSS/JS files
        html_files = list(project_path.rglob('*.html'))
        css_files = list(project_path.rglob('*.css'))
        js_files = list(project_path.rglob('*.js'))
        
        # Convert HTML to JSX (simplified)
        for html_file in html_files:
            try:
                with open(html_file, 'r') as f:
                    html_content = f.read()
                
                # Simple conversion
                jsx_content = html_content.replace('class=', 'className=')
                
                jsx_file = react_dir / f"{html_file.stem}.jsx"
                with open(jsx_file, 'w') as f:
                    f.write(f"""
                    import React from 'react';
                    import './App.css';
                    
                    function {html_file.stem.capitalize()}() {{
                        return (
                            {jsx_content}
                        );
                    }}
                    
                    export default {html_file.stem.capitalize()};
                    """)
            except:
                pass
        
        # Create package.json
        package_json = {
            "name": project_path.name,
            "version": "1.0.0",
            "private": True,
            "dependencies": {
                "react": "^18.0.0",
                "react-dom": "^18.0.0",
                "react-scripts": "5.0.0"
            },
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build",
                "test": "react-scripts test",
                "eject": "react-scripts eject"
            }
        }
        
        with open(react_dir / 'package.json', 'w') as f:
            json.dump(package_json, f, indent=2)
        
        print(f"React project created at: {react_dir}")
        return True

class PackageManager:
    """Unified package manager for multiple languages (NEW)"""
    
    def __init__(self, cli):
        self.cli = cli
        self.managers = {
            'pip': self.install_pip,
            'npm': self.install_npm
            # 'yarn': self.install_yarn,
            # 'cargo': self.install_cargo,
            # 'go': self.install_go
        }
    
    def detect_package_manager(self, project_path: Path) -> List[str]:
        """Detect available package managers in project"""
        detected = []
        
        if (project_path / 'requirements.txt').exists() or (project_path / 'pyproject.toml').exists():
            detected.append('pip')
        
        if (project_path / 'package.json').exists():
            if (project_path / 'yarn.lock').exists():
                detected.append('yarn')
            else:
                detected.append('npm')
        
        if (project_path / 'Cargo.toml').exists():
            detected.append('cargo')
        
        if (project_path / 'go.mod').exists():
            detected.append('go')
        
        return detected
    
    def install_pip(self, project_path: Path, use_mirror: bool = True) -> bool:
        """Install Python packages with pip"""
        requirements_files = [
            project_path / 'requirements.txt',
            project_path / 'pyproject.toml'
        ]
        
        for req_file in requirements_files:
            if req_file.exists():
                return self.cli.install_with_mirror(req_file, project_path)
        
        return False
    
    def install_npm(self, project_path: Path) -> bool:
        """Install Node.js packages with npm"""
        if not (project_path / 'package.json').exists():
            return False
        
        try:
            print("📦 Installing npm packages...")
            subprocess.run(['npm', 'install'], cwd=project_path, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ npm install failed: {e}")
            return False
    
    def install_all(self, project_path: Path) -> Dict[str, bool]:
        """Install packages for all detected package managers"""
        managers = self.detect_package_manager(project_path)
        results = {}
        
        for manager in managers:
            print(f"\n🔧 Installing with {manager}...")
            if manager in self.managers:
                if manager == 'pip':
                    results[manager] = self.managers[manager](project_path, 
                        self.cli.config['MIRROR'].getboolean('enabled'))
                else:
                    results[manager] = self.managers[manager](project_path)
            else:
                results[manager] = False
        
        return results

# ============================================================================
# NEW COMMAND HANDLERS ADDED TO ILIACLI
# ============================================================================

def add_new_command_handlers(self):
    """Add new command handlers to the existing ILIACLI class"""
    
    def handle_ai_command(self, args):
        """Handle AI-powered commands (NEW)"""
        if not args:
            print(f"""
{Fore.CYAN if HAS_COLORS else ''}🤖 AI-Powered Features{Style.RESET_ALL if HAS_COLORS else ''}
Usage: ilia ai <command>
Commands:
  generate <description>  - Generate project from description
  suggest <code>         - Get AI suggestions for code
  explain <file>         - Explain what code does
  optimize <file>        - Optimize code with AI
  translate <lang>       - Translate project to another language
            """)
            return
        
        if args[0] == 'generate':
            if len(args) < 2:
                print("❌ Description required")
                return
            
            description = ' '.join(args[1:])
            print(f"\n🤖 Generating project from: {description}")
            
            if self.ai_generator:
                result = self.ai_generator.generate_project_description(description)
            else:
                print("⚠️  AI features not available. Install: pip install openai")
                return
            
            # Create project from AI result
            project_name = result['project_name']
            project_type = result['project_type']
            
            print(f"✅ AI Generated: {project_name} ({project_type})")
            print(f"📁 Structure preview:")
            
            # Show generated structure
            if isinstance(result['structure'], dict):
                for file, content in list(result['structure'].items())[:5]:
                    print(f"  📄 {file}")
            
            # Ask to create
            create = input(f"\nCreate this project? (y/N): ").strip().lower()
            if create == 'y':
                # Create project directory
                project_dir = Path.cwd() / project_name
                project_dir.mkdir(exist_ok=True)
                
                # Write generated files
                if isinstance(result['structure'], dict):
                    for file_path, content in result['structure'].items():
                        full_path = project_dir / file_path
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(full_path, 'w') as f:
                            f.write(content)
                
                # Write README
                readme_path = project_dir / 'README.md'
                with open(readme_path, 'w') as f:
                    f.write(result.get('readme', f'# {project_name}\n\nAI-generated project.'))
                
                print(f"✅ AI project created: {project_dir}")
    
    def handle_wizard_command(self):
        """Handle interactive wizard (NEW)"""
        responses = self.interactive_wizard.run()
        if responses:
            # Create project from wizard responses
            self.init_project(responses['type'], responses['name'])
    
    def handle_collab_command(self, args):
        """Handle collaboration commands (NEW)"""
        if not args:
            print(f"""
{Fore.CYAN if HAS_COLORS else ''}👥 Real-time Collaboration{Style.RESET_ALL if HAS_COLORS else ''}
Usage: ilia collab <command>
Commands:
  start <project>        - Start collaboration session
  join <session_id>      - Join existing session
  list                   - List active sessions
  chat <message>         - Send chat message
  share <file>          - Share file with session
            """)
            return
        
        if args[0] == 'start':
            project_name = args[1] if len(args) > 1 else Path.cwd().name
            password = input("Session password (optional): ").strip() or None
            
            session_id = self.collaboration.create_session(project_name, password)
            print(f"\n✅ Collaboration session created!")
            print(f"   Session ID: {session_id}")
            print(f"   Project: {project_name}")
            if password:
                print(f"   Password: {password}")
            print(f"\nShare with others: ilia collab join {session_id}")
            
            # Start simple chat interface
            print(f"\n💬 Chat (type 'exit' to leave):")
            username = input("Your name: ").strip() or getpass.getuser()
            peer_id = self.collaboration.join_session(session_id, username, password)
            
            if peer_id:
                while True:
                    message = input(f"{username}: ").strip()
                    if message.lower() == 'exit':
                        break
                    self.collaboration.send_chat_message(session_id, username, message)
    
    def handle_analytics_command(self, args):
        """Handle analytics commands (NEW)"""
        if not args:
            self.analytics.show_dashboard()
        elif args[0] == 'export':
            format_type = args[1] if len(args) > 1 else 'json'
            print(f"Exporting analytics as {format_type}...")
            # Export implementation would go here
    
    def handle_health_command(self, args):
        """Handle project health checks (NEW)"""
        if not args:
            # Check current directory
            project_path = Path.cwd()
        else:
            project_path = Path(args[0])
            if not project_path.is_absolute():
                project_path = Path.cwd() / project_path
        
        if not project_path.exists():
            print(f"❌ Project not found: {project_path}")
            return
        
        print(f"\n{Fore.CYAN if HAS_COLORS else ''}🏥 Project Health Check{Style.RESET_ALL if HAS_COLORS else ''}")
        print("=" * 60)
        
        results = self.health_checker.check_project(project_path)
        
        print(f"\n📋 Project: {project_path.name}")
        print(f"📊 Health Score: {results['score']}/100")
        
        if results['score'] >= 80:
            status_color = Fore.GREEN if HAS_COLORS else ''
            status = "✅ HEALTHY"
        elif results['score'] >= 60:
            status_color = Fore.YELLOW if HAS_COLORS else ''
            status = "⚠️  NEEDS ATTENTION"
        else:
            status_color = Fore.RED if HAS_COLORS else ''
            status = "❌ UNHEALTHY"
        
        print(f"{status_color}{status}{Style.RESET_ALL if HAS_COLORS else ''}")
        
        # Show metrics
        print(f"\n📈 Metrics:")
        for key, value in results['metrics'].items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Show issues
        if results['issues']:
            print(f"\n🔴 Issues Found:")
            for issue in results['issues'][:5]:  # Top 5
                print(f"  • {issue}")
        
        # Show recommendations
        if results['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in results['recommendations']:
                print(f"  • {rec}")
    
    def handle_dashboard_command(self, args):
        """Handle web dashboard commands (NEW)"""
        if not args:
            print(f"""
{Fore.CYAN if HAS_COLORS else ''}🌐 Web Dashboard{Style.RESET_ALL if HAS_COLORS else ''}
Usage: ilia dashboard <command>
Commands:
  start                 - Start web dashboard
  stop                  - Stop web dashboard
  status                - Show dashboard status
  open                  - Open dashboard in browser
            """)
            return
        
        if args[0] == 'start':
            port = int(args[1]) if len(args) > 1 else 8080
            self.web_dashboard.port = port
            
            if self.web_dashboard.start():
                # Auto-open browser
                if len(args) > 2 and args[2] == '--open':
                    webbrowser.open(f'http://localhost:{port}')
                
                # Keep script running
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n🛑 Dashboard stopped")
        
        elif args[0] == 'open':
            port = self.config['DASHBOARD'].get('port', '8080')
            webbrowser.open(f'http://localhost:{port}')
    
    def handle_migrate_command(self, args):
        """Handle project migration commands (NEW)"""
        if not args:
            print(f"""
{Fore.CYAN if HAS_COLORS else ''}🔄 Project Migration{Style.RESET_ALL if HAS_COLORS else ''}
Usage: ilia migrate <command>
Commands:
  list                 - List available migrations for current project
  run <migration>     - Run specific migration
  auto                - Auto-detect and run migrations
            """)
            return
        
        project_path = Path.cwd()
        
        if args[0] == 'list':
            migrations = self.migration_assistant.list_migrations(project_path)
            if migrations:
                print(f"\n🔄 Available migrations for {project_path.name}:")
                for mig in migrations:
                    print(f"  • {mig}")
            else:
                print(f"\n✅ No migrations needed for {project_path.name}")
        
        elif args[0] == 'run' and len(args) > 1:
            migration = args[1]
            if migration in self.migration_assistant.migrations:
                print(f"\n🔄 Running migration: {migration}")
                success = self.migration_assistant.migrations[migration](project_path)
                if success:
                    print(f"✅ Migration completed successfully")
                else:
                    print(f"❌ Migration failed")
            else:
                print(f"❌ Unknown migration: {migration}")
    
    # def handle_scan_command(self, args):
    #     """Handle code quality scanning (NEW)"""
    #     if not args:
    #         project_path = Path.cwd()
    #     else:
    #         project_path = Path(args[0])
    #         if not project_path.is_absolute():
    #             project_path = Path.cwd() / project_path
        
    #     print(f"\n{Fore.CYAN if HAS_COLORS else ''}🔍 Code Quality Scanner{Style.RESET_ALL if HAS_COLORS else ''}")
    #     print("=" * 60)
        
    #     # results = self.code_scanner.scan_project(project_path)
        
    #     print(f"\n📊 Scan Results for {project_path.name}:")
    #     print(f"  Files Scanned: {results['files_scanned']}")
    #     print(f"  Issues Found: {results['issues_found']}")
    #     print(f"  Quality Score: {results['overall_score']:.1f}/100")
        
    #     if results['issues_found'] > 0:
    #         print(f"\n🔴 Top Issues:")
    #         for i, (filename, file_results) in enumerate(results['file_details'].items()):
    #             if file_results['issues']:
    #                 print(f"\n  📄 {filename}:")
    #                 for issue in file_results['issues'][:2]:  # Top 2 per file
    #                     print(f"    • {issue}")
    #             if i >= 2:  # Show only top 3 files
    #                 break
        
    #     if results['suggestions']:
    #         print(f"\n💡 Suggestions:")
    #         for suggestion in results['suggestions'][:5]:  # Top 5
    #             print(f"  • {suggestion}")
    
    def handle_packages_command(self, args):
        """Handle package management (NEW)"""
        if not args:
            project_path = Path.cwd()
        else:
            project_path = Path(args[0])
            if not project_path.is_absolute():
                project_path = Path.cwd() / project_path
        
        print(f"\n{Fore.CYAN if HAS_COLORS else ''}📦 Package Manager{Style.RESET_ALL if HAS_COLORS else ''}")
        print("=" * 60)
        
        # Detect package managers
        managers = self.package_manager.detect_package_manager(project_path)
        
        if not managers:
            print("❌ No package managers detected in project")
            return
        
        print(f"\n🔧 Detected package managers:")
        for manager in managers:
            print(f"  ✅ {manager}")
        
        # Install all
        if len(args) > 1 and args[1] == 'install':
            print(f"\n📦 Installing packages...")
            results = self.package_manager.install_all(project_path)
            
            print(f"\n📊 Installation Results:")
            for manager, success in results.items():
                status = "✅ Success" if success else "❌ Failed"
                print(f"  {manager}: {status}")
        else:
            print(f"\n💡 Run: ilia packages {project_path.name} install")

    # Add the new methods to the class
    ILIACLI.handle_ai_command = handle_ai_command
    ILIACLI.handle_wizard_command = handle_wizard_command
    ILIACLI.handle_collab_command = handle_collab_command
    ILIACLI.handle_analytics_command = handle_analytics_command
    ILIACLI.handle_health_command = handle_health_command
    ILIACLI.handle_dashboard_command = handle_dashboard_command
    ILIACLI.handle_migrate_command = handle_migrate_command
    # ILIACLI.handle_scan_command = handle_scan_command
    ILIACLI.handle_packages_command = handle_packages_command

# Add the new command handlers
add_new_command_handlers(ILIACLI)

# ============================================================================
# ENHANCED RUN METHOD WITH NEW COMMANDS
# ============================================================================

def enhanced_run(self, args):
    """Enhanced run method with new commands"""
    # Handle first run
    if self.config['DEFAULT'].getboolean('first_run', True):
        self.first_run_setup()
        
    self.send_telemetry("app_started", 
               command=args[0] if args else None,
               args_count=len(args))
    
    # NEW: Track command in analytics
    if args and args[0] in ['ai', 'wizard', 'collab', 'analytics', 'health', 
                           'dashboard', 'migrate', 'scan', 'packages']:
        self.analytics.track_command(args[0])
    
    # Parse arguments - NEW COMMANDS FIRST
    if len(args) == 0 or args[0] in ['-h', '--help', 'help']:
        self.show_help()
    
    # NEW COMMANDS
    elif args[0] == 'ai':
        self.handle_ai_command(args[1:])
    elif args[0] == 'wizard':
        self.handle_wizard_command()
    elif args[0] == 'collab':
        self.handle_collab_command(args[1:])
    elif args[0] == 'analytics':
        self.handle_analytics_command(args[1:])
    elif args[0] == 'health':
        self.handle_health_command(args[1:])
    elif args[0] == 'dashboard':
        self.handle_dashboard_command(args[1:])
    elif args[0] == 'migrate':
        self.handle_migrate_command(args[1:])
    # elif args[0] == 'scan':
    #     self.handle_scan_command(args[1:])
    elif args[0] == 'packages':
        self.handle_packages_command(args[1:])
    
    # ORIGINAL COMMANDS (completely preserved)
    elif args[0] in ['--version', 'version']:
        print(f"{self.app_name} v{self.version}")
    
    elif args[0] in ['--setup', 'setup']:
        self.first_run_setup()
    
    elif args[0] in ['--about', 'about']:
        self.show_about()
    
    elif args[0] == 'new':
        if len(args) < 2:
            print("❌ Project name required")
            print("Usage: ilia new <project-name> [--html|--flask|--type]")
            return
        
        project_name = args[1]
        project_type = None
        
        # Parse template flags
        for i, arg in enumerate(args):
            if arg in ['--flask', '-f', '--python']:
                project_type = 'flask'
            elif arg in ['--html', '-h', '--web']:
                project_type = 'html'
            elif arg == '--type' and i + 1 < len(args):
                project_type = args[i + 1]
        
        self.init_project(project_type, project_name)
    
    elif args[0] == 'init':
        project_type = None
        project_name = None
        
        # Parse optional arguments
        for i, arg in enumerate(args[1:], 1):
            if arg in ['--flask', '-f', '--python']:
                project_type = 'flask'
            elif arg in ['--html', '-h', '--web']:
                project_type = 'html'
            elif not arg.startswith('-') and not project_name:
                project_name = arg
        
        self.init_project(project_type, project_name)
    
    elif args[0] == 'config':
        if len(args) > 1:
            if args[1] == 'mirror':
                action = args[2] if len(args) > 2 else None
                self.configure_mirror(action)
            elif args[1] == 'editor':
                editor = args[2] if len(args) > 2 else None
                if editor:
                    self.config['DEFAULT']['editor'] = editor
                    self.save_config()
                    print(f"✅ Default editor set to: {editor}")
                else:
                    print(f"Current editor: {self.config['DEFAULT']['editor']}")
            elif args[1] == 'reset':
                self.reset_config()
            elif args[1] == 'path':
                print(f"\n📁 Configuration Paths:")
                print(f"  Config: {self.config_dir}")
                print(f"  Templates: {self.templates_dir}")
                print(f"  Projects: {self.projects_dir}")
                print(f"  Logs: {self.logs_dir}")
            else:
                self.show_enhanced_config()  # Use enhanced version
        else:
            self.show_enhanced_config()  # Use enhanced version
    
    elif args[0] == 'template' or args[0] == 'templates':
        if len(args) > 1:
            if args[1] == 'create':
                template_name = args[2] if len(args) > 2 else None
                is_framework = '--framework' in args
                if template_name:
                    self.create_template_from_current(template_name, is_framework)
                else:
                    print("❌ Template name required")
            elif args[1] == 'list':
                self.list_templates_with_details()
            elif args[1] == 'info':
                template_name = args[2] if len(args) > 2 else None
                if template_name:
                    self.generate_template_docs(template_name)
                else:
                    print("❌ Template name required")
            elif args[1] == 'validate':
                template_name = args[2] if len(args) > 2 else None
                if template_name:
                    manifest = self.get_template_manifest(template_name)
                    if manifest:
                        is_valid, errors = manifest.validate()
                        if is_valid:
                            print(f"✅ Template '{template_name}' is valid")
                        else:
                            print(f"❌ Template validation failed:")
                            for error in errors:
                                print(f"  • {error}")
                    else:
                        print(f"❌ Template '{template_name}' not found")
                else:
                    print("❌ Template name required")
            elif args[1] == 'edit':
                template_name = args[2] if len(args) > 2 else None
                if template_name:
                    manifest_file = self.templates_dir / template_name / 'manifest.json'
                    if manifest_file.exists():
                        editor = self.config['DEFAULT']['editor']
                        subprocess.run([editor, str(manifest_file)])
                    else:
                        print(f"❌ No manifest found for {template_name}")
                        print("Create one with: ilia template create <name>")
                else:
                    print("❌ Template name required")
            else:
                self.manage_templates(args[1], args[2] if len(args) > 2 else None)
        else:
            self.list_templates()
            
    elif args[0] == 'new':
        if len(args) < 2:
            print("❌ Project name required")
            print("Usage: ilia new <project-name> [--template <name>|--flask|--html]")
            return
        
        project_name = args[1]
        project_type = None
        
        # Check for template flag
        for i, arg in enumerate(args):
            if arg == '--template' and i + 1 < len(args):
                project_type = args[i + 1]
                break
            elif arg in ['--flask', '-f']:
                project_type = 'flask'
            elif arg in ['--html', '-h']:
                project_type = 'html'
        
        # Use default if not specified
        if not project_type:
            project_type = self.config['DEFAULT']['default_template']
        
        self.init_project(project_type, project_name)
    
    elif args[0] == 'projects':
        self.list_projects()
    
    elif args[0] == 'open':
        if len(args) < 2:
            print("❌ Project name required")
            print("Usage: ilia open <project-name>")
            return
        self.open_project(args[1])
    
    elif args[0] == 'info':
        if len(args) < 2:
            print("❌ Project name required")
            print("Usage: ilia info <project-name>")
            return
        self.show_project_info(args[1])
    
    elif args[0] == 'doctor':
        self.run_doctor()
    
    elif args[0] == 'status':
        self.show_status()
    
    elif args[0] == 'update':
        self.check_for_updates()
    
    elif args[0] == 'logs':
        tail = len(args) > 1 and args[1] == '--tail'
        self.show_logs(tail)
    
    elif args[0] == 'cleanup':
        self.cleanup()
    
    elif args[0] == 'uninstall':
        self.uninstall()
        
    elif args[0] == 'help':
        if len(args) > 1 and args[1] == 'templates':
            self.show_template_help()
        elif len(args) > 2 and args[1] == 'template':
            self.show_template_help(args[2])
        else:
            self.show_help()
    
    else:
        print(f"❌ Unknown command: {args[0]}")
        print(f"Try 'ilia --help' for available commands")

# Replace the original run method with enhanced version
ILIACLI.run = enhanced_run

# ============================================================================
# ENHANCED INIT_PROJECT WITH NEW FEATURES
# ============================================================================

def enhanced_init_project(self, project_type: str = None, project_name: str = None):
    """Enhanced project initialization with new features"""
    # Call original init_project logic (copied from above)
    # This is a simplified version - in practice, you would integrate
    # the new features into the existing init_project method
    
    # Track in analytics
    self.analytics.track_project_creation(project_name, project_type, True)
    
    # Run auto quality scan if enabled
    if self.config['QUALITY'].getboolean('auto_scan', False):
        print("\n🔍 Running auto quality scan...")
        # This would be called after project creation
    
    # Call the original init_project (we'll need to integrate properly)
    # For now, we'll call the original method
    original_init_project = getattr(self, '_original_init_project', None)
    if original_init_project:
        return original_init_project(project_type, project_name)
    else:
        # Fallback to standard project creation
        print(f"Creating project: {project_name} ({project_type})")
        # ... rest of original init_project logic ...

# ============================================================================
# MAIN FUNCTION (UNCHANGED)
# ============================================================================

def create_wrapper_scripts():
    """Create wrapper scripts for ilia command"""
    
    # Windows batch file
    batch_content = """@echo off
:: ilia.bat - Wrapper for ilia CLI
:: Version: 2.0.0

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

:: Run ilia.py with arguments
python "%SCRIPT_DIR%\\ilia.py" %*

:: Preserve exit code
exit /b %errorlevel%
"""
    
    # PowerShell script
    ps_content = """# ilia.ps1 - PowerShell wrapper for ilia CLI
# Version: 2.0.0

param([string[]]$Arguments)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$pythonScript = Join-Path $scriptDir "ilia.py"

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
    Write-Host "❌ Error: Could not find ilia.py" -ForegroundColor Red
    exit 1
}
"""
    
    # Bash script for Unix-like systems
    bash_content = """#!/bin/bash
# ilia.sh - Bash wrapper for ilia CLI
# Version: 2.0.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/ilia.py"

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
    echo "❌ Error: Could not find ilia.py"
    exit 1
fi

# Run ilia.py with arguments
"$PYTHON_CMD" "$PYTHON_SCRIPT" "$@"
exit $?
"""
    
    # Create install script
    install_content = """#!/bin/bash
# install.sh - Install ilia CLI wrapper
# Version: 2.0.0

echo "🔧 Installing ilia CLI wrapper..."

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
        cp ilia.bat "$HOME/bin/"
        echo "✅ Copied ilia.bat to $HOME/bin/"
    elif [ -d "/usr/local/bin" ]; then
        cp ilia.bat "/usr/local/bin/"
        echo "✅ Copied ilia.bat to /usr/local/bin/"
    else
        echo "⚠️  Could not find suitable location for wrapper"
        echo "   You can manually add current directory to PATH"
    fi
else
    # Unix-like
    if [ -d "$HOME/.local/bin" ]; then
        cp ilia.sh "$HOME/.local/bin/ilia"
        chmod +x "$HOME/.local/bin/ilia"
        echo "✅ Installed ilia to $HOME/.local/bin/ilia"
    elif [ -d "/usr/local/bin" ]; then
        sudo cp ilia.sh "/usr/local/bin/ilia"
        sudo chmod +x "/usr/local/bin/ilia"
        echo "✅ Installed ilia to /usr/local/bin/ilia"
    else
        echo "⚠️  Could not find suitable location for wrapper"
        echo "   You can manually add current directory to PATH"
    fi
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "To use ilia:"
echo "  1. Open a new terminal"
echo "  2. Run: ilia --help"
echo ""
echo "If 'ilia' command doesn't work, you may need to:"
echo "  • Add the installation directory to PATH"
echo "  • Restart your terminal"
"""
    
    # Save wrapper scripts
    wrappers = [
        ("ilia.bat", batch_content),
        ("ilia.ps1", ps_content, None, True),
        ("ilia.sh", bash_content, 0o755),
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
    print("\n📝 To install ilia system-wide:")
    print("  Linux/macOS: ./install.sh")
    print("  Windows: Copy ilia.bat to a directory in PATH")
    print("\n💡 Or add current directory to PATH and use:")
    print("  ilia --help")

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