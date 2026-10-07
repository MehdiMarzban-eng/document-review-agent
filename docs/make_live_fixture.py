"""Generate a fictional three-page PDF for a manual hosted smoke test."""
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

pages = [
    ["FICTIONAL DEVELOPMENT FIXTURE - NOT RESEARCH RESULTS",
     "Model C evaluation. Test set T-100 contains 100 simulated cases.",
     "Both reports describe the same model, test set, and metric.",
     "No production deployment or noise test was performed."],
    ["Method notes", "MAE denotes mean absolute localization error in metres.",
     "Latency is milliseconds per prediction on the same test machine.",
     "Results are on page 3. This page records definitions only."],
    ["Results for Model C on T-100", "Mean absolute error: 2.4 metres.",
     "Inference latency: 12 milliseconds.",
     "There is no erratum or revision priority in this report."],
]
out = Path(__file__).resolve().parent.parent / ".test-tmp"
out.mkdir(exist_ok=True)
writer = PdfWriter()
for lines in pages:
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):
        DictionaryObject({NameObject("/F1"): font})})
    stream = DecodedStreamObject()
    content = "BT /F1 11 Tf 48 730 Td 22 TL " + " ".join(
        f"({line}) Tj T*" for line in lines) + " ET"
    stream.set_data(content.encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
writer.write(out / "model-c-report.pdf")
(out / "model-c-audit.txt").write_text(
    "FICTIONAL DEVELOPMENT FIXTURE - NOT RESEARCH RESULTS\n"
    "Audit summary for Model C on test set T-100, the same 100 simulated cases.\n"
    "Mean absolute localization error: 3.1 metres.\n"
    "Inference latency: 12 milliseconds.\n"
    "No erratum, correction, or revision priority is supplied.\n", encoding="utf-8")
assert "2.4" in PdfReader(out / "model-c-report.pdf").pages[2].extract_text()
print(out)
