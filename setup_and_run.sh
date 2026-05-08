#!/bin/bash
# Phase 2 RAG System - Automated Setup and Evaluation
# This script sets up a virtual environment and runs the evaluation

set -e  # Exit on error

echo "=========================================="
echo "Phase 2 RAG System - Automated Setup"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r repo/requirements.txt
# Ensure we have a recent openai version (some systems cache old versions)
pip install -q --upgrade openai
echo "✅ All dependencies installed"

# Check for .env file
echo ""
if [ ! -f ".env" ]; then
    echo "⚠️  WARNING: .env file not found!"
    echo "   Please create .env with your OPENAI_API_KEY"
    echo "   Example: OPENAI_API_KEY=sk-..."
    echo ""
    read -p "Press Enter to continue anyway (will fail if API key needed)..."
else
    echo "✅ .env file found"
fi

# Run evaluation
echo ""
echo "=========================================="
echo "🚀 Running Evaluation (25 queries)"
echo "=========================================="
echo ""

python src/eval/run_evaluation.py

echo ""
echo "=========================================="
echo "✅ Evaluation Complete!"
echo "=========================================="
echo ""
echo "📊 Results saved to: outputs/evaluation_results_*.json"
echo "📄 Full report: report/final_evaluation_report.md"
echo ""
