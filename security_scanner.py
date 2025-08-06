
"""
Security Scanner Module - Checks for vulnerabilities before deployment
"""
import os
import re
import subprocess
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime
import hashlib
from pathlib import Path

from utils.logger import app_logger


class SecurityScanner:
    """Comprehensive security scanner for pre-deployment checks"""
    
    def __init__(self):
        self.vulnerabilities = []
        self.warnings = []
        self.info = []
        
        # Common secret patterns
        self.secret_patterns = {
            'api_key': re.compile(r'(?i)(api[_-]?key|apikey)["\s]*[=:]["\s]*([a-zA-Z0-9\-_]{20,})', re.IGNORECASE),
            'password': re.compile(r'(?i)(password|pwd)["\s]*[=:]["\s]*["\']([^"\']{8,})["\']', re.IGNORECASE),
            'secret': re.compile(r'(?i)(secret|token)["\s]*[=:]["\s]*["\']([a-zA-Z0-9\-_]{16,})["\']', re.IGNORECASE),
            'private_key': re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', re.IGNORECASE),
            'database_url': re.compile(r'(?i)(database_url|db_url)["\s]*[=:]["\s]*["\']([^"\']+://[^"\']+)["\']', re.IGNORECASE),
            'jwt_secret': re.compile(r'(?i)(jwt[_-]?secret|jwt[_-]?key)["\s]*[=:]["\s]*["\']([a-zA-Z0-9\-_]{16,})["\']', re.IGNORECASE),
            'openai_key': re.compile(r'(?i)(openai[_-]?api[_-]?key)["\s]*[=:]["\s]*["\']?(sk-[a-zA-Z0-9]{48})["\']?', re.IGNORECASE),
        }
        
        # SQL injection patterns
        self.sql_injection_patterns = [
            re.compile(r'(?i)execute\s*\(\s*["\'].*%s.*["\']', re.MULTILINE),
            re.compile(r'(?i)cursor\.execute\s*\(\s*["\'][^"\']*\+.*["\']', re.MULTILINE),
            re.compile(r'(?i)cursor\.execute\s*\(\s*f["\'][^"\']*\{.*\}.*["\']', re.MULTILINE),
            re.compile(r'(?i)db\.execute\s*\(\s*["\'][^"\']*\+.*["\']', re.MULTILINE),
            re.compile(r'(?i)query\s*=.*\+.*["\']', re.MULTILINE),
        ]
        
        # XSS patterns
        self.xss_patterns = [
            re.compile(r'render_template_string\s*\(.*request\.', re.MULTILINE | re.IGNORECASE),
            re.compile(r'innerHTML\s*=.*request\.', re.MULTILINE | re.IGNORECASE),
            re.compile(r'document\.write\s*\(.*request\.', re.MULTILINE | re.IGNORECASE),
        ]
        
        # Command injection patterns
        self.command_injection_patterns = [
            re.compile(r'(?i)os\.system\s*\(.*request\.', re.MULTILINE),
            re.compile(r'(?i)subprocess\.(run|call|Popen)\s*\([^)]*request\.', re.MULTILINE),
            re.compile(r'(?i)eval\s*\(.*request\.', re.MULTILINE),
            re.compile(r'(?i)exec\s*\(.*request\.', re.MULTILINE),
        ]

    def scan_all(self) -> Dict[str, Any]:
        """Run comprehensive security scan"""
        app_logger.info("🔒 Starting comprehensive security scan...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'scan_results': {
                'secrets': self.scan_for_secrets(),
                'sql_injection': self.scan_for_sql_injection(),
                'xss_vulnerabilities': self.scan_for_xss(),
                'command_injection': self.scan_for_command_injection(),
                'dependencies': self.check_dependencies(),
                'file_permissions': self.check_file_permissions(),
                'environment': self.check_environment_security(),
            },
            'summary': self._generate_summary()
        }
        
        return results

    def scan_for_secrets(self) -> Dict[str, Any]:
        """Scan for exposed secrets in code"""
        app_logger.info("🔍 Scanning for exposed secrets...")
        secrets_found = []
        
        # Files to scan
        scan_paths = [
            '.',
            'routes/',
            'services/',
            'utils/',
            'core/',
        ]
        
        exclude_files = {
            'security_scanner.py',
            'engineroom.db',
            'engineroom.db-shm',
            'engineroom.db-wal',
            '.git',
            '__pycache__',
            '.replit',
            'uv.lock'
        }
        
        exclude_paths = {
            '.cache',
            '.pythonlibs',
            'node_modules',
            '.vscode-server'
        }
        
        for scan_path in scan_paths:
            if os.path.exists(scan_path):
                for root, dirs, files in os.walk(scan_path):
                    # Skip excluded directories and paths
                    dirs[:] = [d for d in dirs if d not in exclude_files and not any(excluded in root for excluded in exclude_paths)]
                    
                    # Skip if current path contains excluded directories
                    if any(excluded in root for excluded in exclude_paths):
                        continue
                    
                    for file in files:
                        if file in exclude_files or not file.endswith(('.py', '.js', '.html', '.json', '.txt', '.md')):
                            continue
                            
                        file_path = os.path.join(root, file)
                        secrets_in_file = self._scan_file_for_secrets(file_path)
                        secrets_found.extend(secrets_in_file)
        
        return {
            'total_secrets_found': len(secrets_found),
            'secrets': secrets_found,
            'severity': 'HIGH' if secrets_found else 'LOW'
        }

    def _scan_file_for_secrets(self, file_path: str) -> List[Dict[str, Any]]:
        """Scan individual file for secrets"""
        secrets = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            for secret_type, pattern in self.secret_patterns.items():
                matches = pattern.finditer(content)
                for match in matches:
                    # Skip if it's a placeholder or example
                    if self._is_placeholder(match.group()):
                        continue
                        
                    secrets.append({
                        'type': secret_type,
                        'file': file_path,
                        'line': content[:match.start()].count('\n') + 1,
                        'match': match.group()[:50] + '...' if len(match.group()) > 50 else match.group(),
                        'severity': 'HIGH'
                    })
                    
        except Exception as e:
            app_logger.warning(f"Could not scan {file_path}: {e}")
            
        return secrets

    def _is_placeholder(self, text: str) -> bool:
        """Check if text appears to be a placeholder"""
        placeholders = [
            'your-api-key', 'your_api_key', 'api-key-here', 
            'password123', 'secret123', 'your-secret',
            'dev-key', 'development-key', 'test-key',
            'placeholder', 'example', 'dummy'
        ]
        
        return any(placeholder in text.lower() for placeholder in placeholders)

    def scan_for_sql_injection(self) -> Dict[str, Any]:
        """Scan for SQL injection vulnerabilities"""
        app_logger.info("🔍 Scanning for SQL injection vulnerabilities...")
        vulnerabilities = []
        
        python_files = self._get_python_files()
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in self.sql_injection_patterns:
                    matches = pattern.finditer(content)
                    for match in matches:
                        vulnerabilities.append({
                            'type': 'SQL Injection',
                            'file': file_path,
                            'line': content[:match.start()].count('\n') + 1,
                            'code': match.group().strip(),
                            'severity': 'HIGH'
                        })
                        
            except Exception as e:
                app_logger.warning(f"Could not scan {file_path}: {e}")
        
        return {
            'total_vulnerabilities': len(vulnerabilities),
            'vulnerabilities': vulnerabilities,
            'severity': 'HIGH' if vulnerabilities else 'LOW'
        }

    def scan_for_xss(self) -> Dict[str, Any]:
        """Scan for XSS vulnerabilities"""
        app_logger.info("🔍 Scanning for XSS vulnerabilities...")
        vulnerabilities = []
        
        scan_files = self._get_python_files() + self._get_js_files() + self._get_html_files()
        
        for file_path in scan_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in self.xss_patterns:
                    matches = pattern.finditer(content)
                    for match in matches:
                        vulnerabilities.append({
                            'type': 'XSS',
                            'file': file_path,
                            'line': content[:match.start()].count('\n') + 1,
                            'code': match.group().strip(),
                            'severity': 'MEDIUM'
                        })
                        
            except Exception as e:
                app_logger.warning(f"Could not scan {file_path}: {e}")
        
        return {
            'total_vulnerabilities': len(vulnerabilities),
            'vulnerabilities': vulnerabilities,
            'severity': 'MEDIUM' if vulnerabilities else 'LOW'
        }

    def scan_for_command_injection(self) -> Dict[str, Any]:
        """Scan for command injection vulnerabilities"""
        app_logger.info("🔍 Scanning for command injection vulnerabilities...")
        vulnerabilities = []
        
        python_files = self._get_python_files()
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in self.command_injection_patterns:
                    matches = pattern.finditer(content)
                    for match in matches:
                        vulnerabilities.append({
                            'type': 'Command Injection',
                            'file': file_path,
                            'line': content[:match.start()].count('\n') + 1,
                            'code': match.group().strip(),
                            'severity': 'HIGH'
                        })
                        
            except Exception as e:
                app_logger.warning(f"Could not scan {file_path}: {e}")
        
        return {
            'total_vulnerabilities': len(vulnerabilities),
            'vulnerabilities': vulnerabilities,
            'severity': 'HIGH' if vulnerabilities else 'LOW'
        }

    def check_dependencies(self) -> Dict[str, Any]:
        """Check for outdated or vulnerable dependencies"""
        app_logger.info("🔍 Checking dependencies for vulnerabilities...")
        
        issues = []
        
        # Check pyproject.toml for known vulnerable packages
        if os.path.exists('pyproject.toml'):
            try:
                with open('pyproject.toml', 'r') as f:
                    content = f.read()
                    
                # Known vulnerable patterns
                vulnerable_patterns = [
                    (r'flask<[12]\.\d+', 'Flask version may be outdated'),
                    (r'requests<2\.28', 'Requests version may have vulnerabilities'),
                    (r'pillow<8\.3', 'Pillow version may have vulnerabilities'),
                ]
                
                for pattern, message in vulnerable_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        issues.append({
                            'type': 'Outdated Dependency',
                            'message': message,
                            'severity': 'MEDIUM'
                        })
                        
            except Exception as e:
                app_logger.warning(f"Could not check pyproject.toml: {e}")
        
        return {
            'total_issues': len(issues),
            'issues': issues,
            'severity': 'MEDIUM' if issues else 'LOW'
        }

    def check_file_permissions(self) -> Dict[str, Any]:
        """Check file permissions for security issues"""
        app_logger.info("🔍 Checking file permissions...")
        
        issues = []
        sensitive_files = ['main.py', 'config.py', 'auth.py', 'database.py']
        
        for file_path in sensitive_files:
            if os.path.exists(file_path):
                stat_info = os.stat(file_path)
                permissions = oct(stat_info.st_mode)[-3:]
                
                if permissions[1] in ['7', '6']:  # Group writable
                    issues.append({
                        'type': 'File Permissions',
                        'file': file_path,
                        'permissions': permissions,
                        'message': 'File is group writable',
                        'severity': 'LOW'
                    })
                    
                if permissions[2] in ['7', '6']:  # World writable
                    issues.append({
                        'type': 'File Permissions',
                        'file': file_path,
                        'permissions': permissions,
                        'message': 'File is world writable',
                        'severity': 'MEDIUM'
                    })
        
        return {
            'total_issues': len(issues),
            'issues': issues,
            'severity': 'MEDIUM' if any(i['severity'] == 'MEDIUM' for i in issues) else 'LOW'
        }

    def check_environment_security(self) -> Dict[str, Any]:
        """Check environment configuration for security issues"""
        app_logger.info("🔍 Checking environment security...")
        
        issues = []
        
        # Check if debug mode is enabled
        if os.getenv('FLASK_ENV') == 'development' or os.getenv('DEBUG') == 'True':
            issues.append({
                'type': 'Debug Mode',
                'message': 'Debug mode should be disabled in production',
                'severity': 'MEDIUM'
            })
        
        # Check for missing security headers
        config_issues = self._check_security_config()
        issues.extend(config_issues)
        
        return {
            'total_issues': len(issues),
            'issues': issues,
            'severity': 'MEDIUM' if issues else 'LOW'
        }

    def _check_security_config(self) -> List[Dict[str, Any]]:
        """Check security configuration"""
        issues = []
        
        try:
            # Check if config.py has security settings
            if os.path.exists('config.py'):
                with open('config.py', 'r') as f:
                    content = f.read()
                    
                # Check for security headers
                if 'SECURITY_HEADERS' not in content:
                    issues.append({
                        'type': 'Missing Security Headers',
                        'message': 'Consider adding security headers configuration',
                        'severity': 'LOW'
                    })
                
                # Check for session security
                if 'SESSION_COOKIE_SECURE' not in content:
                    issues.append({
                        'type': 'Session Security',
                        'message': 'Consider enabling secure session cookies',
                        'severity': 'LOW'
                    })
                    
        except Exception as e:
            app_logger.warning(f"Could not check config security: {e}")
            
        return issues

    def _get_python_files(self) -> List[str]:
        """Get all Python files to scan"""
        python_files = []
        for root, dirs, files in os.walk('.'):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules']]
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        return python_files

    def _get_js_files(self) -> List[str]:
        """Get all JavaScript files to scan"""
        js_files = []
        for root, dirs, files in os.walk('./static/js'):
            for file in files:
                if file.endswith('.js'):
                    js_files.append(os.path.join(root, file))
        return js_files

    def _get_html_files(self) -> List[str]:
        """Get all HTML files to scan"""
        html_files = []
        for root, dirs, files in os.walk('./templates'):
            for file in files:
                if file.endswith('.html'):
                    html_files.append(os.path.join(root, file))
        return html_files

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate security scan summary"""
        return {
            'scan_completed': True,
            'timestamp': datetime.now().isoformat(),
            'total_vulnerabilities': len(self.vulnerabilities),
            'total_warnings': len(self.warnings),
            'recommendation': 'Review all HIGH severity issues before deployment'
        }

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate human-readable security report"""
        report = []
        report.append("=" * 60)
        report.append("🔒 SECURITY SCAN REPORT")
        report.append("=" * 60)
        report.append(f"Scan completed: {results['timestamp']}")
        report.append("")
        
        # Summary
        scan_results = results['scan_results']
        high_issues = 0
        medium_issues = 0
        
        for category, data in scan_results.items():
            if isinstance(data, dict) and 'severity' in data:
                if data['severity'] == 'HIGH':
                    high_issues += data.get('total_secrets_found', data.get('total_vulnerabilities', data.get('total_issues', 0)))
                elif data['severity'] == 'MEDIUM':
                    medium_issues += data.get('total_secrets_found', data.get('total_vulnerabilities', data.get('total_issues', 0)))
        
        report.append(f"🚨 HIGH SEVERITY ISSUES: {high_issues}")
        report.append(f"⚠️  MEDIUM SEVERITY ISSUES: {medium_issues}")
        report.append("")
        
        # Detailed results
        for category, data in scan_results.items():
            report.append(f"\n📊 {category.upper().replace('_', ' ')}")
            report.append("-" * 40)
            
            if isinstance(data, dict):
                if 'secrets' in data and data['secrets']:
                    for secret in data['secrets'][:5]:  # Show first 5
                        report.append(f"  🔑 {secret['type']} in {secret['file']}:{secret['line']}")
                elif 'vulnerabilities' in data and data['vulnerabilities']:
                    for vuln in data['vulnerabilities'][:5]:  # Show first 5
                        report.append(f"  ⚠️  {vuln['type']} in {vuln['file']}:{vuln['line']}")
                elif 'issues' in data and data['issues']:
                    for issue in data['issues'][:5]:  # Show first 5
                        report.append(f"  ⚠️  {issue.get('message', issue.get('type', 'Unknown issue'))}")
                else:
                    report.append(f"  ✅ No issues found")
        
        report.append("\n" + "=" * 60)
        report.append("🔧 RECOMMENDATIONS")
        report.append("=" * 60)
        
        if high_issues > 0:
            report.append("❌ DEPLOYMENT NOT RECOMMENDED")
            report.append("   Fix all HIGH severity issues before deploying")
        elif medium_issues > 0:
            report.append("⚠️  DEPLOYMENT WITH CAUTION")
            report.append("   Review MEDIUM severity issues")
        else:
            report.append("✅ DEPLOYMENT READY")
            report.append("   No critical security issues found")
        
        return "\n".join(report)


def run_security_scan():
    """Run security scan and return results"""
    scanner = SecurityScanner()
    results = scanner.scan_all()
    report = scanner.generate_report(results)
    
    # Save results
    with open('security_scan_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    with open('security_report.txt', 'w') as f:
        f.write(report)
    
    print(report)
    return results


if __name__ == "__main__":
    run_security_scan()
