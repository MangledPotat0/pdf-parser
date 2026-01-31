# Parser Comparison

This document compares the output quality of different PDF parsers on the "Attention is All You Need" paper.

## Test Paper
- **Title:** Attention is All You Need
- **Authors:** Vaswani et al. (2017)
- **Source:** NIPS 2017
- **Pages:** 11
- **Content:** Dense with equations, tables, and figures

## Results

### pdfplumber Parser (Standard)
**Processing Time:** ~1 second  
**File Size:** 25KB  
**GPU Required:** No

**Equation Quality Example:**
```
Attention(Q, K, V) = softmax(QK^T/√dk)V
```
❌ Lost formatting - no subscripts, no proper LaTeX

**Pros:**
- Very fast
- Works on any machine
- Good structure detection
- Generates BibTeX metadata

**Cons:**
- Equations rendered as plain text
- Subscripts/superscripts lost
- Complex math notation breaks

---

### olmOCR Parser (Multi-GPU)
**Processing Time:** ~30 seconds (11 pages)  
**File Size:** 39KB  
**GPU Required:** Yes (2x 16GB or 1x 24GB+)

**Equation Quality Example:**
```latex
\[
\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V
\]
```
✅ Perfect LaTeX formatting - ready for direct use

**More Examples:**
- Inline: `\( h_t \)`, `\( d_{\text{model}} = 512 \)`
- Block equations with proper alignment
- Complex notation: `\( W_i^Q \in \mathbb{R}^{d_{\text{model}} \times d_k} \)`

**Pros:**
- Excellent equation quality
- Proper LaTeX formatting
- Table structure preserved
- Figure detection
- Multi-GPU automatic distribution

**Cons:**
- Requires powerful GPU(s)
- First run downloads 15GB model
- Slower than pdfplumber
- Needs Hugging Face account

---

## Recommendation

**For quick extraction or no GPU:**
→ Use **pdfplumber parser** (standard)

**For papers with heavy math/equations:**
→ Use **olmOCR parser** if you have the hardware

**For production at scale:**
→ Consider using both:
  1. pdfplumber for metadata/BibTeX
  2. olmOCR for equation-heavy papers

---

## Hardware Tested

### Configuration
- **GPUs:** 2x NVIDIA RTX 4060 Ti (16GB each)
- **CPU:** 12-thread processor
- **RAM:** System RAM usage minimal (~2GB)

### olmOCR GPU Distribution
```
GPU 0 (16GB): Visual encoder + Language layers 0-10
GPU 1 (16GB): Language layers 11-27 + Output head
```

Memory usage balanced across both GPUs (~8GB each during inference).

---

## Sample Output

See `/output/NIPS-2017-attention-is-all-you-need-Paper_olmocr.md` for full olmOCR output.

Key sections demonstrating quality:
- Line 101-103: Scaled dot-product attention equation
- Line 117-122: Multi-head attention equations
- Line 140-142: Feed-forward network equation
- Line 158-189: Complexity comparison table
- Line 195-200: Positional encoding equations
