"""
Generate the synthetic samples in samples/pdf/: comprobantes de domicilio and CSF (persona física and moral).

Every name, address, number and provider is fictitious, and each page says so: the samples
exercise the pipeline (embedded text and OCR) without personal data or real company layouts.

Run inside the container (PyMuPDF is installed there):
    docker compose exec app python scripts/generate_samples.py
"""
import fitz  # PyMuPDF

SAMPLE_NOTICE = "MUESTRA CON DATOS FICTICIOS - SIN VALIDEZ OFICIAL"

ELECTRICITY_BILL = [
    (18, "ENERGIA DEL VALLE S.A. DE C.V."),
    (9, "Suministro de energia electrica"),
    (9, ""),
    (11, "XAVIER EJEMPLO PRUEBA"),
    (9, "AV DE LOS EJEMPLOS 123 INT 4"),
    (9, "COL. CENTRO"),
    (9, "C.P. 06000 CUAUHTEMOC, CIUDAD DE MEXICO"),
    (9, ""),
    (9, "NO. DE SERVICIO: 000123456789"),
    (9, "TARIFA: 1   MEDIDOR: XX0000"),
    (9, "FECHA DE EMISION: 14 OCT 26"),
    (9, "PERIODO FACTURADO: 12 AGO 26 - 13 OCT 26"),
    (9, "FECHA LIMITE DE PAGO: 28 OCT 26"),
    (9, ""),
    (12, "TOTAL A PAGAR: $250"),
]

INTERNET_BILL = [
    (18, "RED HOGAR TELECOMUNICACIONES"),
    (9, "Estado de cuenta - Internet y telefonia"),
    (9, ""),
    (11, "Titular: MARIA EJEMPLO MUESTRA"),
    (9, "Domicilio: CALLE FICTICIA 45, COL. DEL VALLE CENTRO"),
    (9, "BENITO JUAREZ, CIUDAD DE MEXICO, C.P. 03100"),
    (9, ""),
    (9, "Numero de cuenta: 9876543210"),
    (9, "Fecha de emision: 05/10/2026"),
    (9, "Periodo: del 01/09/2026 al 30/09/2026"),
    (9, "Pagar antes de: 20/10/2026"),
    (9, ""),
    (12, "Paquete Internet 100 Mbps + Linea fija"),
]


def csf_lines(rfc: str, name_block: list[str], curp: str | None, issued: str, regime: str) -> list[tuple[int, str]]:
    """
    Lines of a CSF-like page, one item per line, in the order the CSF regex extractor expects.

    No SAT logos or layout: only the text structure. Every value is fictitious.

    Args:
        rfc (str): Fictitious RFC (valid structure and check digit).
        name_block (list[str]): Lines for the taxpayer's name section.
        curp (str | None): Fictitious CURP, or None for a persona moral.
        issued (str): Issue date as the SAT prints it ("30 DE OCTUBRE DE 2026").
        regime (str): Tax regime name.

    Returns:
        list[tuple[int, str]]: (font size, text) per line.
    """
    lines = [
        "CEDULA DE IDENTIFICACION FISCAL", rfc, "Registro Federal de Contribuyentes",
        "CONSTANCIA DE SITUACIÓN FISCAL", "Lugar y Fecha de Emisión", f"CIUDAD DE MEXICO , MEXICO A {issued}",
        "Datos de Identificación del Contribuyente:", "RFC:", rfc,
    ]
    if curp:
        lines += ["CURP:", curp]
    lines += name_block
    lines += ["Estatus en el padrón:", "ACTIVO", "Regímenes:", "Régimen", regime, "01/01/2024",
              "Sus datos personales son incorporados y protegidos en los sistemas del SAT"]
    return [(9, line) for line in lines]


CSF_ISSUED = "30 DE OCTUBRE DE 2026"

CSF_FISICA = csf_lines(
    rfc="PELJ900515AB7",
    name_block=["Nombre (s):", "JUAN", "Primer Apellido:", "PEREZ", "Segundo Apellido:", "LOPEZ"],
    curp="PELJ900515HDFRPN07",
    issued=CSF_ISSUED,
    regime="Régimen de Sueldos y Salarios e Ingresos Asimilados a Salarios",
)

CSF_MORAL = csf_lines(
    rfc="ABC200101XY3",
    name_block=["Denominación/Razón Social:", "EMPRESA EJEMPLO SA DE CV"],
    curp=None,
    issued=CSF_ISSUED,
    regime="Régimen General de Ley Personas Morales",
)


def build_page(doc: fitz.Document, lines: list[tuple[int, str]]) -> None:
    """
    Write a bill-like page: header lines, the fictitious-data notice and a footer.

    Args:
        doc (fitz.Document): Document to add the page to.
        lines (list[tuple[int, str]]): (font size, text) per line, top to bottom.
    """
    page = doc.new_page()
    y = 70
    for size, text in lines:
        if text:
            page.insert_text((60, y), text, fontsize=size)
        y += size + 9
    page.insert_text((60, y + 30), SAMPLE_NOTICE, fontsize=10, color=(0.6, 0, 0))


def electricity_sample(path: str) -> None:
    """
    Digital bill with embedded text (PdfProcessor -> text_extraction, no OCR).

    Args:
        path (str): Output PDF path.
    """
    doc = fitz.open()
    build_page(doc, ELECTRICITY_BILL)
    doc.save(path)
    doc.close()


def internet_scan_sample(path: str, dpi: int = 150) -> None:
    """
    Scanned bill: the page is rasterized in grayscale, so the PDF holds only an image (-> OCR).

    Args:
        path (str): Output PDF path.
        dpi (int): Resolution of the simulated scan.
    """
    source = fitz.open()
    build_page(source, INTERNET_BILL)
    pixmap = source[0].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)

    scan = fitz.open()
    page = scan.new_page(width=source[0].rect.width, height=source[0].rect.height)
    page.insert_image(page.rect, pixmap=pixmap)
    scan.save(path, deflate=True, garbage=4)
    scan.close()
    source.close()


def digital_sample(path: str, lines: list[tuple[int, str]]) -> None:
    """
    Digital PDF with embedded text (PdfProcessor -> text_extraction, no OCR).

    Args:
        path (str): Output PDF path.
        lines (list[tuple[int, str]]): Page lines.
    """
    doc = fitz.open()
    build_page(doc, lines)
    doc.save(path)
    doc.close()


if __name__ == "__main__":
    electricity_sample("samples/pdf/comprobante_luz_sample.pdf")
    internet_scan_sample("samples/pdf/comprobante_internet_scan_sample.pdf")
    digital_sample("samples/pdf/csf_fisica_sample.pdf", CSF_FISICA)
    digital_sample("samples/pdf/csf_moral_sample.pdf", CSF_MORAL)
    print("Generated the comprobante and CSF samples in samples/pdf/")
