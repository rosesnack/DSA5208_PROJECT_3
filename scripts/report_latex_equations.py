"""Compile LaTeX display equations and place their vector pages in a ReportLab PDF."""
from pathlib import Path
import shutil
import subprocess

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.platypus import Flowable


class LatexEquations:
    def __init__(self, directory, temporary):
        self.directory = Path(directory)
        self.temporary = Path(temporary)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.temporary.mkdir(parents=True, exist_ok=True)
        self.placements = []
        self.count = 0

    def display(self, latex):
        self.count += 1
        name = f'equation_{self.count:02d}'
        source = self.directory / (name + '.tex')
        output = self.directory / (name + '.pdf')
        document = r'''\documentclass[11pt]{article}
\usepackage{amsmath,amssymb}
\pagestyle{empty}
\begin{document}
\setbox0=\hbox{$\displaystyle LATEX$}
\pdfpagewidth=\dimexpr\wd0+4pt\relax
\pdfpageheight=\dimexpr\ht0+\dp0+4pt\relax
\hoffset=-1in
\voffset=-1in
\shipout\vbox{\kern2pt\hbox{\kern2pt\box0\kern2pt}\kern2pt}
\end{document}
'''.replace('LATEX', latex)
        if not output.exists() or not source.exists() or source.read_text() != document:
            source.write_text(document)
            subprocess.run([shutil.which('pdflatex'), '-halt-on-error', '-interaction=batchmode',
                            '-output-directory', str(self.temporary), str(source)],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            shutil.copyfile(self.temporary / (name + '.pdf'), output)
        return Equation(output, self.count, self.placements)

    def merge(self, destination):
        base_reader = PdfReader(destination)
        writer = PdfWriter()
        writer.clone_document_from_reader(base_reader)
        equation_readers = {path: PdfReader(path) for _, path, _, _, _ in self.placements}
        for page_number, path, x, y, scale in self.placements:
            writer.pages[page_number - 1].merge_transformed_page(
                equation_readers[path].pages[0], Transformation().scale(scale).translate(x, y))
        temporary = self.temporary / 'report_with_equations.pdf'
        writer.write(temporary)
        shutil.copyfile(temporary, destination)


class Equation(Flowable):
    def __init__(self, path, number, placements):
        super().__init__()
        self.path, self.number, self.placements = path, number, placements
        page = PdfReader(path).pages[0]
        self.pdf_width = float(page.mediabox.width)
        self.pdf_height = float(page.mediabox.height)

    def wrap(self, available_width, available_height):
        self.width = available_width
        self.scale = min(1, (available_width - 35) / self.pdf_width)
        self.height = self.pdf_height * self.scale + 15
        return self.width, self.height

    def draw(self):
        left = (self.width - self.pdf_width * self.scale) / 2
        x, y = self.canv.absolutePosition(left, 8)
        self.placements.append((self.canv.getPageNumber(), self.path, x, y, self.scale))
        self.canv.setFillColorRGB(0.09, 0.17, 0.23)
        self.canv.setFont('Times-Roman', 10)
        self.canv.drawRightString(self.width, 8 + self.pdf_height * self.scale / 2 - 3,
                                 f'({self.number})')
