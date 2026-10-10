"""Generate fictional development fixtures; not a held-out benchmark."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.pagesizes import letter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf"
OUT.mkdir(parents=True, exist_ok=True)
STYLES = getSampleStyleSheet()
STYLES.add(ParagraphStyle(name="BodyCustom", fontName="Helvetica", fontSize=11, leading=17, spaceAfter=12, textColor=colors.HexColor("#17243b")))
STYLES.add(ParagraphStyle(name="TitleCustom", fontName="Helvetica-Bold", fontSize=23, leading=29, spaceAfter=18, textColor=colors.HexColor("#17243b")))
STYLES.add(ParagraphStyle(name="SubCustom", fontName="Helvetica-Bold", fontSize=14, leading=19, spaceAfter=12, textColor=colors.HexColor("#2861c9")))


def p(text):
    return Paragraph(text, STYLES["BodyCustom"])


def table(rows):
    result = Table([[p(cell) for cell in row] for row in rows], colWidths=[215, 253], hAlign="LEFT")
    result.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eaf0fa")), ("VALIGN",(0,0),(-1,-1),"TOP"), ("LEFTPADDING",(0,0),(-1,-1),12), ("RIGHTPADDING",(0,0),(-1,-1),12), ("TOPPADDING",(0,0),(-1,-1),10), ("BOTTOMPADDING",(0,0),(-1,-1),6), ("LINEBELOW",(0,0),(-1,-1),.5,colors.HexColor("#d6dfed"))]))
    return result


def footer(canvas, doc):
    canvas.setFont("Helvetica",9)
    canvas.setFillColor(colors.HexColor("#60718b"))
    canvas.drawString(72,34,"FICTIONAL TEST DOCUMENT | Document Review Agent")
    canvas.drawRightString(540,34,f"Page {doc.page}")


def pdf(name, pages):
    flow=[]
    for index,(title,items) in enumerate(pages):
        if index: flow.append(PageBreak())
        flow.append(Paragraph(title,STYLES["TitleCustom"]))
        for item in items:
            flow.append(table(item) if isinstance(item,list) else p(item))
    SimpleDocTemplate(str(OUT/name),pagesize=letter,rightMargin=72,leftMargin=72,topMargin=60,bottomMargin=60).build(flow,onFirstPage=footer,onLaterPages=footer)


pdf("01_Baseline_Report.pdf",[
    ("RiverWatch: Baseline A",[
        "Evaluation report | 5 September 2026 | Fictional development fixture",
        "<b>Purpose.</b> Estimate the location of a simulated pipeline leak from pressure measurements. All experiments are simulations; no live pipeline or field pilot is included.",
        "<b>Dataset.</b> There are 600 simulated cases: 420 training, 90 validation and 90 held-out test cases. The final test set is named RW-90. The baseline and candidate reports use the same RW-90 test cases.",
        "<b>Conditions.</b> Water at 20-24 degrees Celsius, one leak per case and complete sensor readings. Sampling frequency is 10 Hz. No artificial measurement noise or sensor outages were introduced.",
        "Exact processor, RAM, GPU and operating-system details were not recorded. Timing was measured on the same bench workstation for both models."]),
    ("Baseline A: results",[
        "Final results on the 90 held-out RW-90 cases:",
        [["Measure","Baseline A"],["Location error (RMSE)","0.84 metres"],["Mean prediction latency","180 milliseconds"],["95th-percentile latency","240 milliseconds"],["Held-out cases","90"]],
        "RMSE describes aggregate location error. Mean latency and 95th-percentile latency are different measures; they should not be substituted for one another.",
        "No confidence interval, statistical-significance test or per-case error distribution is supplied. These results alone do not establish that a difference is statistically significant."]),
    ("Baseline A: limitations",[
        "No tests of sensor failure, measurement noise, multiple simultaneous leaks or hydrogen service were conducted.",
        "No independent laboratory test, field pilot or operational deployment is reported. The report makes no claim of deployment readiness.",
        "Apply the separate RiverWatch Release Checklist before making a release recommendation. Strong performance on one measure does not replace the other release requirements."])
])
pdf("02_Candidate_Report.pdf",[
    ("RiverWatch: Candidate B",[
        "Evaluation report | 12 September 2026 | Fictional development fixture",
        "<b>Draft summary.</b> Candidate B achieved an RMSE of <b>0.62 metres</b> on RW-90. This summary was written before a scoring defect was discovered. The correction on page 3 supersedes the draft error value.",
        "Candidate B uses the same 420 training, 90 validation and 90 held-out cases as Baseline A. Timing was measured on the same bench workstation. Exact hardware specifications were not recorded.",
        "All cases are simulations with water at 20-24 degrees Celsius, one leak and complete sensor readings. Sampling is 10 Hz. No noisy or missing-sensor inputs were tested."]),
    ("Candidate B: timing and scope",[
        [["Measure","Candidate B"],["Mean prediction latency","260 milliseconds"],["95th-percentile latency","390 milliseconds"],["Held-out cases","90"],["Hardware model","Not recorded"]],
        "The timing measurements were unaffected by the scoring defect. Use these timing values together with the corrected error on page 3.",
        "There are no tests of hydrogen service, sensor failure, artificial noise or multiple simultaneous leaks. There is no field pilot or deployment.",
        "No confidence interval or statistical-significance test is supplied. A release recommendation must also satisfy the separate RiverWatch Release Checklist."]),
    ("Correction: final location error",[
        "<b>Approved correction | 13 September 2026</b>",
        "The draft summary on page 1 accidentally reused a subset score. Recomputing across all 90 held-out RW-90 cases gives a final RMSE of <b>0.71 metres</b>.",
        "The final value is 0.71 metres, replacing 0.62 metres everywhere the draft summary is quoted. The held-out cases and latency measurements are unchanged.",
        [["Result to use","Final corrected value"],["Candidate B RMSE","0.71 metres"],["Candidate B mean latency","260 milliseconds"],["Candidate B 95th-percentile latency","390 milliseconds"]],
        "This correction changes the reported score; it does not add robustness testing, a field pilot or evidence of deployment readiness."])
])
pdf("03_Release_Checklist.pdf",[
    ("RiverWatch: Release Checklist",[
        "Protocol version 1.0 | 1 September 2026 | Fictional development fixture",
        "All four criteria are required. A model that passes only the numerical criteria is not approved for release.",
        [["Required criterion","Pass condition"],["Location accuracy","Held-out RMSE at most 0.75 metres"],["Response time","Mean prediction latency at most 200 milliseconds"],["Sensor-failure evidence","Documented evaluation with missing sensors and an approved recovery procedure"],["Field evidence","A completed field pilot with recorded outcomes"]],
        "Use corrected final results when a report explicitly supersedes a draft. Cite the correction and explain the discrepancy."]),
    ("How to interpret the checklist",[
        "The latency requirement refers to the mean, not the 95th percentile. Both measures may be useful, but only the mean is the specified threshold here.",
        "An unreported test is missing evidence. Do not assume that a model passed a test because the report does not describe a failure.",
        "Neither numerical performance nor citations alone prove readiness for deployment. Name each missing or failed criterion in a recommendation.",
        "This protocol does not specify an exact GPU, RAM size, statistical-significance threshold or an approved budget. Those answers cannot be inferred from it."])
])
pdf("04_Test_Guide_Do_Not_Upload.pdf",[
    ("Document Review: test guide",[
        "Upload PDFs 01, 02 and 03 together. Keep this guide separate so the agent has to find the evidence itself. These are development fixtures, not a benchmark.",
        "<b>1. Comparison</b><br/>Ask: Which model has lower location error and which is faster? Use final results and cite the pages.",
        "Expected: Candidate B has lower RMSE (0.71 m versus 0.84 m). Baseline A has lower mean latency (180 ms versus 260 ms). The reports use the same 90 test cases and workstation; exact hardware is unknown. Evidence: Baseline p2; Candidate p2-p3.",
        "<b>2. Conflicting evidence</b><br/>Ask: The candidate report says both 0.62 and 0.71 metres. Which value should I use, and why?",
        "Expected: Use 0.71 m. Candidate p3 explicitly replaces the draft subset score of 0.62 m on p1. A good answer acknowledges both values and cites the correction.",
        "<b>3. Release decision</b><br/>Ask: Does either model meet all release requirements? Identify failed or missing criteria.",
        "Expected: Neither. A fails accuracy (0.84 &gt; 0.75) but passes mean latency (180 &lt;= 200). B passes accuracy (0.71 &lt;= 0.75) but fails mean latency (260 &gt; 200). Both lack sensor-failure evaluation/recovery and a field pilot. Evidence: Checklist p1; Baseline p2-p3; Candidate p2-p3."]),
    ("Check abstention and citations",[
        "<b>4. Missing information</b><br/>Ask: Which GPU and how much RAM were used? Was B's improvement statistically significant?",
        "Expected: The exact GPU/RAM and statistical significance are not established. Do not invent hardware specifications, confidence intervals or a p-value.",
        "<b>5. Unsupported generalization</b><br/>Ask: Can I conclude that Candidate B is robust to hydrogen service and missing sensors?",
        "Expected: No. These conditions were not tested. The agent should distinguish missing evidence from a demonstrated failure.",
        "<b>Inspect the sources.</b> Open each citation and check that the quoted passage supports the claim. A valid page link alone is not enough. Compare the final answer with all three PDFs, including the correction.",
        "<b>Local check.</b> After setup, disconnect external networking and repeat a question. Confirm the app uses local mode. Successful offline operation is a useful deployment check, not a comprehensive security audit.",
        "Generated fictional material for repeatable manual testing. No actual research results or personal information are included."])
])
print(OUT)
