# Slides

One folder per deck. Each has the LaTeX source, the compiled PDF, the PowerPoint
version and the script that generates the PowerPoint.

| Folder | Deck | Slides |
|---|---|---|
| [01_rtl_overview/](01_rtl_overview/) | RTL of the accelerator: components, values, how data moves file to file | 24 |
| [02_models_cosim/](02_models_cosim/) | Software models (NumPy, C++, SystemC) and Verilator co-simulation: why and how | 33 |

`slide_kit.py` holds the shared colours and drawing helpers used by the PowerPoint generators.

## Rebuild

```bash
# PDF (LaTeX)
cd docs/slides/01_rtl_overview && tectonic rtl_overview.tex      # or pdflatex, run twice
cd docs/slides/02_models_cosim && tectonic models_cosim.tex

# PowerPoint
pip install python-pptx
python docs/slides/01_rtl_overview/make_rtl_pptx.py
python docs/slides/02_models_cosim/make_models_pptx.py
```
