"""
Generate the synthetic comprobante de domicilio samples in samples/pdf/.

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


if __name__ == "__main__":
    electricity_sample("samples/pdf/comprobante_luz_sample.pdf")
    internet_scan_sample("samples/pdf/comprobante_internet_scan_sample.pdf")
    print("Generated samples/pdf/comprobante_luz_sample.pdf and samples/pdf/comprobante_internet_scan_sample.pdf")
