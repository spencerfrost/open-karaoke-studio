#!/bin/bash
# Installation script for Unix/Linux/macOS systems

# Check if Python 3.8+ is available
python3 --version >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ $PYTHON_MAJOR -lt 3 ] || ([ $PYTHON_MAJOR -eq 3 ] && [ $PYTHON_MINOR -lt 8 ]); then
    echo "Python 3.8 or higher is required. You have Python $PYTHON_VERSION"
    exit 1
fi

# Create a virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies with requirements.txt (includes the demucs fork)
echo "Installing dependencies (this may take a while)..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Installation complete!"
echo ""
echo "To start the application:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run the application: python main.py"
echo ""
echo "To exit the virtual environment when done: deactivate"
