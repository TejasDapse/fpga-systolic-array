# Slides

One folder per deck. Each has the LaTeX source, the compiled PDF, the PowerPoint
version and the script that generates the PowerPoint.

| Folder | Deck | Slides |
|---|---|---|
| [01_rtl_overview/](01_rtl_overview/) | RTL of the accelerator: components, values, how data moves file to file | 24 |
| [02_models_cosim/](02_models_cosim/) | Software models (NumPy, C++, SystemC) and Verilator co-simulation: why and how | 33 |
| [03_pe_basics/](03_pe_basics/) | The processing element for beginners: what it does, inside view, rules, bit widths, signed, timing example, code (LaTeX + PDF) | 13 |
| [04_array4x4_max10/](04_array4x4_max10/) | A 4×4 array on Intel MAX 10: combinational vs sequential logic in every block, LEs and LABs, timing, and one value followed end to end from the PC to the PEs and back (LaTeX + PDF) | 38 |

`slide_kit.py` holds the shared colours and drawing helpers used by the PowerPoint generators.

## Rebuild

```bash
# PDF (LaTeX)
cd docs/slides/01_rtl_overview && tectonic rtl_overview.tex      # or pdflatex, run twice
cd docs/slides/02_models_cosim && tectonic models_cosim.tex
cd docs/slides/03_pe_basics && tectonic pe_basics.tex
cd docs/slides/04_array4x4_max10 && tectonic array4x4_max10.tex

# PowerPoint
pip install python-pptx
python docs/slides/01_rtl_overview/make_rtl_pptx.py
python docs/slides/02_models_cosim/make_models_pptx.py
```
