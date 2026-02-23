#!/usr/bin/env python3
"""
ilia CLI Telemetry Server
Production WSGI server using Waitress (better than Flask dev server)
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
import gzip
import hashlib
from typing import Dict, Any
import argparse
from werkzeug.middleware.proxy_fix import ProxyFix

# Configuration
DEFAULT_PORT = 3001
DEFAULT_HOST = '127.0.0.1'
DEFAULT_LOG_DIR = './telemetry_logs'
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max request size

# Initialize Flask app
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Setup logging
def setup_logging(log_dir: Path):
    """Setup application logging"""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Main application log
    log_file = log_dir / 'telemetry_server.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Disable Werkzeug's default logging
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# Initialize logger
log_dir = Path(DEFAULT_LOG_DIR)
logger = setup_logging(log_dir)

class TelemetryManager:
    """Manages telemetry data storage and processing"""
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.stats_file = log_dir / 'statistics.json'
        self.sessions_file = log_dir / 'sessions.json'
        
        # Ensure directories exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize statistics
        self.statistics = self.load_statistics()
        self.sessions = self.load_sessions()
    
    def load_statistics(self) -> Dict[str, Any]:
        """Load statistics from file"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Could not load statistics, starting fresh")
        
        # Default statistics structure
        return {
            'total_requests': 0,
            'events': {},
            'versions': {},
            'platforms': {},
            'first_request': None,
            'last_request': None,
            'hourly_stats': {},
            'daily_stats': {}
        }
    
    def load_sessions(self) -> Dict[str, Any]:
        """Load sessions from file"""
        if self.sessions_file.exists():
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Could not load sessions, starting fresh")
        
        return {}
    
    def save_statistics(self):
        """Save statistics to file"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.statistics, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save statistics: {e}")
    
    def save_sessions(self):
        """Save sessions to file"""
        try:
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save sessions: {e}")
    
    def anonymize_ip(self, ip_address: str) -> str:
        """Anonymize IP address (keep only first 2 octets)"""
        if not ip_address:
            return '0.0.0.0'
        
        parts = ip_address.split('.')
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}.0.0"
        return '0.0.0.0'
    
    def generate_session_hash(self, session_id: str, ip_address: str) -> str:
        """Generate anonymous session hash"""
        # Combine session_id with anonymized IP for uniqueness
        anonymized_ip = self.anonymize_ip(ip_address)
        combined = f"{session_id}_{anonymized_ip}"
        return hashlib.md5(combined.encode()).hexdigest()[:16]
    
    def process_telemetry(self, data: Dict[str, Any], client_ip: str) -> Dict[str, Any]:
        """Process and store telemetry data"""
        timestamp = datetime.now()
        date_str = timestamp.strftime('%Y-%m-%d')
        hour_str = timestamp.strftime('%Y-%m-%d %H:00')
        
        # Generate session hash
        session_id = data.get('session_id', 'unknown')
        session_hash = self.generate_session_hash(session_id, client_ip)
        
        # Update statistics
        self.statistics['total_requests'] += 1
        
        # Track events
        event_type = data.get('event', 'unknown')
        if event_type not in self.statistics['events']:
            self.statistics['events'][event_type] = 0
        self.statistics['events'][event_type] += 1
        
        # Track versions
        version = data.get('ilia_version', 'unknown')
        if version not in self.statistics['versions']:
            self.statistics['versions'][version] = 0
        self.statistics['versions'][version] += 1
        
        # Track platforms
        platform = data.get('platform', 'unknown')
        if platform not in self.statistics['platforms']:
            self.statistics['platforms'][platform] = 0
        self.statistics['platforms'][platform] += 1
        
        # Track hourly stats
        if hour_str not in self.statistics['hourly_stats']:
            self.statistics['hourly_stats'][hour_str] = 0
        self.statistics['hourly_stats'][hour_str] += 1
        
        # Track daily stats
        if date_str not in self.statistics['daily_stats']:
            self.statistics['daily_stats'][date_str] = 0
        self.statistics['daily_stats'][date_str] += 1
        
        # Update timestamps
        if not self.statistics['first_request']:
            self.statistics['first_request'] = timestamp.isoformat()
        self.statistics['last_request'] = timestamp.isoformat()
        
        # Update session data
        if session_hash not in self.sessions:
            self.sessions[session_hash] = {
                'first_seen': timestamp.isoformat(),
                'last_seen': timestamp.isoformat(),
                'event_count': 0,
                'events': {},
                'versions': set(),
                'platforms': set()
            }
        
        session_data = self.sessions[session_hash]
        session_data['last_seen'] = timestamp.isoformat()
        session_data['event_count'] += 1
        
        # Track events per session
        if event_type not in session_data['events']:
            session_data['events'][event_type] = 0
        session_data['events'][event_type] += 1
        
        # Track versions per session
        session_data['versions'].add(version)
        
        # Track platforms per session
        session_data['platforms'].add(platform)
        
        # Save updated data
        self.save_statistics()
        self.save_sessions()
        
        # Log the telemetry
        self.log_telemetry(data, client_ip, session_hash)
        
        return {
            'status': 'received',
            'session_hash': session_hash,
            'timestamp': timestamp.isoformat(),
            'event': event_type
        }
    
    def log_telemetry(self, data: Dict[str, Any], client_ip: str, session_hash: str):
        """Log telemetry data to daily files"""
        timestamp = datetime.now()
        date_str = timestamp.strftime('%Y%m%d')
        
        # Daily log file
        log_file = self.log_dir / f'telemetry_{date_str}.log'
        
        # Create log entry
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'session_hash': session_hash,
            'client_ip': self.anonymize_ip(client_ip),
            'event': data.get('event', 'unknown'),
            'data': {
                'ilia_version': data.get('ilia_version'),
                'python_version': data.get('python_version'),
                'platform': data.get('platform'),
                'mirror_enabled': data.get('mirror_enabled'),
                'auto_venv': data.get('auto_venv'),
                'auto_git': data.get('auto_git'),
                'template_type': data.get('template_type'),
                'success': data.get('success')
            }
        }
        
        # Write to daily log
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except IOError as e:
            logger.error(f"Failed to write to log file: {e}")
        
        # Also write to compressed archive (weekly)
        week_str = timestamp.strftime('%Y-W%W')
        archive_file = self.log_dir / f'archive_{week_str}.jsonl.gz'
        
        try:
            with gzip.open(archive_file, 'at', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except IOError as e:
            logger.error(f"Failed to write to archive: {e}")
        
        logger.info(f"Telemetry received: {data.get('event')} from {session_hash}")

# Initialize telemetry manager
telemetry_manager = TelemetryManager(log_dir)

@app.route('/')
def index():
    """Home page with server info"""
    return jsonify({
        'status': 'online',
        'service': 'ilia-cli-telemetry',
        'version': '1.0.0',
        'endpoints': {
            '/ilia-cli/tm/submit': 'POST - Submit telemetry data',
            '/status': 'GET - Server status',
            '/stats': 'GET - Statistics',
            '/health': 'GET - Health check'
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/status')
def status():
    """Server status with statistics"""
    stats = telemetry_manager.statistics
    
    return jsonify({
        'status': 'online',
        'uptime': 'N/A',  # Could be enhanced with process monitoring
        'statistics': {
            'total_requests': stats['total_requests'],
            'unique_sessions': len(telemetry_manager.sessions),
            'events_received': stats['events'],
            'top_events': dict(sorted(stats['events'].items(), key=lambda x: x[1], reverse=True)[:5]),
            'versions': stats['versions'],
            'platforms': stats['platforms']
        },
        'storage': {
            'log_directory': str(log_dir.absolute()),
            'log_files': len(list(log_dir.glob('*.log'))),
            'archive_files': len(list(log_dir.glob('*.gz')))
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/stats')
def stats():
    """Detailed statistics endpoint"""
    stats = telemetry_manager.statistics
    
    return jsonify({
        'total_requests': stats['total_requests'],
        'events': stats['events'],
        'versions': stats['versions'],
        'platforms': stats['platforms'],
        'hourly_distribution': stats['hourly_stats'],
        'daily_distribution': stats['daily_stats'],
        'first_request': stats['first_request'],
        'last_request': stats['last_request'],
        'unique_sessions': len(telemetry_manager.sessions),
        'session_sample': dict(list(telemetry_manager.sessions.items())[:3])  # First 3 sessions as sample
    })

@app.route('/ilia-cli/tm/submit', methods=['POST'])
def submit_telemetry():
    """Main telemetry submission endpoint"""
    try:
        # Get client IP (respecting proxies)
        if request.headers.get('X-Forwarded-For'):
            client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            client_ip = request.remote_addr
        
        # Parse JSON data
        if not request.is_json:
            return jsonify({
                'error': 'Content-Type must be application/json',
                'status': 'rejected'
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        if not data or 'event' not in data:
            return jsonify({
                'error': 'Missing required field: event',
                'status': 'rejected'
            }), 400
        
        # Process telemetry
        result = telemetry_manager.process_telemetry(data, client_ip)
        
        # Log success
        logger.info(f"Telemetry processed: {data.get('event')} from {client_ip}")
        
        return jsonify(result), 200
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON received")
        return jsonify({
            'error': 'Invalid JSON format',
            'status': 'rejected'
        }), 400
        
    except Exception as e:
        logger.error(f"Error processing telemetry: {e}")
        return jsonify({
            'error': 'Internal server error',
            'status': 'rejected'
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'status': 'error'
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        'error': 'Method not allowed',
        'status': 'error'
    }), 405

@app.errorhandler(413)
def request_too_large(error):
    """Handle 413 errors (request too large)"""
    return jsonify({
        'error': f'Request too large. Maximum size is {MAX_CONTENT_LENGTH} bytes',
        'status': 'rejected'
    }), 413

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500

def cleanup_old_logs(days_to_keep: int = 30):
    """Clean up log files older than specified days"""
    logger.info(f"Cleaning up logs older than {days_to_keep} days...")
    
    cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
    deleted_count = 0
    
    for log_file in log_dir.glob('*.log'):
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                deleted_count += 1
                logger.debug(f"Deleted old log: {log_file.name}")
            except OSError as e:
                logger.error(f"Failed to delete {log_file}: {e}")
    
    logger.info(f"Cleanup complete. Deleted {deleted_count} old log files.")

def run_with_waitress(host: str, port: int):
    """Run the server using Waitress (production WSGI server)"""
    try:
        from waitress import serve
        logger.info(f"Starting Waitress WSGI server on {host}:{port}")
        logger.info("Waitress is a production-ready WSGI server")
        serve(app, host=host, port=port, threads=8)
    except ImportError:
        logger.error("Waitress not installed. Install with: pip install waitress")
        logger.info("Falling back to development server (NOT for production)")
        app.run(host=host, port=port, debug=False)

def run_with_gunicorn(host: str, port: int, workers: int = 4):
    """Run the server using Gunicorn (recommended for production)"""
    import subprocess
    import sys
    
    logger.info(f"Starting Gunicorn WSGI server on {host}:{port}")
    logger.info(f"Workers: {workers}")
    
    cmd = [
        sys.executable, "-m", "gunicorn",
        "--bind", f"{host}:{port}",
        "--workers", str(workers),
        "--worker-class", "sync",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "--log-level", "info",
        "telemetry_server:app"
    ]
    
    subprocess.run(cmd)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='ilia CLI Telemetry Server')
    parser.add_argument('--host', default=DEFAULT_HOST, 
                       help=f'Host to bind to (default: {DEFAULT_HOST})')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                       help=f'Port to listen on (default: {DEFAULT_PORT})')
    parser.add_argument('--log-dir', default=DEFAULT_LOG_DIR,
                       help=f'Log directory (default: {DEFAULT_LOG_DIR})')
    parser.add_argument('--cleanup-days', type=int, default=30,
                       help='Delete logs older than N days (default: 30)')
    parser.add_argument('--server', choices=['waitress', 'gunicorn', 'flask'], 
                       default='waitress',
                       help='WSGI server to use (default: waitress)')
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of worker processes (gunicorn only)')
    
    args = parser.parse_args()
    
    # Update log directory if specified
    global log_dir, telemetry_manager
    log_dir = Path(args.log_dir)
    telemetry_manager = TelemetryManager(log_dir)
    
    # Clean up old logs
    cleanup_old_logs(args.cleanup_days)
    
    # Log startup
    logger.info(f"Starting ilia Telemetry Server on {args.host}:{args.port}")
    logger.info(f"Using server: {args.server.upper()}")
    logger.info(f"Log directory: {log_dir.absolute()}")
    
    # Run with selected server
    if args.server == 'waitress':
        run_with_waitress(args.host, args.port)
    elif args.server == 'gunicorn':
        run_with_gunicorn(args.host, args.port, args.workers)
    else:
        # Flask development server (NOT for production)
        logger.warning("Using Flask development server - NOT RECOMMENDED for production")
        app.run(host=args.host, port=args.port, debug=False)

if __name__ == '__main__':
    main()