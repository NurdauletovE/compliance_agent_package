#!/usr/bin/env python3
"""
Compliance Agent Package Verification Script

This script verifies the integrity and completeness of the compliance agent package,
ensuring all required files are present and properly configured.
"""

import os
import sys
import json
import yaml
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Any

class PackageVerifier:
    def __init__(self, package_dir: str = "."):
        self.package_dir = Path(package_dir)
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_checks = 0
        
    def log_error(self, message: str):
        """Log an error message"""
        self.errors.append(f"❌ ERROR: {message}")
        
    def log_warning(self, message: str):
        """Log a warning message"""
        self.warnings.append(f"⚠️  WARNING: {message}")
        
    def log_success(self, message: str):
        """Log a success message"""
        self.success_count += 1
        print(f"✅ {message}")
        
    def check_file_exists(self, file_path: str, required: bool = True) -> bool:
        """Check if a file exists"""
        self.total_checks += 1
        full_path = self.package_dir / file_path
        
        if full_path.exists():
            self.log_success(f"File exists: {file_path}")
            return True
        else:
            if required:
                self.log_error(f"Required file missing: {file_path}")
            else:
                self.log_warning(f"Optional file missing: {file_path}")
            return False
            
    def check_file_executable(self, file_path: str) -> bool:
        """Check if a file is executable"""
        self.total_checks += 1
        full_path = self.package_dir / file_path
        
        if full_path.exists() and os.access(full_path, os.X_OK):
            self.log_success(f"File is executable: {file_path}")
            return True
        else:
            self.log_error(f"File is not executable: {file_path}")
            return False
            
    def check_directory_exists(self, dir_path: str, required: bool = True) -> bool:
        """Check if a directory exists"""
        self.total_checks += 1
        full_path = self.package_dir / dir_path
        
        if full_path.exists() and full_path.is_dir():
            self.log_success(f"Directory exists: {dir_path}")
            return True
        else:
            if required:
                self.log_error(f"Required directory missing: {dir_path}")
            else:
                self.log_warning(f"Optional directory missing: {dir_path}")
            return False
            
    def check_yaml_syntax(self, file_path: str) -> bool:
        """Check if a YAML file has valid syntax"""
        self.total_checks += 1
        full_path = self.package_dir / file_path
        
        if not full_path.exists():
            self.log_error(f"YAML file not found: {file_path}")
            return False
            
        try:
            with open(full_path, 'r') as f:
                yaml.safe_load(f)
            self.log_success(f"Valid YAML syntax: {file_path}")
            return True
        except yaml.YAMLError as e:
            self.log_error(f"Invalid YAML syntax in {file_path}: {e}")
            return False
            
    def check_python_syntax(self, file_path: str) -> bool:
        """Check if a Python file has valid syntax"""
        self.total_checks += 1
        full_path = self.package_dir / file_path
        
        if not full_path.exists():
            self.log_error(f"Python file not found: {file_path}")
            return False
            
        try:
            with open(full_path, 'r') as f:
                compile(f.read(), str(full_path), 'exec')
            self.log_success(f"Valid Python syntax: {file_path}")
            return True
        except SyntaxError as e:
            self.log_error(f"Invalid Python syntax in {file_path}: {e}")
            return False
            
    def check_dockerfile_syntax(self, file_path: str) -> bool:
        """Basic Dockerfile syntax check"""
        self.total_checks += 1
        full_path = self.package_dir / file_path
        
        if not full_path.exists():
            self.log_error(f"Dockerfile not found: {file_path}")
            return False
            
        try:
            with open(full_path, 'r') as f:
                content = f.read()
                
            # Basic checks - look for FROM instruction (ignore comments)
            lines = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]
            if not lines or not lines[0].startswith('FROM'):
                self.log_error(f"Dockerfile should have FROM as first non-comment instruction: {file_path}")
                return False
                
            required_instructions = ['FROM', 'WORKDIR', 'COPY', 'RUN']
            for instruction in required_instructions:
                if instruction not in content:
                    self.log_warning(f"Dockerfile missing {instruction} instruction: {file_path}")
                    
            self.log_success(f"Valid Dockerfile structure: {file_path}")
            return True
            
        except Exception as e:
            self.log_error(f"Error reading Dockerfile {file_path}: {e}")
            return False
            
    def check_requirements_format(self, file_path: str) -> bool:
        """Check if requirements.txt has valid format"""
        self.total_checks += 1
        full_path = self.package_dir / file_path
        
        if not full_path.exists():
            self.log_error(f"Requirements file not found: {file_path}")
            return False
            
        try:
            with open(full_path, 'r') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Basic package name validation
                    if not any(c.isalnum() or c in '-_.' for c in line.split('==')[0]):
                        self.log_warning(f"Suspicious package name in {file_path} line {i}: {line}")
                        
            self.log_success(f"Valid requirements format: {file_path}")
            return True
            
        except Exception as e:
            self.log_error(f"Error reading requirements file {file_path}: {e}")
            return False
            
    def check_environment_variables(self, file_path: str) -> bool:
        """Check environment file format"""
        self.total_checks += 1
        full_path = self.package_dir / file_path
        
        if not full_path.exists():
            self.log_warning(f"Environment file not found: {file_path}")
            return False
            
        try:
            with open(full_path, 'r') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' not in line:
                        self.log_warning(f"Invalid environment variable format in {file_path} line {i}: {line}")
                        
            self.log_success(f"Valid environment file format: {file_path}")
            return True
            
        except Exception as e:
            self.log_error(f"Error reading environment file {file_path}: {e}")
            return False
            
    def check_agent_configuration(self) -> bool:
        """Check agent.py configuration and imports"""
        self.total_checks += 1
        full_path = self.package_dir / "agent.py"
        
        if not full_path.exists():
            self.log_error("Agent main file not found: agent.py")
            return False
            
        try:
            with open(full_path, 'r') as f:
                content = f.read()
                
            # Check for required imports and classes
            required_elements = [
                'import asyncio',
                'import aiohttp',
                'import logging',
                'class OpenSCAPScanner',
                'class ComplianceAPIClient',
                'async def main'
            ]
            
            for element in required_elements:
                if element not in content:
                    self.log_warning(f"Missing expected element in agent.py: {element}")
                    
            self.log_success("Agent configuration appears valid")
            return True
            
        except Exception as e:
            self.log_error(f"Error analyzing agent.py: {e}")
            return False
            
    def check_docker_compose_config(self) -> bool:
        """Check docker-compose.yml configuration"""
        self.total_checks += 1
        full_path = self.package_dir / "docker-compose.yml"
        
        if not full_path.exists():
            self.log_error("Docker compose file not found: docker-compose.yml")
            return False
            
        try:
            with open(full_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Check basic structure
            if 'services' not in config:
                self.log_error("Docker compose missing 'services' section")
                return False
                
            if 'compliance-agent' not in config['services']:
                self.log_error("Docker compose missing 'compliance-agent' service")
                return False
                
            agent_service = config['services']['compliance-agent']
            
            # Check required fields
            required_fields = ['build', 'environment', 'ports', 'volumes']
            for field in required_fields:
                if field not in agent_service:
                    self.log_warning(f"Docker compose agent service missing: {field}")
                    
            self.log_success("Docker compose configuration appears valid")
            return True
            
        except Exception as e:
            self.log_error(f"Error analyzing docker-compose.yml: {e}")
            return False
            
    def check_deployment_script(self) -> bool:
        """Check deploy.sh script functionality"""
        self.total_checks += 1
        full_path = self.package_dir / "deploy.sh"
        
        if not full_path.exists():
            self.log_error("Deployment script not found: deploy.sh")
            return False
            
        try:
            with open(full_path, 'r') as f:
                content = f.read()
                
            # Check for required functions
            required_functions = [
                'deploy_agent',
                'stop_agent',
                'check_status',
                'show_logs'
            ]
            
            for func in required_functions:
                if func not in content:
                    self.log_warning(f"Deployment script missing function: {func}")
                    
            # Check for shebang
            if not content.startswith('#!/bin/bash'):
                self.log_warning("Deployment script missing bash shebang")
                
            self.log_success("Deployment script appears functional")
            return True
            
        except Exception as e:
            self.log_error(f"Error analyzing deploy.sh: {e}")
            return False
            
    def calculate_file_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file"""
        full_path = self.package_dir / file_path
        if not full_path.exists():
            return ""
            
        sha256_hash = hashlib.sha256()
        with open(full_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
        
    def generate_checksums(self) -> Dict[str, str]:
        """Generate checksums for all important files"""
        important_files = [
            "agent.py",
            "Dockerfile",
            "docker-compose.yml",
            "deploy.sh",
            "requirements.txt",
            "config/agent.yaml"
        ]
        
        checksums = {}
        for file_path in important_files:
            checksum = self.calculate_file_checksum(file_path)
            if checksum:
                checksums[file_path] = checksum
                
        return checksums
        
    def verify_package(self) -> bool:
        """Run complete package verification"""
        print("🔍 Starting Compliance Agent Package Verification...")
        print("=" * 60)
        
        # Check required files
        print("\n📁 Checking Required Files:")
        self.check_file_exists("agent.py")
        self.check_file_exists("Dockerfile")
        self.check_file_exists("docker-compose.yml")
        self.check_file_exists("deploy.sh")
        self.check_file_exists("requirements.txt")
        self.check_file_exists("README.md")
        
        # Check optional files
        print("\n📋 Checking Optional Files:")
        self.check_file_exists("INSTALLATION_GUIDE.md", required=False)
        self.check_file_exists("PACKAGE_SUMMARY.md", required=False)
        self.check_file_exists(".env.example", required=False)
        self.check_file_exists("setup.sh", required=False)
        
        # Check directories
        print("\n📂 Checking Directories:")
        self.check_directory_exists("config")
        self.check_directory_exists("logs", required=False)
        self.check_directory_exists("results", required=False)
        
        # Check configuration files
        print("\n⚙️  Checking Configuration Files:")
        self.check_yaml_syntax("docker-compose.yml")
        self.check_yaml_syntax("config/agent.yaml")
        self.check_environment_variables(".env.example")
        
        # Check executable permissions
        print("\n🔐 Checking Permissions:")
        self.check_file_executable("deploy.sh")
        
        # Check syntax and structure
        print("\n🔧 Checking Syntax and Structure:")
        self.check_python_syntax("agent.py")
        self.check_dockerfile_syntax("Dockerfile")
        self.check_requirements_format("requirements.txt")
        
        # Check configuration validity
        print("\n🔍 Checking Configuration Validity:")
        self.check_agent_configuration()
        self.check_docker_compose_config()
        self.check_deployment_script()
        
        # Generate checksums
        print("\n🔒 Generating File Checksums:")
        checksums = self.generate_checksums()
        checksum_file = self.package_dir / "CHECKSUMS.json"
        with open(checksum_file, 'w') as f:
            json.dump(checksums, f, indent=2)
        self.log_success(f"Generated checksums file: CHECKSUMS.json")
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 60)
        
        success_rate = (self.success_count / self.total_checks * 100) if self.total_checks > 0 else 0
        print(f"✅ Successful checks: {self.success_count}/{self.total_checks} ({success_rate:.1f}%)")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")
                
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")
            print("\n🚨 Package verification FAILED - please fix the errors above")
            return False
        else:
            print("\n🎉 Package verification PASSED - all critical checks successful!")
            if self.warnings:
                print("⚠️  Note: Some warnings were found - review them for optimization")
            return True

def main():
    """Main verification function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify Compliance Agent Package")
    parser.add_argument("--package-dir", "-d", default=".", 
                       help="Package directory to verify (default: current directory)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Set up logging
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO)
    
    # Run verification
    verifier = PackageVerifier(args.package_dir)
    success = verifier.verify_package()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
