#!/bin/bash

# Volatility Surface Explorer - Setup Script
# This script sets up the development environment and verifies installation

set -e  # Exit on error

echo "📈 Volatility Surface Explorer - Setup Script"
echo "=============================================="
echo ""

# Check Python version
echo "🔍 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "❌ Python 3.10+ required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python version OK: $PYTHON_VERSION"
echo ""

# Create virtual environment (optional but recommended)
echo "🔧 Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "ℹ️  Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✅ pip upgraded"
echo ""

# Install dependencies
echo "📚 Installing dependencies..."
echo "   This may take a few minutes..."
pip install -r requirements.txt > /dev/null 2>&1
echo "✅ All dependencies installed"
echo ""

# Verify key imports
echo "🧪 Verifying installations..."
python3 << EOF
import sys

packages = [
    ('streamlit', 'Streamlit'),
    ('pandas', 'pandas'),
    ('numpy', 'NumPy'),
    ('scipy', 'SciPy'),
    ('plotly', 'Plotly'),
    ('yfinance', 'yfinance'),
    ('sklearn', 'scikit-learn')
]

failed = []
for module, name in packages:
    try:
        __import__(module)
        print(f"✅ {name}")
    except ImportError:
        print(f"❌ {name} - FAILED")
        failed.append(name)

if failed:
    print(f"\n❌ Some packages failed to import: {', '.join(failed)}")
    sys.exit(1)
else:
    print("\n✅ All packages verified successfully!")
EOF

echo ""

# Create data directory if it doesn't exist
echo "📁 Setting up data directory..."
mkdir -p data
echo "✅ Data directory ready"
echo ""

# Test module imports
echo "🧪 Testing custom modules..."
python3 << EOF
import sys
sys.path.insert(0, '.')

try:
    from src import data_loader, greeks, surface_builder, strategy, visualizations
    print("✅ All custom modules imported successfully")
except ImportError as e:
    print(f"❌ Module import failed: {e}")
    sys.exit(1)
EOF

echo ""

# Display next steps
echo "=============================================="
echo "✨ Setup Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Activate the virtual environment (if not already active):"
echo "   source venv/bin/activate"
echo ""
echo "2. Run the application:"
echo "   streamlit run app.py"
echo ""
echo "3. Open your browser to:"
echo "   http://localhost:8501"
echo ""
echo "4. (Optional) Test individual modules:"
echo "   python -m src.data_loader"
echo "   python -m src.greeks"
echo "   python -m src.surface_builder"
echo ""
echo "For more information, see:"
echo "   - README.md (comprehensive documentation)"
echo "   - QUICKSTART.md (quick start guide)"
echo ""
echo "Happy trading! 📈"
echo ""

