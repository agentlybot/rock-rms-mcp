#!/bin/bash
# Rock RMS MCP Setup Script for Grace Church Staff
# Run this in Terminal: bash setup-for-user.sh

echo ""
echo "==================================================="
echo "  Rock RMS MCP Setup for Claude Desktop"
echo "  Grace Church Pelham - Children's Ministry"
echo "==================================================="
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed."
    echo "Please install it from: https://www.python.org/downloads/"
    echo "Then re-run this script."
    exit 1
fi

echo "Python 3 found: $(python3 --version)"
echo ""

# Install the MCP package
echo "Installing Rock RMS MCP server..."
pip3 install --user git+https://github.com/agentlybot/rock-rms-mcp.git 2>&1
echo ""

if [ $? -ne 0 ]; then
    echo "Installation failed. Please contact Jon for help."
    exit 1
fi

echo "Installation successful!"
echo ""

# Get Rock RMS credentials
echo "---------------------------------------------------"
echo "Enter your Rock RMS login credentials."
echo "(These are saved locally on your computer only.)"
echo "---------------------------------------------------"
echo ""
read -p "Rock RMS Username: " ROCK_USER
read -sp "Rock RMS Password: " ROCK_PASS
echo ""
echo ""

# Find Claude Desktop config location
CONFIG_DIR="$HOME/Library/Application Support/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

if [ ! -d "$CONFIG_DIR" ]; then
    echo "Claude Desktop config folder not found."
    echo "Make sure Claude Desktop is installed and has been opened at least once."
    echo "Download it from: https://claude.ai/download"
    echo ""
    echo "After installing and opening Claude Desktop once, re-run this script."
    exit 1
fi

# Find the python3 path for the config
PYTHON_PATH=$(which python3)

# Create or update config
if [ -f "$CONFIG_FILE" ]; then
    # Config exists — check if it already has mcpServers
    if python3 -c "import json; d=json.load(open('$CONFIG_FILE')); exit(0 if 'mcpServers' in d else 1)" 2>/dev/null; then
        # Add to existing mcpServers
        python3 -c "
import json
with open('$CONFIG_FILE') as f:
    config = json.load(f)
config['mcpServers']['rock-rms'] = {
    'command': '$PYTHON_PATH',
    'args': ['-m', 'rock_rms_mcp'],
    'env': {
        'ROCK_USERNAME': '$ROCK_USER',
        'ROCK_PASSWORD': '$ROCK_PASS'
    }
}
with open('$CONFIG_FILE', 'w') as f:
    json.dump(config, f, indent=2)
"
    else
        # Add mcpServers key
        python3 -c "
import json
with open('$CONFIG_FILE') as f:
    config = json.load(f)
config['mcpServers'] = {
    'rock-rms': {
        'command': '$PYTHON_PATH',
        'args': ['-m', 'rock_rms_mcp'],
        'env': {
            'ROCK_USERNAME': '$ROCK_USER',
            'ROCK_PASSWORD': '$ROCK_PASS'
        }
    }
}
with open('$CONFIG_FILE', 'w') as f:
    json.dump(config, f, indent=2)
"
    fi
else
    # Create new config
    python3 -c "
import json
config = {
    'mcpServers': {
        'rock-rms': {
            'command': '$PYTHON_PATH',
            'args': ['-m', 'rock_rms_mcp'],
            'env': {
                'ROCK_USERNAME': '$ROCK_USER',
                'ROCK_PASSWORD': '$ROCK_PASS'
            }
        }
    }
}
with open('$CONFIG_FILE', 'w') as f:
    json.dump(config, f, indent=2)
"
fi

echo ""
echo "==================================================="
echo "  Setup Complete!"
echo "==================================================="
echo ""
echo "Next steps:"
echo "  1. Quit Claude Desktop completely (right-click the"
echo "     icon in your menu bar and click Quit)"
echo "  2. Re-open Claude Desktop"
echo "  3. Start asking questions like:"
echo ""
echo '     "How many kids checked in last Sunday at 9am?"'
echo '     "Show me who was in Kerplunk on March 8"'
echo '     "Search for the Smith family"'
echo ""
echo "If you see a hammer icon in the bottom-right of the"
echo "Claude chat window, the connection is working!"
echo ""
echo "Questions? Contact Jon at jon@scopestack.io"
echo ""
