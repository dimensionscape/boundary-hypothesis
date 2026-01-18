"""Build the short illustrated companion for casual readers."""
from pathlib import Path
import hashlib
import html
import json
import re

import matplotlib
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Flowable

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/laymans-guide.md'
DEST = ROOT / 'output/pdf/boundary-hypothesis-laymans-guide.pdf'
TEMP = ROOT / 'tmp/guide'
TEMP.mkdir(parents=True, exist_ok=True)
DEST.parent.mkdir(parents=True, exist_ok=True)
AUTHOR = 'Christopher Speciale'
TITLE = "A layman's guide to A boundary hypothesis for genesis and structural stabilization"
PAGE_W, PAGE_H = A4
MARGIN = 55
WIDTH = PAGE_W - 2 * MARGIN
TEAL = colors.HexColor('#0C343A')
GOLD = colors.HexColor('#C38F52')
PAPER = colors.HexColor('#FCFBF7')
PALE = colors.HexColor('#EDF2EF')
INK = colors.HexColor('#17292C')
MUTED = colors.HexColor('#5E7071')

font_dir = Path(matplotlib.get_data_path()) / 'fonts/ttf'
for face, name in [('Guide', 'STIXGeneral.ttf'), ('Guide-Bold', 'STIXGeneralBol.ttf'),
                   ('Guide-Italic', 'STIXGeneralItalic.ttf')]:
    pdfmetrics.registerFont(TTFont(face, str(font_dir / name)))
pdfmetrics.registerFontFamily('Guide', normal='Guide', bold='Guide-Bold',
                             italic='Guide-Italic', boldItalic='Guide-Bold')
pdfmetrics.registerFont(TTFont('GuideMeta', str(font_dir / 'DejaVuSans.ttf')))
BODY = ParagraphStyle('Body', fontName='Guide', fontSize=11.7, leading=15.8,
                      textColor=INK, spaceAfter=7, allowWidows=0, allowOrphans=0)
HEAD = ParagraphStyle('Heading', parent=BODY, fontName='Guide-Bold', fontSize=20,
                      leading=23, textColor=TEAL, spaceBefore=5, spaceAfter=12,
                      keepWithNext=True)
SUB = ParagraphStyle('Subheading', parent=BODY, fontName='Guide-Bold', fontSize=13,
                     leading=16, textColor=TEAL, spaceBefore=5, spaceAfter=5,
                     keepWithNext=True)
QUOTE = ParagraphStyle('Callout', parent=BODY, leftIndent=11, rightIndent=11,
                       borderColor=GOLD, borderWidth=0.7, borderPadding=9,
                       backColor=PALE, spaceBefore=5, spaceAfter=12)


def inline(text):
    text = html.escape(text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    return re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',
                  r'<link href="\2" color="#0C545D"><u>\1</u></link>', text)


class Masthead(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = WIDTH, 129

    def draw(self):
        c = self.canv
        c.setFillColor(TEAL)
        c.roundRect(0, 9, WIDTH, 120, 5, fill=1, stroke=0)
        c.setFillColor(GOLD)
        c.setFont('GuideMeta', 8)
        c.drawString(17, 110, 'THE PAPER, IN PLAIN LANGUAGE')
        c.setFillColor(PAPER)
        c.setFont('Guide', 27)
        c.drawString(17, 79, "A layman's guide")
        style = ParagraphStyle('Subtitle', fontName='Guide', fontSize=13,
                               leading=15, textColor=PAPER)
        subtitle = Paragraph('to <i>A boundary hypothesis for genesis<br/>'
                             'and structural stabilization</i>', style)
        subtitle.wrap(WIDTH-34, 40)
        subtitle.drawOn(c, 17, 41)
        c.setFillColor(GOLD)
        c.setFont('GuideMeta', 7.5)
        c.drawString(17, 23, 'CHRISTOPHER SPECIALE')
        c.drawRightString(WIDTH-17, 23, 'JANUARY 18, 2026')


class Diagram(Flowable):
    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.width, self.height = WIDTH, 66 if kind == 'slots' else 57
        self.spaceAfter = 6

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(PALE)
        c.roundRect(0, 0, WIDTH, self.height, 4, fill=1, stroke=0)
        if self.kind == 'slots':
            group = WIDTH/4
            for state in range(4):
                start = state*group+17
                for slot in range(4):
                    occupied = slot <= state
                    c.setFillColor(TEAL if occupied else PAPER)
                    c.setStrokeColor(TEAL)
                    c.roundRect(start+slot*19, 30, 13, 17, 2, fill=1, stroke=1)
                c.setFillColor(INK)
                c.setFont('GuideMeta', 7.2)
                remaining = 3-state
                label = f'{remaining} available' if remaining else 'Additions close'
                c.drawCentredString(state*group+group/2, 13, label)
        else:
            left, right = 25, WIDTH-25
            c.setStrokeColor(TEAL)
            c.setLineWidth(1)
            c.line(left, 31, right, 31)
            for fraction, label in [(0, '0'), (1/3, '1/3'), (2/3, '2/3'), (1, '1')]:
                x = left+(right-left)*fraction
                c.setFillColor(GOLD)
                c.circle(x, 31, 4, fill=1, stroke=0)
                c.setFillColor(INK)
                c.setFont('GuideMeta', 8)
                c.drawCentredString(x, 11, label)
        c.restoreState()


raw = SOURCE.read_text(encoding='utf-8')
assert not re.search(r'[\u2010-\u2015]|\ufffd', raw)
expected_headings = re.findall(r'^## (.+)$', raw, re.M)
assert len(expected_headings) == 3


def story():
    result = [Masthead()]
    lines = raw.splitlines()
    i, section_count = 0, 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if section_count == 0 and not line.startswith('## '):
            i += 1
            continue
        if line.startswith('## '):
            if section_count:
                result.append(PageBreak())
            section_count += 1
            result.append(Paragraph(inline(line[3:]), HEAD))
            i += 1
            continue
        if line.startswith('### '):
            result.append(Paragraph(inline(line[4:]), SUB))
            i += 1
            continue
        if line.startswith('<!-- FIGURE:'):
            kind = line.split(':', 1)[1].split()[0]
            result.append(Diagram(kind))
            i += 1
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '<!--')):
            paragraph.append(lines[i].strip())
            i += 1
        text = ' '.join(paragraph)
        result.append(Paragraph(inline(text[2:] if text.startswith('> ') else text),
                                QUOTE if text.startswith('> ') else BODY))
    return result


def decorate(c, doc):
    c.saveState()
    c.setFillColor(PAPER)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    if doc.page > 1:
        c.setFont('GuideMeta', 8)
        c.setFillColor(MUTED)
        c.drawString(MARGIN, PAGE_H-27, "A LAYMAN'S GUIDE")
        c.drawRightString(PAGE_W-MARGIN, PAGE_H-27, 'BOUNDARY HYPOTHESIS')
        c.setStrokeColor(GOLD)
        c.line(MARGIN, PAGE_H-36, PAGE_W-MARGIN, PAGE_H-36)
    c.setStrokeColor(colors.HexColor('#C9D3CC'))
    c.line(MARGIN, 38, PAGE_W-MARGIN, 38)
    c.setFont('GuideMeta', 7.5)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, 23, 'CHRISTOPHER SPECIALE  /  JANUARY 18, 2026')
    c.drawRightString(PAGE_W-MARGIN, 23, f'{doc.page} / 3')
    c.restoreState()


doc = SimpleDocTemplate(str(TEMP/'body.pdf'), pagesize=A4,
                        leftMargin=MARGIN, rightMargin=MARGIN,
                        topMargin=49, bottomMargin=52,
                        title=TITLE, author=AUTHOR)
doc.build(story(), onFirstPage=decorate, onLaterPages=decorate)
reader = PdfReader(TEMP/'body.pdf')
assert len(reader.pages) == 3, f'Expected a short three-page guide; got {len(reader.pages)} pages'
writer = PdfWriter()
writer.clone_document_from_reader(reader)
writer.add_metadata({'/Title': TITLE, '/Author': AUTHOR,
                     '/Subject': 'Short plain-language companion to the research manuscript',
                     '/Creator': 'Manuscript', '/Producer': 'Research manuscript',
                     '/CreationDate': "D:20260118120000-05'00'",
                     '/ModDate': "D:20260118120000-05'00'"})
writer.write(DEST)
final = PdfReader(DEST)
text = '\n'.join(page.extract_text() or '' for page in final.pages)
for heading in expected_headings:
    assert heading in text, heading
for phrase in ['nothing to stop everything', 'origin hypothesis', 'Four available slots',
                'Infinite candidates, finite room', 'January 18, 2026']:
    assert phrase.casefold() in text.casefold(), phrase
assert not re.search(r'[\u2010-\u2015]|\ufffd', text)
assert final.metadata.author == AUTHOR
assert sum(len(p.get('/Annots', [])) for p in final.pages) == 2
report = {'source': SOURCE.relative_to(ROOT).as_posix(),
          'pdf': DEST.relative_to(ROOT).as_posix(), 'pages': 3, 'author': AUTHOR,
          'paper_date': '2026-01-18', 'source_words': len(raw.split()),
          'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'pdf_sha256': hashlib.sha256(DEST.read_bytes()).hexdigest(),
          'text_checks_passed': True,
          'visual_review': 'A fresh visual review is required after each build'}
(ROOT/'results/guide-pdf-check.json').write_text(json.dumps(report, indent=2)+'\n',
                                               encoding='utf-8', newline='\n')
print(json.dumps(report, indent=2))
