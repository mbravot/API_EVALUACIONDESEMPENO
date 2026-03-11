from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import logging
import uuid

logger = logging.getLogger(__name__)

evaluador_bp = Blueprint('evaluador_bp', __name__)

# Endpoint para obtener las evaluaciones realizadas por el usuario logueado
@evaluador_bp.route('/mis-evaluaciones', methods=['GET', 'OPTIONS'])
@jwt_required()
def obtener_mis_evaluaciones():
    """
    Obtiene las evaluaciones realizadas por el usuario logueado.
    Filtra por id_usuarioevaluador en rrhh_dim_colaboradorevaluacion y trae
    los datos de la fact rrhh_fact_evaluacion más datos de dimensión (evaluador/evaluado).
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        usuario_id = get_jwt_identity()
        if not usuario_id:
            return jsonify({"error": "Usuario no identificado"}), 401
        usuario_id = str(usuario_id).strip()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # rrhh_fact_evaluacion: incluir cargo evaluador, cargo evaluado, sucursal
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
            WHERE TRIM(d.id_usuarioevaluador) = TRIM(%s)
            ORDER BY f.fecha DESC, f.id DESC
        """
        cursor.execute(sql, (usuario_id,))
        filas = cursor.fetchall()

        if not filas:
            cursor.close()
            conn.close()
            return jsonify([]), 200

        ids_evaluacion = [r['id_evaluacion'] for r in filas]
        placeholders = ','.join(['%s'] * len(ids_evaluacion))

        # Funciones por evaluación (rrhh_fact_evaluacionfuncion + nombre función)
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

        # Competencias por evaluación (rrhh_fact_evaluacioncompetencia + nombre y definición desde competencia-nivel)
        cursor.execute(f"""
            SELECT ec.id_evaluacion, ec.id_cargocompetencia, ec.nota,
                   cc.id_competencianivel, c.nombre AS nombre_competencia, cn.definicion
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
                'id_competencianivel': int(row['id_competencianivel']) if row.get('id_competencianivel') is not None else None,
                'nota': int(row['nota']) if row.get('nota') is not None else None,
                'nombre_competencia': row.get('nombre_competencia'),
                'definicion': row.get('definicion'),
            })

        # Plan de trabajo por evaluación
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
        logger.exception("Error en obtener_mis_evaluaciones")
        return jsonify({"error": str(e)}), 500

# Endpoint para listar las evaluaciones pendientes del usuario logueado
@evaluador_bp.route('/evaluaciones-pendientes', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_evaluaciones_pendientes():
    """
    Lista las evaluaciones que debe realizar el usuario logueado (asignadas en rrhh_dim_colaboradorevaluacion).
    Incluye indicador si ya fue realizada (existe en rrhh_fact_evaluacion).
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        usuario_id = get_jwt_identity()
        if not usuario_id:
            return jsonify({"error": "Usuario no identificado"}), 401
        usuario_id = str(usuario_id).strip()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT
                d.id AS id_dim_colaborador_evaluacion,
                d.id_evaluador,
                d.id_evaluado,
                d.id_cargoevaluador,
                d.id_cargoevaluado,
                d.id_sucursal,
                d.id_nivel,
                d.correo AS correo_dim,
                col_eval.nombre AS evaluador_nombre,
                col_eval.apellido_paterno AS evaluador_apellido_paterno,
                col_eval.apellido_materno AS evaluador_apellido_materno,
                col_evaldo.nombre AS evaluado_nombre,
                col_evaldo.apellido_paterno AS evaluado_apellido_paterno,
                col_evaldo.apellido_materno AS evaluado_apellido_materno,
                (SELECT f.id FROM rrhh_fact_evaluacion f
                 WHERE f.id_evaluador = d.id_evaluador AND f.id_evaluado = d.id_evaluado
                 LIMIT 1) AS id_evaluacion_realizada
            FROM rrhh_dim_colaboradorevaluacion d
            LEFT JOIN general_dim_colaborador col_eval ON d.id_evaluador = col_eval.id
            LEFT JOIN general_dim_colaborador col_evaldo ON d.id_evaluado = col_evaldo.id
            WHERE TRIM(d.id_usuarioevaluador) = TRIM(%s)
            ORDER BY d.id
        """
        cursor.execute(sql, (usuario_id,))
        filas = cursor.fetchall()

        items = []
        for r in filas:
            items.append({
                'id_dim_colaborador_evaluacion': r.get('id_dim_colaborador_evaluacion'),
                'id_evaluador': r.get('id_evaluador'),
                'id_evaluado': r.get('id_evaluado'),
                'id_cargoevaluador': r.get('id_cargoevaluador'),
                'id_cargoevaluado': r.get('id_cargoevaluado'),
                'id_sucursal': r.get('id_sucursal'),
                'id_nivel': r.get('id_nivel'),
                'correo_dim': r.get('correo_dim'),
                'evaluador_nombre': _nombre_completo(r, 'evaluador'),
                'evaluado_nombre': _nombre_completo(r, 'evaluado'),
                'realizada': r.get('id_evaluacion_realizada') is not None,
                'id_evaluacion_realizada': r.get('id_evaluacion_realizada'),
            })

        cursor.close()
        conn.close()
        return jsonify(items), 200
    except Exception as e:
        logger.exception("Error en listar_evaluaciones_pendientes")
        return jsonify({"error": str(e)}), 500

# Endpoint para crear una evaluación de desempeño
@evaluador_bp.route('/evaluaciones', methods=['POST', 'OPTIONS'])
@jwt_required()
def crear_evaluacion():
    """
    Crea una evaluación de desempeño completa: cabecera (rrhh_fact_evaluacion),
    notas de competencias (rrhh_fact_evaluacioncompetencia), notas de funciones
    (rrhh_fact_evaluacionfuncion) y plan de trabajo (rrhh_fact_plantrabajo).
    El usuario logueado debe ser id_usuarioevaluador en la dimensión para el par (id_evaluador, id_evaluado).
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        usuario_id = get_jwt_identity()
        if not usuario_id:
            return jsonify({"error": "Usuario no identificado"}), 401
        usuario_id = str(usuario_id).strip()

        data = request.get_json()
        if not data:
            return jsonify({"error": "Cuerpo JSON requerido"}), 400

        id_evaluador = data.get('id_evaluador')
        id_evaluado = data.get('id_evaluado')
        id_cargoevaluador = data.get('id_cargoevaluador')
        id_cargoevaluado = data.get('id_cargoevaluado')
        fecha = data.get('fecha')
        notafinal = data.get('notafinal')

        if not all([id_evaluador, id_evaluado, id_cargoevaluador is not None, id_cargoevaluado is not None, fecha, notafinal is not None]):
            return jsonify({
                "error": "Faltan campos requeridos: id_evaluador, id_evaluado, id_cargoevaluador, id_cargoevaluado, fecha, notafinal"
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Validar que el par existe en la dimensión y que el usuario logueado es el evaluador asignado
        cursor.execute("""
            SELECT id, id_sucursal FROM rrhh_dim_colaboradorevaluacion
            WHERE id_evaluador = %s AND id_evaluado = %s AND TRIM(COALESCE(id_usuarioevaluador,'')) = TRIM(%s)
        """, (id_evaluador, id_evaluado, usuario_id))
        dim = cursor.fetchone()
        if not dim:
            cursor.close()
            conn.close()
            return jsonify({"error": "No está asignado como evaluador para este par evaluador/evaluado o el par no existe"}), 403

        # Evitar duplicado: ya existe evaluación para este par
        cursor.execute("""
            SELECT id FROM rrhh_fact_evaluacion WHERE id_evaluador = %s AND id_evaluado = %s
        """, (id_evaluador, id_evaluado))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Ya existe una evaluación para este evaluador/evaluado"}), 409

        id_sucursal = data.get('id_sucursal') if data.get('id_sucursal') is not None else dim.get('id_sucursal')
        comentarioevaluador = data.get('comentarioevaluador') or None
        comentarioevaluado = data.get('comentarioevaluado') or None
        factorbono = data.get('factorbono') if data.get('factorbono') is not None else None
        firmaevaluador = data.get('firmaevaluador') or None
        firmaevaluado = data.get('firmaevaluado') or None

        # Normalizar fecha (aceptar YYYY-MM-DD o ISO)
        if isinstance(fecha, str):
            fecha = fecha.strip()[:10]
        id_evaluacion = str(uuid.uuid4())

        try:
            cursor.execute("""
                INSERT INTO rrhh_fact_evaluacion
                (id, id_evaluador, id_cargoevaluador, id_evaluado, id_cargoevaluado, fecha,
                 comentarioevaluador, comentarioevaluado, notafinal, factorbono, firmaevaluador, firmaevaluado, id_sucursal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                id_evaluacion, id_evaluador, id_cargoevaluador, id_evaluado, id_cargoevaluado, fecha,
                comentarioevaluador, comentarioevaluado, int(notafinal), factorbono, firmaevaluador, firmaevaluado, id_sucursal
            ))

            competencias = data.get('competencias') or []
            id_cargo_evdo = int(id_cargoevaluado)  # pivot.id_cargo es int
            for item in competencias:
                if not isinstance(item, dict):
                    continue
                nota = item.get('nota') if item.get('nota') is not None else item.get('puntuacion')
                if nota is None:
                    logger.warning("Competencia sin nota/puntuacion, se omite: %s", item)
                    continue
                # Aceptar id_cargocompetencia (pivot id) o id_competencianivel (resolver desde pivot)
                id_cargocompetencia = item.get('id_cargocompetencia')
                if id_cargocompetencia is None:
                    id_competencianivel = item.get('id_competencianivel') or item.get('id')  # "id" = id competencianivel en disponibles
                    if id_competencianivel is None:
                        logger.warning("Competencia sin id_cargocompetencia ni id_competencianivel: %s", item)
                        continue
                    try:
                        id_cn = int(id_competencianivel)
                    except (TypeError, ValueError):
                        continue
                    cursor.execute(
                        "SELECT id FROM rrhh_pivot_cargocompetencia WHERE id_cargo = %s AND id_competencianivel = %s",
                        (id_cargo_evdo, id_cn)
                    )
                    pivot = cursor.fetchone()
                    if pivot:
                        id_cargocompetencia = pivot['id']
                    else:
                        # Crear pivot si no existe (no es obligatorio tenerlo previamente asignado al cargo)
                        cursor.execute(
                            "INSERT INTO rrhh_pivot_cargocompetencia (id_cargo, id_competencianivel) VALUES (%s, %s)",
                            (id_cargo_evdo, id_cn)
                        )
                        id_cargocompetencia = cursor.lastrowid
                else:
                    try:
                        id_cargocompetencia = int(id_cargocompetencia)
                    except (TypeError, ValueError):
                        continue
                cursor.execute("""
                    INSERT INTO rrhh_fact_evaluacioncompetencia (id, id_evaluacion, id_cargocompetencia, nota)
                    VALUES (%s, %s, %s, %s)
                """, (str(uuid.uuid4()), id_evaluacion, id_cargocompetencia, int(nota)))

            funciones = data.get('funciones') or []
            for item in funciones:
                id_cargofuncion = item.get('id_cargofuncion')
                nota = item.get('nota')
                if id_cargofuncion is None or nota is None:
                    continue
                cursor.execute("""
                    INSERT INTO rrhh_fact_evaluacionfuncion (id, id_evaluacion, id_cargofuncion, nota)
                    VALUES (%s, %s, %s, %s)
                """, (str(uuid.uuid4()), id_evaluacion, int(id_cargofuncion), int(nota)))

            plan_trabajo = data.get('plan_trabajo') or []
            for item in plan_trabajo:
                cursor.execute("""
                    INSERT INTO rrhh_fact_plantrabajo (id, id_evaluacion, objetivo, accionesesperadas, seguimiento, fechalimitetermino)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()), id_evaluacion,
                    (item.get('objetivo') or None),
                    (item.get('accionesesperadas') or None),
                    (item.get('seguimiento') or None),
                    item.get('fechalimitetermino')
                ))

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

        return jsonify({
            "id_evaluacion": id_evaluacion,
            "mensaje": "Evaluación creada correctamente"
        }), 201
    except Exception as e:
        logger.exception("Error en crear_evaluacion")
        return jsonify({"error": str(e)}), 500

# Endpoint para actualizar una evaluación
@evaluador_bp.route('/evaluaciones/<id_evaluacion>', methods=['PUT', 'PATCH', 'OPTIONS'])
@jwt_required()
def actualizar_evaluacion(id_evaluacion):
    """
    Actualiza una evaluación existente. Solo el usuario que es id_usuarioevaluador puede editarla.
    Body: mismos campos que crear (fecha, comentarioevaluador, comentarioevaluado, notafinal, factorbono,
    firmaevaluador, firmaevaluado, id_sucursal, competencias, funciones, plan_trabajo). Los enviados reemplazan.
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        usuario_id = get_jwt_identity()
        if not usuario_id:
            return jsonify({"error": "Usuario no identificado"}), 401
        usuario_id = str(usuario_id).strip()
        data = request.get_json() or {}

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT f.id, f.id_evaluador, f.id_evaluado, f.id_cargoevaluado
            FROM rrhh_fact_evaluacion f
            INNER JOIN rrhh_dim_colaboradorevaluacion d
                ON d.id_evaluador = f.id_evaluador AND d.id_evaluado = f.id_evaluado
            WHERE f.id = %s AND TRIM(COALESCE(d.id_usuarioevaluador,'')) = TRIM(%s)
        """, (id_evaluacion, usuario_id))
        ev = cursor.fetchone()
        if not ev:
            cursor.close()
            conn.close()
            return jsonify({"error": "Evaluación no encontrada o no tiene permiso para editarla"}), 404

        id_cargoevaluado = ev['id_cargoevaluado']
        updates = []
        params = []
        if 'fecha' in data and data['fecha'] is not None:
            fecha = data['fecha']
            if isinstance(fecha, str):
                fecha = fecha.strip()[:10]
            updates.append("fecha = %s")
            params.append(fecha)
        if 'comentarioevaluador' in data:
            updates.append("comentarioevaluador = %s")
            params.append(data.get('comentarioevaluador') or None)
        if 'comentarioevaluado' in data:
            updates.append("comentarioevaluado = %s")
            params.append(data.get('comentarioevaluado') or None)
        if 'notafinal' in data and data['notafinal'] is not None:
            updates.append("notafinal = %s")
            params.append(int(data['notafinal']))
        if 'factorbono' in data:
            updates.append("factorbono = %s")
            params.append(data.get('factorbono'))
        if 'firmaevaluador' in data:
            updates.append("firmaevaluador = %s")
            params.append(data.get('firmaevaluador') or None)
        if 'firmaevaluado' in data:
            updates.append("firmaevaluado = %s")
            params.append(data.get('firmaevaluado') or None)
        if 'id_sucursal' in data and data['id_sucursal'] is not None:
            updates.append("id_sucursal = %s")
            params.append(data['id_sucursal'])

        if updates:
            params.append(id_evaluacion)
            cursor.execute(
                "UPDATE rrhh_fact_evaluacion SET " + ", ".join(updates) + " WHERE id = %s",
                params
            )

        if 'competencias' in data:
            cursor.execute("DELETE FROM rrhh_fact_evaluacioncompetencia WHERE id_evaluacion = %s", (id_evaluacion,))
            id_cargo_evdo = int(id_cargoevaluado)
            for item in data.get('competencias') or []:
                if not isinstance(item, dict):
                    continue
                nota = item.get('nota') if item.get('nota') is not None else item.get('puntuacion')
                if nota is None:
                    continue
                id_cargocompetencia = item.get('id_cargocompetencia')
                if id_cargocompetencia is None:
                    id_competencianivel = item.get('id_competencianivel') or item.get('id')
                    if id_competencianivel is None:
                        continue
                    try:
                        id_cn = int(id_competencianivel)
                    except (TypeError, ValueError):
                        continue
                    cursor.execute(
                        "SELECT id FROM rrhh_pivot_cargocompetencia WHERE id_cargo = %s AND id_competencianivel = %s",
                        (id_cargo_evdo, id_cn)
                    )
                    pivot = cursor.fetchone()
                    if pivot:
                        id_cargocompetencia = pivot['id']
                    else:
                        cursor.execute(
                            "INSERT INTO rrhh_pivot_cargocompetencia (id_cargo, id_competencianivel) VALUES (%s, %s)",
                            (id_cargo_evdo, id_cn)
                        )
                        id_cargocompetencia = cursor.lastrowid
                else:
                    try:
                        id_cargocompetencia = int(id_cargocompetencia)
                    except (TypeError, ValueError):
                        continue
                cursor.execute("""
                    INSERT INTO rrhh_fact_evaluacioncompetencia (id, id_evaluacion, id_cargocompetencia, nota)
                    VALUES (%s, %s, %s, %s)
                """, (str(uuid.uuid4()), id_evaluacion, id_cargocompetencia, int(nota)))

        if 'funciones' in data:
            cursor.execute("DELETE FROM rrhh_fact_evaluacionfuncion WHERE id_evaluacion = %s", (id_evaluacion,))
            for item in data.get('funciones') or []:
                id_cargofuncion = item.get('id_cargofuncion')
                nota = item.get('nota')
                if id_cargofuncion is None or nota is None:
                    continue
                cursor.execute("""
                    INSERT INTO rrhh_fact_evaluacionfuncion (id, id_evaluacion, id_cargofuncion, nota)
                    VALUES (%s, %s, %s, %s)
                """, (str(uuid.uuid4()), id_evaluacion, int(id_cargofuncion), int(nota)))

        if 'plan_trabajo' in data:
            cursor.execute("DELETE FROM rrhh_fact_plantrabajo WHERE id_evaluacion = %s", (id_evaluacion,))
            for item in data.get('plan_trabajo') or []:
                cursor.execute("""
                    INSERT INTO rrhh_fact_plantrabajo (id, id_evaluacion, objetivo, accionesesperadas, seguimiento, fechalimitetermino)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()), id_evaluacion,
                    (item.get('objetivo') or None),
                    (item.get('accionesesperadas') or None),
                    (item.get('seguimiento') or None),
                    item.get('fechalimitetermino')
                ))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"id_evaluacion": id_evaluacion, "mensaje": "Evaluación actualizada correctamente"}), 200
    except Exception as e:
        logger.exception("Error en actualizar_evaluacion")
        return jsonify({"error": str(e)}), 500

# Endpoint para eliminar una evaluación
@evaluador_bp.route('/evaluaciones/<id_evaluacion>', methods=['DELETE', 'OPTIONS'])
@jwt_required()
def eliminar_evaluacion(id_evaluacion):
    """Elimina una evaluación. Solo el usuario que es id_usuarioevaluador puede eliminarla."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        usuario_id = get_jwt_identity()
        if not usuario_id:
            return jsonify({"error": "Usuario no identificado"}), 401
        usuario_id = str(usuario_id).strip()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT f.id FROM rrhh_fact_evaluacion f
            INNER JOIN rrhh_dim_colaboradorevaluacion d
                ON d.id_evaluador = f.id_evaluador AND d.id_evaluado = f.id_evaluado
            WHERE f.id = %s AND TRIM(COALESCE(d.id_usuarioevaluador,'')) = TRIM(%s)
        """, (id_evaluacion, usuario_id))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Evaluación no encontrada o no tiene permiso para eliminarla"}), 404

        cursor.execute("DELETE FROM rrhh_fact_evaluacioncompetencia WHERE id_evaluacion = %s", (id_evaluacion,))
        cursor.execute("DELETE FROM rrhh_fact_evaluacionfuncion WHERE id_evaluacion = %s", (id_evaluacion,))
        cursor.execute("DELETE FROM rrhh_fact_plantrabajo WHERE id_evaluacion = %s", (id_evaluacion,))
        cursor.execute("DELETE FROM rrhh_fact_evaluacion WHERE id = %s", (id_evaluacion,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"mensaje": "Evaluación eliminada correctamente"}), 200
    except Exception as e:
        logger.exception("Error en eliminar_evaluacion")
        return jsonify({"error": str(e)}), 500


def _nombre_completo(r, prefijo):
    """Arma nombre completo desde nombre + apellido_paterno + apellido_materno de general_dim_colaborador."""
    n = r.get(prefijo + '_nombre') or ''
    p = r.get(prefijo + '_apellido_paterno') or ''
    m = r.get(prefijo + '_apellido_materno') or ''
    return ' '.join(filter(None, [n, p, m])).strip() or None
