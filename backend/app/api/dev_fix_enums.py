"""
Endpoint temporal para actualizar TODOS los valores de enum a MAYÚSCULAS.
Solo para desarrollo - ELIMINAR EN PRODUCCIÓN
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, text

from app.core.database import get_session

router = APIRouter(prefix="/dev/fix", tags=["dev-fix-enums"])


# Mapeos de valores minúsculas -> MAYÚSCULAS para cada enum
ENUM_MAPPINGS = {
    # EstadoCamaEnum
    "estadocamaenum": {
        "libre": "LIBRE",
        "ocupada": "OCUPADA",
        "traslado_entrante": "TRASLADO_ENTRANTE",
        "cama_en_espera": "CAMA_EN_ESPERA",
        "traslado_saliente": "TRASLADO_SALIENTE",
        "traslado_confirmado": "TRASLADO_CONFIRMADO",
        "alta_sugerida": "ALTA_SUGERIDA",
        "cama_alta": "CAMA_ALTA",
        "en_limpieza": "EN_LIMPIEZA",
        "bloqueada": "BLOQUEADA",
        "espera_derivacion": "ESPERA_DERIVACION",
        "derivacion_confirmada": "DERIVACION_CONFIRMADA",
        "fallecido": "FALLECIDO",
        "reservada": "RESERVADA",
    },
    # TipoPacienteEnum
    "tipopacienteenum": {
        "urgencia": "URGENCIA",
        "ambulatorio": "AMBULATORIO",
        "hospitalizado": "HOSPITALIZADO",
        "derivado": "DERIVADO",
    },
    # SexoEnum
    "sexoenum": {
        "hombre": "HOMBRE",
        "mujer": "MUJER",
    },
    # TipoEnfermedadEnum
    "tipoenfermedadenum": {
        "medica": "MEDICA",
        "quirurgica": "QUIRURGICA",
        "traumatologica": "TRAUMATOLOGICA",
        "neurologica": "NEUROLOGICA",
        "urologica": "UROLOGICA",
        "geriatrica": "GERIATRICA",
        "ginecologica": "GINECOLOGICA",
        "obstetrica": "OBSTETRICA",
    },
    # TipoAislamientoEnum
    "tipoaislamientoenum": {
        "ninguno": "NINGUNO",
        "contacto": "CONTACTO",
        "gotitas": "GOTITAS",
        "aereo": "AEREO",
        "ambiente_protegido": "AMBIENTE_PROTEGIDO",
        "especial": "ESPECIAL",
    },
    # ComplejidadEnum
    "complejidadenum": {
        "ninguna": "NINGUNA",
        "baja": "BAJA",
        "media": "MEDIA",
        "alta": "ALTA",
    },
    # TipoServicioEnum
    "tiposervicioenum": {
        "uci": "UCI",
        "uti": "UTI",
        "medicina": "MEDICINA",
        "aislamiento": "AISLAMIENTO",
        "cirugia": "CIRUGIA",
        "obstetricia": "OBSTETRICIA",
        "pediatria": "PEDIATRIA",
        "medico_quirurgico": "MEDICO_QUIRURGICO",
    },
    # EstadoListaEsperaEnum
    "estadolistaesperaenum": {
        "esperando": "ESPERANDO",
        "buscando": "BUSCANDO",
        "asignado": "ASIGNADO",
    },
}

# Tablas y columnas que necesitan actualización
TABLE_COLUMN_ENUM_MAP = {
    "cama": [("estado", "estadocamaenum")],
    "paciente": [
        ("tipo_paciente", "tipopacienteenum"),
        ("sexo", "sexoenum"),
        ("tipo_enfermedad", "tipoenfermedadenum"),
        ("tipo_aislamiento", "tipoaislamientoenum"),
        ("complejidad_requerida", "complejidadenum"),
        ("estado_lista_espera", "estadolistaesperaenum"),
    ],
    "servicio": [("tipo", "tiposervicioenum")],
}


@router.get("/update-all-enums")
@router.post("/update-all-enums")
def update_all_enums(session: Session = Depends(get_session)):
    """
    Actualiza TODOS los valores de enum en la BD a MAYÚSCULAS.
    ⚠️ SOLO PARA DESARROLLO - EJECUTAR UNA SOLA VEZ

    Disponible como GET y POST para facilitar ejecución desde navegador.
    """
    results = []
    errors = []

    try:
        for table_name, columns in TABLE_COLUMN_ENUM_MAP.items():
            for column_name, enum_type in columns:
                try:
                    mapping = ENUM_MAPPINGS.get(enum_type, {})

                    if not mapping:
                        errors.append({
                            "table": table_name,
                            "column": column_name,
                            "error": f"No mapping found for enum type: {enum_type}"
                        })
                        continue

                    updated_count = 0
                    for old_value, new_value in mapping.items():
                        try:
                            # Actualizar valores usando CASE para mejor performance
                            update_sql = text(f"""
                                UPDATE {table_name}
                                SET {column_name} = :new_value
                                WHERE {column_name} = :old_value
                            """)

                            result = session.execute(update_sql, {
                                "new_value": new_value,
                                "old_value": old_value
                            })

                            if result.rowcount > 0:
                                updated_count += result.rowcount

                        except Exception as e:
                            session.rollback()  # Rollback en caso de error
                            errors.append({
                                "table": table_name,
                                "column": column_name,
                                "old_value": old_value,
                                "new_value": new_value,
                                "error": str(e)
                            })

                    if updated_count > 0:
                        results.append({
                            "table": table_name,
                            "column": column_name,
                            "enum_type": enum_type,
                            "updated_rows": updated_count
                        })
                        # Commit después de cada columna exitosa
                        session.commit()

                except Exception as e:
                    session.rollback()
                    errors.append({
                        "table": table_name,
                        "column": column_name,
                        "error": str(e)
                    })

        total_updated = sum(r["updated_rows"] for r in results)

        return {
            "status": "success" if not errors else "partial",
            "total_updated_rows": total_updated,
            "tables_updated": len(results),
            "details": results,
            "errors": errors if errors else None,
            "message": f"✅ Actualizados {total_updated} registros en {len(results)} tablas/columnas"
        }

    except Exception as e:
        session.rollback()
        return {
            "status": "error",
            "message": "Error al actualizar enums",
            "error": str(e)
        }


@router.get("/check-enum-values")
def check_enum_values(session: Session = Depends(get_session)):
    """
    Verifica el estado de los valores de enum en las tablas principales.
    ⚠️ SOLO PARA DESARROLLO
    """
    try:
        results = []

        # Verificar estados de camas
        camas_result = session.exec(text("""
            SELECT estado, COUNT(*) as count
            FROM cama
            GROUP BY estado
            ORDER BY estado
        """))

        camas_estados = [{"estado": row[0], "count": row[1]} for row in camas_result]

        results.append({
            "table": "cama",
            "column": "estado",
            "values": camas_estados,
            "needs_update": any(e["estado"] and e["estado"].islower() for e in camas_estados if e["estado"])
        })

        # Verificar tipos de servicio
        servicios_result = session.exec(text("""
            SELECT tipo, COUNT(*) as count
            FROM servicio
            GROUP BY tipo
            ORDER BY tipo
        """))

        servicios_tipos = [{"tipo": row[0], "count": row[1]} for row in servicios_result]

        results.append({
            "table": "servicio",
            "column": "tipo",
            "values": servicios_tipos,
            "needs_update": any(t["tipo"] and t["tipo"].islower() for t in servicios_tipos if t["tipo"])
        })

        needs_update = any(r["needs_update"] for r in results)

        return {
            "status": "success",
            "needs_update": needs_update,
            "tables": results,
            "message": "⚠️ Algunos valores necesitan actualización" if needs_update else "✅ Todos los valores están correctos"
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
