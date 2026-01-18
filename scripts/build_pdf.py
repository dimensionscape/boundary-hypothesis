"""Build the Boundary / Field / Structure edition of the research manuscript."""
from pathlib import Path
from io import BytesIO
import hashlib
import html
import json
import math
import re

import matplotlib
matplotlib.use('Agg')
from matplotlib import mathtext, rcParams
from matplotlib.font_manager import FontProperties
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Flowable, PageBreak, Preformatted,
)
from pypdf import PdfReader, PdfWriter
from check_manuscript import check

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'manuscript/paper.md'
VERIFY = ROOT / 'scripts/verify.py'
DEST = ROOT / 'output/pdf/boundary-hypothesis.pdf'
TEMP = ROOT / 'tmp/pdfs'
TEMP.mkdir(parents=True, exist_ok=True)
DEST.parent.mkdir(parents=True, exist_ok=True)
AUTHOR = 'Christopher Speciale'
TITLE = 'A boundary hypothesis for genesis and structural stabilization'

raw, verification, manuscript_audit = check()

font_dir = Path(matplotlib.get_data_path()) / 'fonts/ttf'
for face, file in [('Paper', 'STIXGeneral.ttf'), ('Paper-Bold', 'STIXGeneralBol.ttf'),
                   ('Paper-Italic', 'STIXGeneralItalic.ttf'), ('Paper-BoldItalic', 'STIXGeneralBolIta.ttf')]:
    pdfmetrics.registerFont(TTFont(face, str(font_dir / file)))
pdfmetrics.registerFontFamily('Paper', normal='Paper', bold='Paper-Bold',
                             italic='Paper-Italic', boldItalic='Paper-BoldItalic')
pdfmetrics.registerFont(TTFont('Meta', str(font_dir / 'DejaVuSans.ttf')))
glyphs = pdfmetrics.getFont('Paper').face.charToGlyph
missing = sorted({c for c in raw if ord(c) > 127 and ord(c) not in glyphs})
assert not missing, repr(missing)

rcParams['mathtext.fontset'] = 'stix'
rcParams['svg.fonttype'] = 'path'
rcParams['savefig.transparent'] = True
PAGE_W, PAGE_H = A4
MARGIN = 56
WIDTH = PAGE_W - 2 * MARGIN
INK = colors.HexColor('#17292C')
MUTED = colors.HexColor('#5E7071')
TEAL = colors.HexColor('#0C343A')
GOLD = colors.HexColor('#C38F52')
PAPER = colors.HexColor('#FCFBF7')
PALE = colors.HexColor('#EDF2EF')
BODY = ParagraphStyle('Body', fontName='Paper', fontSize=11.0, leading=14.6,
                      textColor=INK, spaceAfter=7, allowWidows=0, allowOrphans=0,
                      alignment=TA_JUSTIFY)
PROOF = ParagraphStyle('Proof', parent=BODY, spaceAfter=8)
CLAIM = ParagraphStyle('Claim', parent=BODY, fontName='Paper-Bold',
                       keepWithNext=True, spaceBefore=4, spaceAfter=5)
HEAD = ParagraphStyle('Heading', parent=BODY, fontName='Paper-Bold', textColor=TEAL,
                      fontSize=14, leading=17, spaceBefore=15, spaceAfter=8,
                      keepWithNext=True, alignment=0)
SUB = ParagraphStyle('Subheading', parent=HEAD, fontSize=11.8, leading=15,
                     spaceBefore=10, spaceAfter=6)
TITLE_STYLE = ParagraphStyle('Title', parent=HEAD, fontSize=22, leading=26,
                            spaceBefore=0, spaceAfter=13, alignment=TA_CENTER)
AUTHOR_STYLE = ParagraphStyle('Author', parent=BODY, fontSize=12,
                             leading=16, alignment=TA_CENTER, spaceAfter=4)
META_STYLE = ParagraphStyle('Meta', fontName='Meta', fontSize=9.1, leading=12,
                           textColor=MUTED, alignment=TA_CENTER, spaceAfter=17)
ABSTRACT = ParagraphStyle('Abstract', parent=BODY, fontSize=10.1, leading=13.3,
                         leftIndent=12, rightIndent=12, spaceAfter=11)
CELL = ParagraphStyle('Cell', parent=BODY, fontSize=9.4, leading=12.0,
                     spaceAfter=0, alignment=0)
CELL_HEAD = ParagraphStyle('CellHead', parent=CELL, fontName='Paper-Bold')
CODE = ParagraphStyle('Code', fontName='Courier', fontSize=8.0, leading=10.5,
                      leftIndent=7, rightIndent=5, spaceAfter=5)
REF = ParagraphStyle('Reference', parent=BODY, fontSize=9.5, leading=12.4,
                     leftIndent=19, firstLineIndent=-19, spaceAfter=8,
                     alignment=0)


def scripts(text):
    def replace(match):
        mark, token = match.groups()
        if token.startswith(('(', '{')):
            token = token[1:-1]
        tag = 'sub' if mark == '_' else 'super'
        return f'<{tag}>{token}</{tag}>'
    text = re.sub(r'([_^])(\([^)]*\)|\{[^}]*\}|[A-Za-z\u0370-\u03ff][A-Za-z\u0370-\u03ff0-9]*|[0-9]+|[+*])',
                  replace, text)
    return text.replace('†', '<super>†</super>')


def inline(value):
    codes = []
    def code(match):
        codes.append('<font name="Courier" size="9">'
                     + html.escape(match.group(1)) + '</font>')
        return f'CODETOKEN{len(codes) - 1}TOKEN'
    value = re.sub(r'`([^`]+)`', code, value)
    value = html.escape(value)
    value = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', value)
    value = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',
                   r'<link href="\2" color="#263F50">\1</link>', value)
    pieces = re.split(r'(<[^>]*>)', value)
    for i in range(0, len(pieces), 2):
        pieces[i] = scripts(pieces[i])
    value = ''.join(pieces)
    for i, literal in enumerate(codes):
        value = value.replace(f'CODETOKEN{i}TOKEN', literal)
    return value


math_cache = {}


class Equation(Flowable):
    def __init__(self, expression, number):
        super().__init__()
        expression = re.sub(r'\\(mathcal|mathbb)\s+([A-Za-z])',
                            lambda m: '\\' + m[1] + '{' + m[2] + '}', expression)
        expression = re.sub(r'\\dot\s*(\\[A-Za-z]+|[A-Za-z])',
                            lambda m: '\\dot{' + m[1] + '}', expression)
        self.expression, self.number = expression.strip(), number
        if expression not in math_cache:
            buffer = BytesIO()
            mathtext.math_to_image('$' + expression + '$', buffer,
                                   prop=FontProperties(size=12), format='svg')
            math_cache[expression] = svg2rlg(BytesIO(buffer.getvalue()))
        self.drawing = math_cache[expression]
        self.scale = min(1.0, (WIDTH - 34) / self.drawing.width)
        assert self.scale >= 0.70, (number, self.scale, expression)
        self.width = WIDTH
        self.height = self.drawing.height * self.scale + 14
        self.spaceAfter = 5
        self.spaceBefore = 0

    def wrap(self, avail_width, avail_height):
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(PALE)
        canvas.roundRect(0, 0, WIDTH, self.height, 4, fill=1, stroke=0)
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.3)
        canvas.line(0, 4, 0, self.height - 4)
        canvas.restoreState()
        canvas.saveState()
        x = max(2, (WIDTH - 27 - self.drawing.width * self.scale) / 2)
        canvas.translate(x, 7)
        canvas.scale(self.scale, self.scale)
        renderPDF.draw(self.drawing, canvas, 0, 0)
        canvas.restoreState()
        canvas.setFont('Paper', 10.2)
        canvas.drawRightString(WIDTH, self.height / 2 - 3, f'({self.number})')


class Cover(Flowable):
    """Vector cover with an open boundary resolving into a regular structure."""
    def __init__(self):
        super().__init__()
        self.width = WIDTH
        self.height = 700

    def wrap(self, avail_width, avail_height):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(GOLD)
        c.setFont('Meta', 9)
        c.drawString(0, 666, 'RESEARCH MANUSCRIPT  /  01.18.2026')
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.8)
        c.line(0, 648, WIDTH, 648)
        cover_style = ParagraphStyle('CoverTitle', fontName='Paper', fontSize=34,
                                      leading=39, textColor=PAPER)
        p = Paragraph('A boundary hypothesis<br/>for genesis and<br/>structural stabilization',
                      cover_style)
        _, h = p.wrap(WIDTH, 180)
        p.drawOn(c, 0, 603 - h)
        c.setFillColor(PAPER)
        c.setFont('Paper', 16)
        c.drawString(0, 432, AUTHOR)
        c.setFont('Meta', 8.5)
        c.setFillColor(colors.HexColor('#AEC2BE'))
        c.drawString(0, 407, 'ORIGIN  /  STRUCTURE  /  STABILIZATION')

        # A visual motif, not a diagram of physical states or an external time.
        left, base, wide, high = 0, 163, WIDTH, 176
        c.setLineWidth(0.45)
        for row in range(8):
            yy = base + row * high / 7
            path = c.beginPath()
            path.moveTo(left, yy + (row - 3.5) * 4)
            path.curveTo(wide * 0.30, yy + math.sin(row) * 26,
                         wide * 0.49, yy - math.cos(row * 0.8) * 22,
                         wide * 0.66, yy)
            path.lineTo(wide, yy)
            c.setStrokeColor(colors.HexColor('#678B89'))
            c.drawPath(path)
        for column in range(7):
            xx = wide * (0.66 + 0.34 * column / 6)
            c.setStrokeColor(colors.HexColor('#678B89'))
            c.line(xx, base, xx, base + high)
        c.setLineWidth(1.8)
        c.setStrokeColor(GOLD)
        c.line(wide * 0.66, base - 16, wide * 0.66, base + high + 16)
        for row in range(8):
            c.setFillColor(GOLD)
            c.circle(wide * 0.66, base + row * high / 7, 2, fill=1, stroke=0)
        c.setFont('Meta', 7.5)
        c.setFillColor(colors.HexColor('#AEC2BE'))
        c.drawString(0, 121, 'A SOURCE-FREE ORIGIN HYPOTHESIS WITH CONDITIONAL MATHEMATICAL MODELS')
        c.setStrokeColor(colors.HexColor('#41646A'))
        c.setLineWidth(0.6)
        c.line(0, 94, WIDTH, 94)
        c.setFillColor(PAPER)
        c.setFont('Paper', 11)
        c.drawString(0, 69, 'Complete argument, proofs, calculations, and reproducibility appendix')
        c.setFillColor(GOLD)
        c.setFont('Meta', 8)
        c.drawString(0, 37, 'VERSION 1.0.0')
        c.drawRightString(WIDTH, 37, 'JANUARY 18, 2026')
        c.restoreState()


class PaperDoc(SimpleDocTemplate):
    def afterFlowable(self, item):
        if isinstance(item, Paragraph) and item.style.name in ('Heading', 'Subheading'):
            label = item.getPlainText()
            key = 'section-' + hashlib.sha1(label.encode()).hexdigest()[:12]
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(label, key,
                                       level=0 if item.style.name == 'Heading' else 1,
                                       closed=False)


def story():
    result, equations, headings = [Cover(), PageBreak()], [], []
    lines = raw.splitlines()
    i, section = 0, ''
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith('<!--'):
            i += 1
            continue
        if line.startswith('# '):
            i += 1
            continue
        if line == '**' + AUTHOR + '**':
            i += 1
            continue
        if line.startswith('Research manuscript - '):
            i += 1
            continue
        if line.startswith(('## ', '### ')):
            level = 3 if line.startswith('### ') else 2
            label = line[level + 1:]
            section = label if level == 2 else section
            if label.startswith('Appendix ') or label == 'References':
                result.append(PageBreak())
            result.append(Paragraph(inline(label), SUB if level == 3 else HEAD))
            headings.append(label)
            i += 1
            continue
        if line.startswith('```'):
            kind, block = line[3:], []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                block.append(lines[i])
                i += 1
            i += 1
            if kind == 'math':
                pieces = re.split(r'\\tag\{(\d+)\}', ' '.join(block))
                assert not pieces[-1].strip()
                for j in range(0, len(pieces) - 1, 2):
                    expression, number = pieces[j].strip(), int(pieces[j + 1])
                    equations.append(number)
                    result.append(Equation(expression, number))
            else:
                assert max(map(len, block), default=0) <= 96
                result.append(Preformatted('\n'.join(block), CODE, maxLineLength=100))
            continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                row = [p.strip() for p in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', p) for p in row):
                    rows.append(row)
                i += 1
            fractions = [0.67, 0.33] if len(rows[0]) == 2 else [0.23, 0.40, 0.37]
            table = Table([
                [Paragraph(inline(p), CELL_HEAD if n == 0 else CELL) for p in row]
                for n, row in enumerate(rows)
            ], colWidths=[WIDTH * f for f in fractions], repeatRows=1)
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 0), (-1, 0), PALE),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [PAPER, colors.white]),
                ('LINEABOVE', (0, 0), (-1, 0), 1.1, GOLD),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, TEAL),
                ('LINEBELOW', (0, -1), (-1, -1), 0.5, TEAL),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            result.extend([table, Spacer(1, 9)])
            continue
        paragraph = [line]
        i += 1
        while (i < len(lines) and lines[i].strip()
               and not lines[i].strip().startswith(('#', '|', '```', '<!--'))):
            paragraph.append(lines[i].strip())
            i += 1
        style = BODY
        if section == 'Abstract':
            style = ABSTRACT
        elif section == 'References':
            style = REF
        elif line.startswith('**Proposition'):
            style = CLAIM
        elif line.startswith('**Proof.'):
            style = PROOF
        result.append(Paragraph(inline(' '.join(paragraph)), style))
    assert equations == list(range(1, 19)), equations
    return result, equations, headings


def render(total=None):
    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setTitle(TITLE)
        canvas.setAuthor(AUTHOR)
        canvas.setCreator('Manuscript')
        canvas.setFillColor(TEAL if doc.page == 1 else PAPER)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        if doc.page == 1:
            canvas.restoreState()
            return
        canvas.setFont('Meta', 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, PAGE_H - 28, 'BOUNDARY HYPOTHESIS')
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 28, 'CHRISTOPHER SPECIALE')
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(0.8)
        canvas.line(MARGIN, PAGE_H - 37, PAGE_W - MARGIN, PAGE_H - 37)
        canvas.setStrokeColor(colors.HexColor('#C9D3CC'))
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 40, PAGE_W - MARGIN, 40)
        canvas.drawString(MARGIN, 25, 'JANUARY 18, 2026  /  V1.0.0')
        label = f'{doc.page:02d}' if total is None else f'{doc.page:02d} / {total:02d}'
        canvas.setFillColor(TEAL)
        canvas.drawRightString(PAGE_W - MARGIN, 25, label)
        canvas.restoreState()
    content, equations, headings = story()
    doc = PaperDoc(str(TEMP / 'body.pdf'), pagesize=A4,
                   leftMargin=MARGIN, rightMargin=MARGIN,
                   topMargin=53, bottomMargin=54,
                   title=TITLE, author=AUTHOR,
                   subject='Source-free genesis, conditional structural models, and cosmological matching')
    doc.build(content, onFirstPage=decorate, onLaterPages=decorate)
    return equations, headings


equations, headings = render()
page_count = len(PdfReader(TEMP / 'body.pdf').pages)
equations, headings = render(page_count)
reader = PdfReader(TEMP / 'body.pdf')
writer = PdfWriter()
writer.clone_document_from_reader(reader)
writer.add_metadata({'/Author': AUTHOR, '/Title': TITLE,
                     '/Creator': 'Manuscript', '/Producer': 'Research manuscript',
                     '/CreationDate': "D:20260118120000-05'00'",
                     '/ModDate': "D:20260118120000-05'00'"})
writer.add_attachment('verify.py', VERIFY.read_bytes())
writer.add_attachment('verification-results.json',
                       (json.dumps(verification, indent=2) + '\n').encode())
writer.write(DEST)

final = PdfReader(DEST)
texts = [p.extract_text() or '' for p in final.pages]
combined = '\n'.join(texts)
assert len(final.pages) == page_count
assert final.metadata.author == AUTHOR
assert len(final.attachments['verify.py']) == 1
assert final.attachments['verify.py'][0] == VERIFY.read_bytes()
for forbidden in (r'[\u2010-\u2015]', r'[A-Z]:[/\\]|file://|VERIFICATION_(SUMMARY|CODE)'):
    assert not re.search(forbidden, combined), forbidden
for required in ('Christopher Speciale', 'Appendix D.', 'Proposition 11.',
                 'conditional interface with cosmology', '20,001', 'References'):
    assert required.lower() in combined.lower(), required
assert all(len(t.strip()) > 80 for t in texts)
assert '\ufffd' not in combined
assert (ROOT / 'results/verification.json').exists()
annotations = sum(len(p.get('/Annots', [])) for p in final.pages)
assert annotations >= 13
(TEMP / 'extracted.txt').write_text(combined, encoding='utf-8')
report = {
    'pdf': DEST.relative_to(ROOT).as_posix(),
    'source': SOURCE.relative_to(ROOT).as_posix(), 'author': AUTHOR,
    'pages': page_count, 'source_words': len(re.findall(r'\b\w+\b', raw)),
    'numbered_equations': len(equations), 'propositions': 11,
    'embedded_files': list(final.attachments), 'external_reference_links': annotations,
    'verification': verification, 'forbidden_text_checks_passed': True,
    'missing_font_glyphs': missing, 'text_checks_passed': True,
    'smallest_equation_scale': min(
        min(1.0, (WIDTH - 34) / drawing.width) for drawing in math_cache.values()),
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'pdf_sha256': hashlib.sha256(DEST.read_bytes()).hexdigest(),
    'visual_review': 'A fresh visual review is required after each build',
    'headings': headings,
}
(ROOT / 'results/pdf-check.json').write_text(
    json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in report.items()
                  if k not in ('verification', 'headings')}, indent=2))
