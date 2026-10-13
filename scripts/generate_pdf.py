"""Converte RELATORIO.md em RELATORIO.pdf estilizado e profissional.
Utiliza headless LibreOffice com perfil isolado para execução em sandbox.
"""
from pathlib import Path
import re
import subprocess

BASE_DIR = Path(__file__).resolve().parent.parent
MD_PATH = BASE_DIR / "RELATORIO.md"
PDF_PATH = BASE_DIR / "RELATORIO.pdf"
HTML_PATH = BASE_DIR / "outputs" / "relatorio_formatted.html"
PROFILE_DIR = Path("/tmp/lo_relatorio_profile")


def md_to_html(md_text: str) -> str:
    """Conversor simples e robusto de Markdown para HTML estruturado."""
    html_lines = []
    in_table = False
    table_header_done = False
    in_code_block = False

    for line in md_text.splitlines():
        line_stripped = line.strip()

        # Fenced code blocks
        if line_stripped.startswith("```"):
            if in_code_block:
                html_lines.append("</pre>")
                in_code_block = False
            else:
                html_lines.append("<pre>")
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(line.replace("<", "&lt;").replace(">", "&gt;"))
            continue

        # Tables
        if line_stripped.startswith("|") and line_stripped.endswith("|"):
            cells = [c.strip() for c in line_stripped.split("|")[1:-1]]
            if not in_table:
                in_table = True
                table_header_done = False
                html_lines.append("<table>")
            
            # Check if divider line like |---|---|
            if all(re.match(r"^:?-+:?$", c) for c in cells):
                table_header_done = True
                continue

            tag = "td" if table_header_done else "th"
            row_html = "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"
            html_lines.append(row_html)
            continue
        elif in_table:
            html_lines.append("</table>")
            in_table = False

        # Empty lines
        if not line_stripped:
            html_lines.append("<br>")
            continue

        # Headers
        if line_stripped.startswith("### "):
            html_lines.append(f"<h3>{line_stripped[4:]}</h3>")
        elif line_stripped.startswith("## "):
            html_lines.append(f"<h2>{line_stripped[3:]}</h2>")
        elif line_stripped.startswith("# "):
            html_lines.append(f"<h1>{line_stripped[2:]}</h1>")
        elif line_stripped.startswith("---"):
            html_lines.append("<hr>")
        elif line_stripped.startswith("* ") or line_stripped.startswith("- "):
            html_lines.append(f"<li>{line_stripped[2:]}</li>")
        elif re.match(r"^\d+\.\s", line_stripped):
            content = re.sub(r"^\d+\.\s", "", line_stripped)
            html_lines.append(f"<li>{content}</li>")
        else:
            # Paragraph
            html_lines.append(f"<p>{line_stripped}</p>")

    if in_table:
        html_lines.append("</table>")
    if in_code_block:
        html_lines.append("</pre>")

    body = "\n".join(html_lines)

    # Basic markdown inline formatting: bold, italic, code
    body = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", body)
    body = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", body)
    body = re.sub(r"`([^`]+)`", r"<code>\1</code>", body)

    full_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório Técnico - Case Classificação de Tópicos (Método VDE)</title>
<style>
  @page {{
    size: A4;
    margin: 1.1cm 1.1cm 1.1cm 1.1cm;
  }}
  body {{
    font-family: 'Liberation Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-size: 8.5pt;
    line-height: 1.25;
    color: #1a1a1a;
    background: #ffffff;
  }}
  h1 {{
    font-size: 13pt;
    color: #0f2d59;
    border-bottom: 1.5px solid #0f2d59;
    padding-bottom: 2px;
    margin-top: 4px;
    margin-bottom: 5px;
  }}
  h2 {{
    font-size: 10pt;
    color: #1b4984;
    border-bottom: 1px solid #d0d7de;
    padding-bottom: 2px;
    margin-top: 8px;
    margin-bottom: 3px;
  }}
  h3 {{
    font-size: 8.8pt;
    color: #2b3b4c;
    margin-top: 5px;
    margin-bottom: 2px;
  }}
  p {{
    margin: 2px 0 2px 0;
    text-align: justify;
  }}
  li {{
    margin: 1px 0 1px 12px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 4px 0;
    font-size: 7.2pt;
  }}
  th, td {{
    border: 1px solid #c8d1dc;
    padding: 2.5px 4px;
    text-align: left;
    vertical-align: top;
  }}
  th {{
    background-color: #f1f5f9;
    font-weight: bold;
    color: #0f2d59;
  }}
  tr:nth-child(even) td {{
    background-color: #fafbfc;
  }}
  code {{
    font-family: 'Liberation Mono', 'Courier New', Courier, monospace;
    font-size: 7.5pt;
    background-color: #f3f4f6;
    padding: 1px 2px;
    border-radius: 2px;
    border: 1px solid #e2e8f0;
  }}
  pre {{
    font-family: 'Liberation Mono', 'Courier New', Courier, monospace;
    font-size: 6.8pt;
    background-color: #f8fafc;
    padding: 4px;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 3px 0;
  }}
  hr {{
    border: none;
    border-top: 1px solid #cbd5e1;
    margin: 6px 0;
  }}
</style>
</head>
<body>
{body}
</body>
</html>"""
    return full_html


def generate_pdf():
    if not MD_PATH.exists():
        print(f"Erro: {MD_PATH} não encontrado.")
        return

    print(f"Lendo {MD_PATH}...")
    md_text = MD_PATH.read_text(encoding="utf-8")

    html_content = md_to_html(md_text)
    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    HTML_PATH.write_text(html_content, encoding="utf-8")
    print(f"HTML intermediário salvo em {HTML_PATH}")

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print("Gerando PDF com LibreOffice headless...")

    cmd = [
        "libreoffice",
        f"-env:UserInstallation=file://{PROFILE_DIR}",
        "--headless",
        "--convert-to",
        "pdf",
        str(HTML_PATH),
        "--outdir",
        str(BASE_DIR),
    ]

    subprocess.run(cmd, check=True)

    generated_pdf = BASE_DIR / "relatorio_formatted.pdf"
    if generated_pdf.exists():
        generated_pdf.replace(PDF_PATH)

    print(f"PDF gerado com sucesso em: {PDF_PATH} ({PDF_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    generate_pdf()
