# Report

## Converting to PDF

To convert `final_evaluation_report.md` to PDF **with images**:

```bash
# From project root
make report-pdf
# or
./report/convert_to_pdf.sh
```

- **If LaTeX is installed**: Produces `final_evaluation_report.pdf` directly.
- **If LaTeX is not installed**: Produces `final_evaluation_report.html`. Open it in a browser and use **File → Print → Save as PDF** — images will display correctly.

The script uses `--resource-path=.` so images in `images/` are found during conversion.
