# 📋 ILIA Template Manifest Guide

## Table of Contents
1. [What is a Manifest?](#what-is-a-manifest)
2. [Basic Structure](#basic-structure)
3. [Complete Example](#complete-example)
4. [Field Reference](#field-reference)
5. [Template Variables](#template-variables)
6. [Commands](#commands)
7. [Dependencies](#dependencies)
8. [Best Practices](#best-practices)
9. [Common Patterns](#common-patterns)
10. [Troubleshooting](#troubleshooting)

## What is a Manifest?

A `manifest.json` file defines how your template behaves. It tells ILIA:
- What variables to ask for
- What commands to run before/after copying
- What dependencies are needed
- How to validate the template

## Basic Structure

```json
{
  "name": "template-name",
  "version": "1.0.0",
  "description": "What this template does",
  "type": "framework",
  "framework": "flask",
  "variables": [],
  "commands": {},
  "dependencies": {},
  "required_files": [],
  "ignore_patterns": [],
  "metadata": {}
}
```

## Complete Example

Here's a real-world example for a Flask API template:

```json
{
  "name": "flask-api-template",
  "version": "2.0.0",
  "description": "Production-ready Flask REST API with JWT authentication",
  "type": "framework",
  "framework": "flask",
  
  "variables": [
    {
      "name": "project_name",
      "description": "Your API project name",
      "default": "myapi",
      "required": true
    },
    {
      "name": "author",
      "description": "Author name",
      "default": "",
      "required": true
    },
    {
      "name": "database",
      "description": "Database type (postgresql/mysql/sqlite)",
      "default": "postgresql",
      "required": false
    },
    {
      "name": "use_docker",
      "description": "Include Docker configuration",
      "default": "true",
      "required": false
    }
  ],
  
  "commands": {
    "pre_copy": [
      "echo 'Creating {{ project_name }} API...'",
      "mkdir -p logs"
    ],
    "post_copy": [
      "python -m venv venv",
      "source venv/bin/activate || venv\\Scripts\\activate",
      "pip install -r requirements.txt",
      "python init_db.py"
    ],
    "setup": [
      "git init",
      "git add .",
      "git commit -m 'Initial commit: {{ project_name }} API'"
    ]
  },
  
  "dependencies": {
    "python": [
      "flask==2.3.0",
      "flask-jwt-extended==4.5.0",
      "sqlalchemy==2.0.0",
      "psycopg2-binary==2.9.0"
    ],
    "node": [
      "jest",
      "supertest"
    ],
    "system": [
      "docker",
      "docker-compose"
    ]
  },
  
  "required_files": [
    "app.py",
    "requirements.txt",
    "README.md"
  ],
  
  "ignore_patterns": [
    ".git",
    "__pycache__",
    "*.pyc",
    ".env",
    "venv",
    "node_modules",
    ".DS_Store"
  ],
  
  "metadata": {
    "author": "Your Name",
    "created": "2024-01-01",
    "license": "MIT",
    "tags": ["api", "flask", "rest", "jwt"],
    "website": "https://example.com"
  }
}
```

## Field Reference

### `name` (Required)
The template name shown in listings
```json
"name": "my-awesome-template"
```

### `version` (Optional, defaults to "1.0.0")
Semantic version of the template
```json
"version": "2.1.3"
```

### `description` (Optional)
Human-readable description
```json
"description": "React dashboard with authentication and dark mode"
```

### `type` (Optional, defaults to "files")
- `"framework"` - Language-specific framework (Flask, React, etc.)
- `"files"` - Generic file template
```json
"type": "framework"
```

### `framework` (Auto-detected if omitted)
The framework this template targets:
- `"flask"`, `"django"`, `"react"`, `"vue"`, `"angular"`, `"html"`, `"rust"`, `"go"`, `"custom"`
```json
"framework": "react"
```

## Template Variables

Variables are placeholders in your files that get replaced when creating a project.

### Variable Structure

```json
{
  "name": "variable_name",           // Required - used in {{ variable_name }}
  "description": "What this is for", // Required - shown to user
  "default": "default_value",        // Optional - pre-filled answer
  "required": true                    // Optional - must provide value
}
```

### Using Variables in Files

In your template files, use `{{ variable_name }}`:

**app.py:**
```python
"""
{{ project_name }}
Author: {{ author }}
Version: {{ version }}
"""

def main():
    print(f"Welcome to {{ project_name }}!")
    print(f"Running on port {{ port }}")
```

**README.md:**
```markdown
# {{ project_name }}

Created by {{ author }} on {{ date }}

## Configuration
- Database: {{ database }}
- Port: {{ port }}

## License
{{ license }}
```

**docker-compose.yml:**
```yaml
version: '3'
services:
  {{ project_name }}:
    build: .
    ports:
      - "{{ port }}:5000"
    environment:
      - DB_TYPE={{ database }}
```

### Special Built-in Variables

These are automatically available without definition:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{ project_name }}` | Project name from user input | myapp |
| `{{ year }}` | Current year | 2024 |
| `{{ date }}` | Current date (YYYY-MM-DD) | 2024-01-15 |
| `{{ timestamp }}` | Full timestamp | 2024-01-15 14:30:00 |
| `{{ author }}` | From config or user input | John Doe |
| `{{ email }}` | From config | john@example.com |
| `{{ version }}` | Default 1.0.0 | 1.0.0 |

## Commands

Commands run at three different stages:

### `pre_copy` - Before files are copied
Run before any template files are copied. Good for:
- Creating directories
- Validating environment
- Downloading prerequisites

```json
"pre_copy": [
  "echo 'Starting setup for {{ project_name }}'",
  "mkdir -p {{ project_dir }}/logs",
  "python --version"
]
```

### `post_copy` - After files are copied
Run after files are copied but before final setup. Good for:
- Installing dependencies
- Setting up virtual environments
- Initial configuration

```json
"post_copy": [
  "cd {{ project_dir }}",
  "python -m venv venv",
  "source venv/bin/activate || venv\\Scripts\\activate",
  "pip install -r requirements.txt",
  "npm install"
]
```

### `setup` - Final setup commands
Run last, after everything else. Good for:
- Git initialization
- Database seeding
- Starting services

```json
"setup": [
  "git init",
  "git add .",
  "git commit -m 'Initial commit for {{ project_name }}'",
  "docker-compose up -d",
  "python seed_database.py"
]
```

### Special Variables in Commands

| Variable | Description |
|----------|-------------|
| `{{ project_dir }}` | Full path to the new project directory |

### Command Examples by Platform

**Cross-platform:**
```json
"post_copy": [
  "python -m pip install --upgrade pip",
  "pip install -r requirements.txt"
]
```

**Windows-specific:**
```json
"post_copy": [
  "venv\\Scripts\\activate",
  "pip install -r requirements.txt"
]
```

**Unix-specific:**
```json
"post_copy": [
  "source venv/bin/activate",
  "pip install -r requirements.txt"
]
```

## Dependencies

Declare dependencies for different package managers:

### Python Dependencies
```json
"dependencies": {
  "python": [
    "flask==2.3.0",
    "requests>=2.28.0",
    "pytest",
    "black"
  ]
}
```

### Node.js Dependencies
```json
"dependencies": {
  "node": [
    "react@18.2.0",
    "express",
    "jest",
    "webpack"
  ]
}
```

### System Dependencies
```json
"dependencies": {
  "system": [
    "docker",
    "redis-server",
    "postgresql",
    "nginx"
  ]
}
```

### All Together
```json
"dependencies": {
  "python": ["flask", "sqlalchemy"],
  "node": ["react", "axios"],
  "system": ["docker", "git"]
}
```

## Required Files

List files that must exist for the template to be valid:

```json
"required_files": [
  "app.py",
  "requirements.txt",
  "README.md",
  "package.json",
  "index.html"
]
```

The system will warn if any required files are missing.

## Ignore Patterns

Files/directories to exclude when copying:

```json
"ignore_patterns": [
  ".git",
  "__pycache__",
  "*.pyc",
  ".env",
  "venv",
  "node_modules",
  ".DS_Store",
  "*.log",
  "dist",
  "build",
  ".idea",
  ".vscode"
]
```

## Metadata

Additional information about the template:

```json
"metadata": {
  "author": "Your Name",
  "created": "2024-01-01",
  "modified": "2024-01-15",
  "license": "MIT",
  "tags": ["api", "flask", "rest"],
  "website": "https://example.com",
  "repository": "https://github.com/user/template",
  "category": "web-development"
}
```

## Best Practices

### 1. **Use Descriptive Variable Names**
```json
// Bad
{"name": "v1", "description": "Variable 1"}

// Good
{"name": "database_port", "description": "Port for database connection"}
```

### 2. **Set Sensible Defaults**
```json
"variables": [
  {"name": "port", "default": "5000", "required": false},
  {"name": "environment", "default": "development", "required": false}
]
```

### 3. **Add Error Handling in Commands**
```json
"post_copy": [
  "python -c 'import sys; sys.exit(0 if __import__(\"flask\") else 1)' || echo 'Flask installation failed'"
]
```

### 4. **Keep Commands Simple**
```json
// Bad - too complex
"post_copy": ["python -c '... huge one-liner ...'"]

// Good - use script files
"post_copy": ["python setup.py", "bash ./scripts/init.sh"]
```

### 5. **Validate Early**
```json
"pre_copy": [
  "python --version || echo 'Python required' && exit 1",
  "npm --version || echo 'Node.js required' && exit 1"
]
```

## Common Patterns

### Pattern 1: Flask + React Template
```json
{
  "name": "flask-react-template",
  "type": "framework",
  "framework": "react",
  "variables": [
    {"name": "api_port", "default": "5000"},
    {"name": "web_port", "default": "3000"}
  ],
  "commands": {
    "post_copy": [
      "cd backend && pip install -r requirements.txt",
      "cd frontend && npm install"
    ],
    "setup": [
      "echo 'Run: cd backend && python app.py'",
      "echo 'Run: cd frontend && npm start'"
    ]
  },
  "dependencies": {
    "python": ["flask", "flask-cors"],
    "node": ["react", "axios"]
  }
}
```

### Pattern 2: Dockerized Application
```json
{
  "name": "docker-app-template",
  "variables": [
    {"name": "service_name", "required": true},
    {"name": "port", "default": "8080"}
  ],
  "commands": {
    "post_copy": [
      "docker build -t {{ service_name }} .",
      "docker-compose up -d"
    ]
  },
  "commands": {
    "setup": [
      "echo 'Service running on port {{ port }}'"
    ]
  },
  "dependencies": {
    "system": ["docker", "docker-compose"]
  }
}
```

### Pattern 3: CLI Tool Template
```json
{
  "name": "cli-tool-template",
  "type": "framework",
  "variables": [
    {"name": "command_name", "required": true},
    {"name": "entry_point", "default": "main.py"}
  ],
  "commands": {
    "post_copy": [
      "pip install -e .",
      "chmod +x {{ command_name }}"
    ]
  },
  "required_files": ["setup.py", "{{ entry_point }}"]
}
```

## Troubleshooting

### Common Issues and Solutions

**Issue:** Variables not being replaced
```bash
# Check your syntax - must have spaces inside braces
# ✅ Correct: {{ variable_name }}
# ❌ Wrong: {{variable_name}} or {variable_name}
```

**Issue:** Commands fail on Windows
```json
// Use conditional commands
"post_copy": [
  "if exist venv\\Scripts\\activate (venv\\Scripts\\activate) else (source venv/bin/activate)"
]
```

**Issue:** Template validation fails
```bash
# Validate your template
ilia templates validate my-template

# Check the manifest syntax
cat manifest.json | python -m json.tool
```

**Issue:** Large template imports slowly
```json
// Add more ignore patterns
"ignore_patterns": [
  "*.log", "*.tmp", "*.cache", "*.pyc",
  "__pycache__", ".git", "node_modules"
]
```

## Testing Your Manifest

After creating your manifest, test it:

```bash
# 1. Validate syntax
ilia templates validate my-template

# 2. View documentation
ilia help template my-template
# or
ilia templates info my-template

# 3. Create a test project
ilia new test-project --template my-template

# 4. Check if variables were replaced
grep -r "{{" test-project/  # Should find nothing

# 5. Test commands ran successfully
cd test-project && python app.py  # Should work
```

## Quick Reference Card

```json
{
  "name": "string",                    // Required
  "version": "string",                 // Optional
  "description": "string",             // Optional
  "type": "framework|files",          // Optional
  "framework": "string",               // Optional (auto-detected)
  
  "variables": [                       // Template customization
    {
      "name": "string",                // Required
      "description": "string",         // Required  
      "default": "string",             // Optional
      "required": true|false           // Optional
    }
  ],
  
  "commands": {                        // Automation
    "pre_copy": ["string"],            // Before files copy
    "post_copy": ["string"],           // After files copy
    "setup": ["string"]                // Final setup
  },
  
  "dependencies": {                    // Requirements
    "python": ["string"],
    "node": ["string"], 
    "system": ["string"]
  },
  
  "required_files": ["string"],        // Validation
  "ignore_patterns": ["string"],       // Exclusion
  "metadata": {}                       // Extra info
}
```

## Conclusion

The manifest system gives you powerful control over your templates. Start simple, test thoroughly, and gradually add more features as needed. The key is to make your templates **reusable**, **documented**, and **user-friendly**.