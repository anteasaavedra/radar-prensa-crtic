"""
Generador de reporte Excel multi-hoja para Radar de Prensa CRTIC.

Uso:
    from app.excel_export import generate_excel_report
    excel_bytes = generate_excel_report(df)
    # → pasar a st.download_button(data=excel_bytes, ...)
"""
from io import BytesIO
import pandas as pd
from datetime import datetime


def generate_excel_report(df: pd.DataFrame) -> bytes:
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Hoja Menciones
        df.to_excel(writer, index=False, sheet_name="Menciones")

        # Hoja Resumen
        resumen = pd.DataFrame({
            "Indicador": [
                "Fecha de generación",
                "Total de menciones",
                "VEM total estimado",
                "Menciones positivas",
                "Menciones neutras",
                "Menciones negativas",
                "Alta relevancia",
                "Media relevancia",
                "Baja relevancia",
            ],
            "Valor": [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                len(df),
                df["vem"].sum() if "vem" in df.columns else 0,
                (df["sentimiento"] == "Positivo").sum() if "sentimiento" in df.columns else 0,
                (df["sentimiento"] == "Neutro").sum()   if "sentimiento" in df.columns else 0,
                (df["sentimiento"] == "Negativo").sum() if "sentimiento" in df.columns else 0,
                (df["relevancia"]  == "Alta").sum()     if "relevancia"  in df.columns else 0,
                (df["relevancia"]  == "Media").sum()    if "relevancia"  in df.columns else 0,
                (df["relevancia"]  == "Baja").sum()     if "relevancia"  in df.columns else 0,
            ],
        })
        resumen.to_excel(writer, index=False, sheet_name="Resumen")

        # Hoja Top menciones por VEM
        top = (
            df.sort_values("vem", ascending=False).head(20)
            if "vem" in df.columns
            else df.head(20)
        )
        top.to_excel(writer, index=False, sheet_name="Top VEM")

        # Hoja Alertas (negativas + alta relevancia)
        if not df.empty and "sentimiento" in df.columns and "relevancia" in df.columns:
            alertas = df[
                (df["sentimiento"] == "Negativo") | (df["relevancia"] == "Alta")
            ]
        else:
            alertas = df
        alertas.to_excel(writer, index=False, sheet_name="Alertas")

        # Formato para todas las hojas
        for sheet_name, ws in writer.sheets.items():
            # Encabezados en negrita
            for cell in ws[1]:
                cell.font = cell.font.copy(bold=True)

            # Filtros automáticos
            ws.auto_filter.ref = ws.dimensions

            # Ancho automático de columnas
            for column_cells in ws.columns:
                col_letter = column_cells[0].column_letter
                max_length = max(
                    (len(str(cell.value)) for cell in column_cells if cell.value is not None),
                    default=10,
                )
                ws.column_dimensions[col_letter].width = min(max_length + 2, 60)

    output.seek(0)
    return output.getvalue()
