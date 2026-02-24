# Installing Latest Python on macOS

You currently have Python 3.9.6, but the Jira library requires Python >= 3.10. Here are the steps to install the latest Python version.

## Option 1: Using Homebrew (Recommended)

### Step 1: Fix Homebrew Permissions
```bash
sudo chown -R $(whoami) /opt/homebrew/Cellar
```

### Step 2: Install Python 3.12 (Latest Stable)
```bash
brew update
brew install python@3.12
brew link --overwrite python@3.12
```

### Step 3: Verify Installation
```bash
python3.12 --version
```

### Step 4: Make it Default (Optional)
Add to your `~/.zshrc`:
```bash
export PATH="/opt/homebrew/opt/python@3.12/bin:$PATH"
```

Then reload:
```bash
source ~/.zshrc
```

## Option 2: Using the Installer Script

Run the provided script:
```bash
./install_python.sh
```

## Option 3: Download from python.org

1. Visit https://www.python.org/downloads/
2. Download the latest Python 3.12.x installer for macOS
3. Run the installer
4. Follow the installation wizard

## After Installation

1. Verify the installation:
   ```bash
   python3 --version
   # Should show Python 3.12.x or higher
   ```

2. Install project dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

3. Run the Jira tool:
   ```bash
   python3 main.py
   ```

## Troubleshooting

- If `python3` still shows 3.9.6, use `python3.12` explicitly
- Make sure your PATH includes the new Python installation
- You may need to recreate your virtual environment if using one
