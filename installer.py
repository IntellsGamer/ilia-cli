#!/usr/bin/env python3
"""
APD CLI Installer - Python Version
Converts the original batch installer to Python
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_initial_files():
    """Check if required initial CLI files exist"""
    current_dir = Path.cwd()
    
    # Check for both required files
    required_files = ['apd.bat', 'schematic_deploy.py']
    missing_files = []
    
    for file in required_files:
        if not (current_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("Could not find initial CLI files to set up.")
        print(f"Missing: {', '.join(missing_files)}")
        print()
        input("Press Enter to exit...")
        return False
    return True

def check_existing_installation():
    """Check if CLI is already installed or needs cleanup"""
    install_dir = Path(os.getenv('APPDATA')) / 'APD'
    
    if install_dir.exists():
        config_file = install_dir / 'available.inf'
        
        if not config_file.exists():
            # Corrupted installation - try to remove
            try:
                shutil.rmtree(install_dir)
                if install_dir.exists():
                    print("Another instance of the CLI is installed incorrectly")
                    print("and we couldn't automatically fix the issue.")
                    print()
                    input("Press Enter to exit...")
                    return False
            except Exception as e:
                print(f"Error removing corrupted installation: {e}")
                print()
                input("Press Enter to exit...")
                return False
        else:
            print("The CLI is already installed.")
            print()
            input("Press Enter to exit...")
            return False
    
    return True

def install_cli():
    """Install the CLI files to appropriate locations"""
    current_dir = Path.cwd()
    user_home = Path.home()
    install_dir = Path(os.getenv('APPDATA')) / 'APD'
    
    try:
        # Set window title
        os.system('title Schematic Deploy - Installer')
        
        # Copy apd.bat to user home
        APD_bat_src = current_dir / 'apd.bat'
        APD_bat_dst = user_home / 'apd.bat'
        shutil.copy2(APD_bat_src, APD_bat_dst)
        print(f"✅ Copied apd.bat to: {user_home}")
        
        # Copy schematic_deploy.py to user home
        deploy_src = current_dir / 'schematic_deploy.py'
        deploy_dst = user_home / 'schematic_deploy.py'
        shutil.copy2(deploy_src, deploy_dst)
        print(f"✅ Copied schematic_deploy.py to: {user_home}")
        
        # Create templates directory structure
        templates_src = current_dir / 'templates'
        templates_dst = install_dir / 'templates'
        
        # Create directories
        install_dir.mkdir(parents=True, exist_ok=True)
        templates_dst.mkdir(parents=True, exist_ok=True)
        
        # Copy templates
        if templates_src.exists():
            shutil.copytree(templates_src, templates_dst, dirs_exist_ok=True)
            print(f"✅ Copied templates to: {templates_dst}")
        else:
            print(f"⚠️  Templates directory not found at {templates_src}")
            # Create empty templates directory
            (templates_dst / 'html').mkdir(parents=True, exist_ok=True)
            (templates_dst / 'flask').mkdir(parents=True, exist_ok=True)
            print("✅ Created empty template directories")
        
        # Handle available.inf file
        available_src = templates_dst / 'available.inf'
        available_dst = install_dir / 'available.inf'
        
        if available_src.exists():
            available_src.rename(available_dst)
        else:
            # Create available.inf if it doesn't exist
            with open(available_dst, 'w') as f:
                f.write("# Configuration file - do not delete\n")
                f.write(f"install_date={subprocess.getoutput('date /t')}")
        
        print("\n✅ Successfully installed APD CLI!")
        print("\n📋 Installed files:")
        print(f"  • {user_home}/apd.bat")
        print(f"  • {user_home}/schematic_deploy.py")
        print(f"  • {install_dir}/ (configuration)")
        
        print("\n🚀 Try opening a folder and running: APD --setup")
        print()
        print(f'💡 If "APD" command doesn\'t work, add "{user_home}" to PATH')
        print('   or run: python schematic_deploy.py --setup')
        print()
        input("Press Enter to exit...")
        
    except PermissionError:
        print("❌ Permission denied. Please run as administrator.")
        print()
        input("Press Enter to exit...")
        return False
    except Exception as e:
        print(f"❌ Installation error: {e}")
        print()
        input("Press Enter to exit...")
        return False
    
    return True

def main():
    """Main installer function"""
    print("=== APD CLI Installer ===")
    print()
    
    # Check initial files
    if not check_initial_files():
        return
    
    # Check existing installation
    if not check_existing_installation():
        return
    
    # Proceed with installation
    if install_cli():
        print("\n🎉 Installation completed successfully!")
    else:
        print("\n❌ Installation failed.")

if __name__ == "__main__":
    main()