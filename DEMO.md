# Equation and Figure Extraction Demo

This demonstrates the improvements made to the olmOCR parser.

## ✅ Equation Formatting (NEW)

### Before (LaTeX syntax)
```
\[ \text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V \]

Inline: \( h_t \), \( d_{\text{model}} = 512 \)
```

**Problem:** Doesn't render in standard markdown viewers

### After (Markdown syntax)
```
$$ \text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V $$

Inline: $ h_t $, $ d_{\text{model}} = 512 $
```

**Result:** ✅ Renders beautifully in GitHub, VS Code, Obsidian, etc.

---

## ✅ Figure Extraction (NEW)

### What It Does
1. **Saves all pages as PNG images** in `{pdf_name}_figures/` directory
2. **Detects pages with figures** (searches for "Figure N:" in text)
3. **Automatically links** figure images in the markdown

### Example Output Structure
```
output/
├── NIPS-2017-attention-is-all-you-need-Paper_olmocr.md
└── NIPS-2017-attention-is-all-you-need-Paper_figures/
    ├── page_1.png  (444 KB - Title page)
    ├── page_2.png  (620 KB)
    ├── page_3.png  (377 KB - Contains Figure 1: Transformer architecture)
    ├── page_4.png  (428 KB - Contains Figure 2: Attention mechanisms)
    ├── page_5.png  (481 KB)
    ├── ...
    └── page_11.png (420 KB)
```

### In the Markdown File
Pages with figures automatically get image references:

```markdown
# 3 Model Architecture

[...text content...]

![Page 3 - Contains figure](NIPS-2017-attention-is-all-you-need-Paper_figures/page_3.png)

---

[...next page...]
```

---

## Sample Output Quality

### Inline Equations
```markdown
They generate a sequence of hidden states $ h_t $, as a function 
of the previous hidden state $ h_{t-1} $ and the input for position $ t $.
```

Renders as: They generate a sequence of hidden states $h_t$, as a function of the previous hidden state $h_{t-1}$ and the input for position $t$.

### Block Equations
```markdown
$$
\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V
$$
```

Renders as centered, formatted equation.

### Multi-line Equations
```markdown
$$
\text{MultiHead}(Q, K, V) = \text{Concat}(\text{head}_1, ..., \text{head}_h) W^O \\
\text{where } \text{head}_i = \text{Attention}(QW_i^Q, KW_i^K, VW_i^V)
$$
```

Renders with proper alignment and line breaks.

---

## Processing Summary (Test Paper)

**Paper:** "Attention is All You Need" (Vaswani et al., 2017)  
**Pages:** 11  
**Processing time:** ~30 seconds on 2x RTX 4060 Ti

**Output:**
- ✅ 1 markdown file (39 KB) with proper equation syntax
- ✅ 11 PNG images (total ~5.4 MB)
- ✅ 2 figure pages detected and linked (pages 3 and 4)
- ✅ All equations converted to markdown syntax
- ✅ Tables preserved in markdown format

---

## Use Cases

### 1. **Research Paper Repository**
Extract papers to markdown for version control, full-text search, and easy reading.

### 2. **Note-Taking in Obsidian/Notion**
Import academic papers with proper math rendering in your knowledge base.

### 3. **Documentation**
Convert technical PDFs to markdown for inclusion in documentation sites.

### 4. **Figure Extraction**
Get high-quality page images for presentations or further processing.

---

## Compatibility

Equations render correctly in:
- ✅ GitHub markdown
- ✅ VS Code markdown preview
- ✅ Obsidian
- ✅ Notion (via LaTeX blocks)
- ✅ Jupyter notebooks
- ✅ MkDocs
- ✅ Hugo
- ✅ Jekyll

Figure images work in all markdown viewers that support relative paths.
