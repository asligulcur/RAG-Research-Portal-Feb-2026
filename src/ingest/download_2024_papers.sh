#!/bin/bash
# Download 4 Most Recent SLM Papers (2024)

echo "======================================================================"
echo "📥 Downloading Recent SLM Papers (2024)"
echo "======================================================================"
echo ""

cd "$(dirname "$0")/../../data/raw" || exit 1

echo "📄 [1/4] Qwen2.5 (September 2024)..."
curl -# -L -o Qwen25_2024_2409_12186.pdf https://arxiv.org/pdf/2409.12186.pdf
echo "✅ Downloaded Qwen2.5"
echo ""

echo "📄 [2/4] SmolLM (October 2024)..."
curl -# -L -o SmolLM_2024_2410_16678.pdf https://arxiv.org/pdf/2410.16678.pdf
echo "✅ Downloaded SmolLM"
echo ""

echo "📄 [3/4] MiniCPM (April 2024)..."
curl -# -L -o MiniCPM_2024_2404_06395.pdf https://arxiv.org/pdf/2404.06395.pdf
echo "✅ Downloaded MiniCPM"
echo ""

echo "📄 [4/4] Gemma 2 (August 2024)..."
curl -# -L -o Gemma2_2024_2408_00118.pdf https://arxiv.org/pdf/2408.00118.pdf
echo "✅ Downloaded Gemma 2"
echo ""

echo "======================================================================"
echo "✅ Downloaded 4 recent papers"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Check the PDFs in data/raw/"
echo "  2. Add these 4 papers to data/data_manifest.csv:"
echo ""
echo "     Qwen25_2024,Qwen2.5: A Party of Foundation Models,..."
echo "     SmolLM_2024,SmolLM: Blazingly Fast Small LM,..."
echo "     MiniCPM_2024,MiniCPM: Unveiling Small LM Potential,..."
echo "     Gemma2_2024,Gemma 2: Improving Open LMs,..."
echo ""
echo "  3. (Optional) Remove older versions:"
echo "     - Qwen_2023"
echo "     - Gemma_2024 (first version)"
echo ""
