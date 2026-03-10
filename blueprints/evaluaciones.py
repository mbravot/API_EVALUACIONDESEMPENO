from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from utils.db import get_db_connection
import logging

logger = logging.getLogger(__name__)

evaluaciones_bp = Blueprint('evaluaciones_bp', __name__)


# Estadísticas globales para el Dashboard
@evaluaciones_bp.route('/estadisticas', methods=['GET', 'OPTIONS'])
@jwt_required()
def get_estadisticas():
    """
    Devuelve total asignadas, realizadas, pendientes y desglose por sucursal.
    Esperado por el front: total_asignadas, realizadas, pendientes, por_sucursal[].
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Totales globales: asignadas = dim, realizadas = fact (por par evaluador-evaluado)
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM rrhh_dim_colaboradorevaluacion) AS total_asignadas,
                (SELECT COUNT(*) FROM rrhh_fact_evaluacion) AS realizadas
        """)
        row = cursor.fetchone()
        total_asignadas = int(row['total_asignadas']) if row else 0
        realizadas = int(row['realizadas']) if row else 0
        pendientes = max(0, total_asignadas - realizadas)

        # Por sucursal: total, realizadas, pendientes (sucursal desde la dimensión)
        cursor.execute("""
            SELECT
                COALESCE(s.nombre, 'Sin sucursal') AS sucursal,
                COUNT(d.id) AS total,
                COUNT(f.id) AS realizadas
            FROM rrhh_dim_colaboradorevaluacion d
            LEFT JOIN rrhh_fact_evaluacion f
                ON d.id_evaluador = f.id_evaluador AND d.id_evaluado = f.id_evaluado
            LEFT JOIN general_dim_sucursal s ON d.id_sucursal = s.id
            GROUP BY d.id_sucursal, s.nombre
            ORDER BY sucursal
        """)
        filas_sucursal = cursor.fetchall()
        por_sucursal = []
        for r in filas_sucursal:
            total_suc = int(r['total']) if r.get('total') is not None else 0
            real_suc = int(r['realizadas']) if r.get('realizadas') is not None else 0
            pend_suc = max(0, total_suc - real_suc)
            por_sucursal.append({
                'sucursal': r.get('sucursal') or 'Sin sucursal',
                'total': total_suc,
                'realizadas': real_suc,
                'pendientes': pend_suc,
            })

        cursor.close()
        conn.close()

        return jsonify({
            'total_asignadas': total_asignadas,
            'realizadas': realizadas,
            'pendientes': pendientes,
            'por_sucursal': por_sucursal,
        }), 200
    except Exception as e:
        logger.exception("Error en get_estadisticas")
        return jsonify({"error": str(e)}), 500


def _nombre_completo(r, prefijo):
    """Arma nombre completo desde nombre + apellido_paterno + apellido_materno de general_dim_colaborador."""
    n = r.get(prefijo + '_nombre') or ''
    p = r.get(prefijo + '_apellido_paterno') or ''
    m = r.get(prefijo + '_apellido_materno') or ''
    return ' '.join(filter(None, [n, p, m])).strip() or None

# Listar todas las evaluaciones
@evaluaciones_bp.route('', methods=['GET', 'OPTIONS'])
@evaluaciones_bp.route('/', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_todas_evaluaciones():
    """
    Obtiene todas las evaluaciones (sin filtrar por usuario).
    Misma estructura que GET /api/evaluador/mis-evaluaciones: cabecera, cargo evaluador/evaluado,
    sucursal, funciones, competencias y plan de trabajo.
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT
                f.id AS id_evaluacion,
                f.id_evaluador, f.id_evaluado, f.id_cargoevaluador, f.id_cargoevaluado, f.id_sucursal,
                f.fecha, f.comentarioevaluador, f.comentarioevaluado, f.notafinal, f.factorbono,
                f.firmaevaluador, f.firmaevaluado,
                d.id AS id_dim_colaborador_evaluacion, d.id_nivel, d.correo AS correo_dim,
                col_eval.nombre AS evaluador_nombre, col_eval.apellido_paterno AS evaluador_apellido_paterno,
                col_eval.apellido_materno AS evaluador_apellido_materno,
                col_evaldo.nombre AS evaluado_nombre, col_evaldo.apellido_paterno AS evaluado_apellido_paterno,
                col_evaldo.apellido_materno AS evaluado_apellido_materno,
                cargo_ev.nombre AS cargo_evaluador_nombre, cargo_evdo.nombre AS cargo_evaluado_nombre,
                suc.nombre AS sucursal_nombre, suc.ubicacion AS sucursal_ubicacion
            FROM rrhh_fact_evaluacion f
            INNER JOIN rrhh_dim_colaboradorevaluacion d
                ON d.id_evaluador = f.id_evaluador AND d.id_evaluado = f.id_evaluado
            LEFT JOIN general_dim_colaborador col_eval ON d.id_evaluador = col_eval.id
            LEFT JOIN general_dim_colaborador col_evaldo ON d.id_evaluado = col_evaldo.id
            LEFT JOIN rrhh_dim_cargo cargo_ev ON f.id_cargoevaluador = cargo_ev.id
            LEFT JOIN rrhh_dim_cargo cargo_evdo ON f.id_cargoevaluado = cargo_evdo.id
            LEFT JOIN general_dim_sucursal suc ON f.id_sucursal = suc.id
            ORDER BY f.fecha DESC, f.id DESC
        """
        cursor.execute(sql)
        filas = cursor.fetchall()

        if not filas:
            cursor.close()
            conn.close()
            return jsonify([]), 200

        ids_evaluacion = [r['id_evaluacion'] for r in filas]
        placeholders = ','.join(['%s'] * len(ids_evaluacion))

        cursor.execute(f"""
            SELECT ef.id_evaluacion, ef.id_cargofuncion, ef.nota, f.nombre AS nombre_funcion
            FROM rrhh_fact_evaluacionfuncion ef
            LEFT JOIN rrhh_pivot_cargofuncion pf ON ef.id_cargofuncion = pf.id
            LEFT JOIN rrhh_dim_funcion f ON pf.id_funcion = f.id
            WHERE ef.id_evaluacion IN ({placeholders})
        """, ids_evaluacion)
        filas_funciones = cursor.fetchall()
        funciones_por_eval = {}
        for row in filas_funciones:
            eid = row['id_evaluacion']
            if eid not in funciones_por_eval:
                funciones_por_eval[eid] = []
            funciones_por_eval[eid].append({
                'id_cargofuncion': row['id_cargofuncion'],
                'nota': int(row['nota']) if row.get('nota') is not None else None,
                'nombre_funcion': row.get('nombre_funcion'),
            })

        cursor.execute(f"""
            SELECT ec.id_evaluacion, ec.id_cargocompetencia, ec.nota,
                   c.nombre AS nombre_competencia
            FROM rrhh_fact_evaluacioncompetencia ec
            LEFT JOIN rrhh_pivot_cargocompetencia cc ON ec.id_cargocompetencia = cc.id
            LEFT JOIN rrhh_dim_competencianivel cn ON cc.id_competencianivel = cn.id
            LEFT JOIN rrhh_dim_competencia c ON cn.id_competencia = c.id
            WHERE ec.id_evaluacion IN ({placeholders})
        """, ids_evaluacion)
        filas_competencias = cursor.fetchall()
        competencias_por_eval = {}
        for row in filas_competencias:
            eid = row['id_evaluacion']
            if eid not in competencias_por_eval:
                competencias_por_eval[eid] = []
            competencias_por_eval[eid].append({
                'id_cargocompetencia': row['id_cargocompetencia'],
                'nota': int(row['nota']) if row.get('nota') is not None else None,
                'nombre_competencia': row.get('nombre_competencia'),
            })

        cursor.execute(f"""
            SELECT id_evaluacion, objetivo, accionesesperadas, seguimiento, fechalimitetermino
            FROM rrhh_fact_plantrabajo
            WHERE id_evaluacion IN ({placeholders})
        """, ids_evaluacion)
        filas_plan = cursor.fetchall()
        plan_por_eval = {}
        for row in filas_plan:
            eid = row['id_evaluacion']
            if eid not in plan_por_eval:
                plan_por_eval[eid] = []
            plan_por_eval[eid].append({
                'objetivo': row.get('objetivo'),
                'accionesesperadas': row.get('accionesesperadas'),
                'seguimiento': row.get('seguimiento'),
                'fechalimitetermino': row['fechalimitetermino'].isoformat() if row.get('fechalimitetermino') else None,
            })

        evaluaciones = []
        for r in filas:
            eid = r['id_evaluacion']
            evaluaciones.append({
                'id_evaluacion': eid,
                'fecha': r['fecha'].isoformat() if r.get('fecha') else None,
                'comentarioevaluador': r.get('comentarioevaluador'),
                'comentarioevaluado': r.get('comentarioevaluado'),
                'notafinal': int(r['notafinal']) if r.get('notafinal') is not None else None,
                'factorbono': int(r['factorbono']) if r.get('factorbono') is not None else None,
                'firmaevaluador': r.get('firmaevaluador'),
                'firmaevaluado': r.get('firmaevaluado'),
                'id_evaluador': r.get('id_evaluador'),
                'id_evaluado': r.get('id_evaluado'),
                'id_cargoevaluador': r.get('id_cargoevaluador'),
                'id_cargoevaluado': r.get('id_cargoevaluado'),
                'id_sucursal': r.get('id_sucursal'),
                'id_nivel': r.get('id_nivel'),
                'evaluador_nombre': _nombre_completo(r, 'evaluador'),
                'evaluado_nombre': _nombre_completo(r, 'evaluado'),
                'cargo_evaluador': r.get('cargo_evaluador_nombre'),
                'cargo_evaluado': r.get('cargo_evaluado_nombre'),
                'sucursal': r.get('sucursal_nombre'),
                'sucursal_ubicacion': r.get('sucursal_ubicacion'),
                'funciones': funciones_por_eval.get(eid, []),
                'competencias': competencias_por_eval.get(eid, []),
                'plan_trabajo': plan_por_eval.get(eid, []),
            })

        cursor.close()
        conn.close()
        return jsonify(evaluaciones), 200
    except Exception as e:
        logger.exception("Error en listar_todas_evaluaciones")
        return jsonify({"error": str(e)}), 500
