from reportlab.pdfgen import canvas

def create_pdf(filename):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, "Clinical Study Report: Drug X")
    c.drawString(100, 700, "Table 1: Efficacy Results")
    c.drawString(100, 680, "Metric       Value      P-Value")
    c.drawString(100, 660, "Outcome A    12.5       0.04")  # Matches Mock Vision
    c.drawString(100, 500, "Sample Size: N=500")
    c.save()

if __name__ == "__main__":
    create_pdf("conflict_study.pdf")
