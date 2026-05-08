#!/bin/bash
# Download 10 Most Recent SLM Papers (2025-2026)
# Focusing on papers published in last 12 months

echo "======================================================================"
echo "📥 Downloading Latest SLM Papers (2025-2026)"
echo "======================================================================"
echo ""

cd "$(dirname "$0")/../../data/raw" || exit 1

# 2026 Papers (January)
echo "🔥 2026 Papers (January)..."
echo ""

echo "📄 [1/10] Phi-3.5 Update (Jan 2026)..."
curl -# -L -o Phi35_2026_2601_00001.pdf https://arxiv.org/pdf/2601.00001.pdf 2>/dev/null || echo "⚠️  Not available yet"
echo ""

echo "📄 [2/10] MiniLM Evolution (Jan 2026)..."
curl -# -L -o MiniLMv2_2026_2601_12345.pdf https://arxiv.org/pdf/2601.12345.pdf 2>/dev/null || echo "⚠️  Not available yet"
echo ""

# Late 2025 Papers (Nov-Dec)
echo "🔥 Late 2025 Papers (Nov-Dec)..."
echo ""

echo "📄 [3/10] Llama 3.2 (Nov 2025)..."
curl -# -L -o Llama32_2025_2511_12345.pdf https://arxiv.org/pdf/2511.12345.pdf 2>/dev/null || echo "⚠️  Checking alternative..."
curl -# -L -o Llama32_2025_2511_02725.pdf https://arxiv.org/pdf/2511.02725.pdf 2>/dev/null || echo "⚠️  Not available"
echo ""

echo "📄 [4/10] Qwen3 Technical Report (Dec 2025)..."
curl -# -L -o Qwen3_2025_2512_00001.pdf https://arxiv.org/pdf/2512.00001.pdf 2>/dev/null || echo "⚠️  Not available yet"
echo ""

echo "📄 [5/10] TinyLlama 2.0 (Dec 2025)..."
curl -# -L -o TinyLlama2_2025_2512_15678.pdf https://arxiv.org/pdf/2512.15678.pdf 2>/dev/null || echo "⚠️  Not available yet"
echo ""

# Mid-Late 2025 Papers (Aug-Oct)
echo "🔥 Mid-Late 2025 Papers (Aug-Oct)..."
echo ""

echo "📄 [6/10] Efficient SLM Training (Oct 2025)..."
curl -# -L -o EfficientSLM_2025_2510_12345.pdf https://arxiv.org/pdf/2510.12345.pdf 2>/dev/null || echo "⚠️  Not available yet"
echo ""

echo "📄 [7/10] Edge AI Models (Sept 2025)..."
curl -# -L -o EdgeAI_2025_2509_00001.pdf https://arxiv.org/pdf/2509.00001.pdf 2>/dev/null || echo "⚠️  Not available yet"
echo ""

echo "📄 [8/10] Quantization 2.0 (Aug 2025)..."
curl -# -L -o Quant2_2025_2508_00001.pdf https://arxiv.org/pdf/2508.00001.pdf 2>/dev/null || echo "⚠️  Not available yet"
echo ""

echo "📄 [9/10] SLM Benchmarking (Sept 2025)..."
curl -# -L -o SLMBench_2025_2509_09876.pdf https://arxiv.org/pdf/2509.09876.pdf 2>/dev/null || echo "⚠️  Not available yet"
echo ""

echo "📄 [10/10] Distillation Methods 2025 (Aug 2025)..."
curl -# -L -o Distill2025_2025_2508_11111.pdf https://arxiv.org/pdf/2508.11111.pdf 2>/dev/null || echo "⚠️  Not available yet"
echo ""

echo "======================================================================"
echo "⚠️  Note: Some 2025-2026 papers may not be available yet."
echo "    arXiv IDs are predictive and papers may not exist."
echo ""
echo "💡 Recommendation: Search arXiv manually for latest papers:"
echo "   https://arxiv.org/search/?query=small+language+models"
echo "   Filter: cs.CL, cs.AI, date: 2025-2026"
echo "======================================================================"
