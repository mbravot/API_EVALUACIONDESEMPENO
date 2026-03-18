from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from utils.db import get_db_connection
import logging

logger = logging.getLogger(__name__)

colaborador_bp = Blueprint('colaborador_bp', __name__)

# Listar todos los registros de colaborador-evaluación
@colaborador_bp.route('', methods=['GET', 'OPTIONS'])
@colaborador_bp.route('/', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_colaboradorevaluacion():
    """Lista todos los registros de rrhh_dim_colaboradorevaluacion."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ce.id,
                   ce.id_evaluador,
                   ce.id_cargoevaluador,
                   ce.id_evaluado,
                   ce.id_cargoevaluado,
                   ce.id_sucursal,
                   ce.correo,
                   ce.id_nivel,
                   ce.id_usuarioevaluador,
                   col_eval.nombre AS evaluador_nombre,
                   col_eval.apellido_paterno AS evaluador_apellido_paterno,
                   col_eval.apellido_materno AS evaluador_apellido_materno,
                   col_evaldo.nombre AS evaluado_nombre,
                   col_evaldo.apellido_paterno AS evaluado_apellido_paterno,
                   col_evaldo.apellido_materno AS evaluado_apellido_materno
            FROM rrhh_dim_colaboradorevaluacion ce
            LEFT JOIN general_dim_colaborador col_eval ON ce.id_evaluador = col_eval.id
            LEFT JOIN general_dim_colaborador col_evaldo ON ce.id_evaluado = col_evaldo.id
            ORDER BY ce.id
        """)
        filas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([
            {
                "id": r["id"],
                "id_evaluador": r["id_evaluador"],
                "id_cargoevaluador": r["id_cargoevaluador"],
                "id_evaluado": r["id_evaluado"],
                "id_cargoevaluado": r["id_cargoevaluado"],
                "id_sucursal": r["id_sucursal"],
                "correo": r["correo"],
                "id_nivel": r["id_nivel"],
                "id_usuarioevaluador": r["id_usuarioevaluador"],
                "evaluador_nombre": " ".join(
                    filter(
                        None,
                        [
                            r.get("evaluador_nombre"),
                            r.get("evaluador_apellido_paterno"),
                            r.get("evaluador_apellido_materno"),
                        ],
                    )
                ) or None,
                "evaluado_nombre": " ".join(
                    filter(
                        None,
                        [
                            r.get("evaluado_nombre"),
                            r.get("evaluado_apellido_paterno"),
                            r.get("evaluado_apellido_materno"),
                        ],
                    )
                ) or None,
            }
            for r in filas
        ]), 200
    except Exception as e:
        logger.exception("Error en listar_colaboradorevaluacion")
        return jsonify({"error": str(e)}), 500


# Obtener un registro por id
@colaborador_bp.route('/<int:id>', methods=['GET', 'OPTIONS'])
@jwt_required()
def obtener_colaboradorevaluacion(id):
    """Obtiene un registro de rrhh_dim_colaboradorevaluacion por id."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ce.id,
                   ce.id_evaluador,
                   ce.id_cargoevaluador,
                   ce.id_evaluado,
                   ce.id_cargoevaluado,
                   ce.id_sucursal,
                   ce.correo,
                   ce.id_nivel,
                   ce.id_usuarioevaluador,
                   col_eval.nombre AS evaluador_nombre,
                   col_eval.apellido_paterno AS evaluador_apellido_paterno,
                   col_eval.apellido_materno AS evaluador_apellido_materno,
                   col_evaldo.nombre AS evaluado_nombre,
                   col_evaldo.apellido_paterno AS evaluado_apellido_paterno,
                   col_evaldo.apellido_materno AS evaluado_apellido_materno
            FROM rrhh_dim_colaboradorevaluacion ce
            LEFT JOIN general_dim_colaborador col_eval ON ce.id_evaluador = col_eval.id
            LEFT JOIN general_dim_colaborador col_evaldo ON ce.id_evaluado = col_evaldo.id
            WHERE ce.id = %s
        """, (id,))
        r = cursor.fetchone()
        cursor.close()
        conn.close()
        if not r:
            return jsonify({"error": "Registro no encontrado"}), 404
        return jsonify({
            "id": r["id"],
            "id_evaluador": r["id_evaluador"],
            "id_cargoevaluador": r["id_cargoevaluador"],
            "id_evaluado": r["id_evaluado"],
            "id_cargoevaluado": r["id_cargoevaluado"],
            "id_sucursal": r["id_sucursal"],
            "correo": r["correo"],
            "id_nivel": r["id_nivel"],
            "id_usuarioevaluador": r["id_usuarioevaluador"],
            "evaluador_nombre": " ".join(
                filter(
                    None,
                    [
                        r.get("evaluador_nombre"),
                        r.get("evaluador_apellido_paterno"),
                        r.get("evaluador_apellido_materno"),
                    ],
                )
            ) or None,
            "evaluado_nombre": " ".join(
                filter(
                    None,
                    [
                        r.get("evaluado_nombre"),
                        r.get("evaluado_apellido_paterno"),
                        r.get("evaluado_apellido_materno"),
                    ],
                )
            ) or None,
        }), 200
    except Exception as e:
        logger.exception("Error en obtener_colaboradorevaluacion")
        return jsonify({"error": str(e)}), 500


# Crear un nuevo registro
@colaborador_bp.route('', methods=['POST', 'OPTIONS'])
@jwt_required()
def crear_colaboradorevaluacion():
    """Crea un nuevo registro en rrhh_dim_colaboradorevaluacion."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        id_evaluador_raw = data.get('id_evaluador')
        id_evaluador = (str(id_evaluador_raw).strip() if id_evaluador_raw is not None else '')
        id_cargoevaluador = data.get('id_cargoevaluador')
        id_evaluado_raw = data.get('id_evaluado')
        id_evaluado = (str(id_evaluado_raw).strip() if id_evaluado_raw is not None else '')
        id_cargoevaluado = data.get('id_cargoevaluado')
        id_sucursal = data.get('id_sucursal')
        correo_raw = data.get('correo')
        correo = (str(correo_raw).strip() if correo_raw is not None else '') or None
        id_nivel = data.get('id_nivel')
        id_usuarioevaluador_raw = data.get('id_usuarioevaluador')
        id_usuarioevaluador = (str(id_usuarioevaluador_raw).strip() if id_usuarioevaluador_raw is not None else '') or None

        if not id_evaluador or id_cargoevaluador is None or not id_evaluado or id_cargoevaluado is None or id_sucursal is None:
            return jsonify({
                "error": "id_evaluador, id_cargoevaluador, id_evaluado, id_cargoevaluado e id_sucursal son requeridos"
            }), 400

        id_cargoevaluador = int(id_cargoevaluador)
        id_cargoevaluado = int(id_cargoevaluado)
        id_sucursal = int(id_sucursal)
        if id_nivel is not None:
            id_nivel = int(id_nivel)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rrhh_dim_colaboradorevaluacion
            (id_evaluador, id_cargoevaluador, id_evaluado, id_cargoevaluado, id_sucursal, correo, id_nivel, id_usuarioevaluador)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (id_evaluador, id_cargoevaluador, id_evaluado, id_cargoevaluado, id_sucursal, correo, id_nivel, id_usuarioevaluador))
        conn.commit()
        id_nuevo = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({
            "id": id_nuevo,
            "id_evaluador": id_evaluador,
            "id_cargoevaluador": id_cargoevaluador,
            "id_evaluado": id_evaluado,
            "id_cargoevaluado": id_cargoevaluado,
            "id_sucursal": id_sucursal,
            "correo": correo,
            "id_nivel": id_nivel,
            "id_usuarioevaluador": id_usuarioevaluador,
            "mensaje": "Registro creado correctamente",
        }), 201
    except ValueError:
        return jsonify({"error": "id_cargoevaluador, id_cargoevaluado, id_sucursal e id_nivel deben ser números"}), 400
    except Exception as e:
        logger.exception("Error en crear_colaboradorevaluacion")
        return jsonify({"error": str(e)}), 500


# Actualizar un registro
@colaborador_bp.route('/<int:id>', methods=['PUT', 'OPTIONS'])
@jwt_required()
def actualizar_colaboradorevaluacion(id):
    """Actualiza un registro de rrhh_dim_colaboradorevaluacion."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        id_evaluador = data.get('id_evaluador')
        if id_evaluador is not None:
            id_evaluador = str(id_evaluador).strip()
        id_cargoevaluador = data.get('id_cargoevaluador')
        id_evaluado = data.get('id_evaluado')
        if id_evaluado is not None:
            id_evaluado = str(id_evaluado).strip()
        id_cargoevaluado = data.get('id_cargoevaluado')
        id_sucursal = data.get('id_sucursal')
        correo = data.get('correo')
        if correo is not None:
            correo = (correo or '').strip() or None
        id_nivel = data.get('id_nivel')
        id_usuarioevaluador = data.get('id_usuarioevaluador')
        if id_usuarioevaluador is not None:
            id_usuarioevaluador = str(id_usuarioevaluador).strip() or None

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, id_evaluador, id_cargoevaluador, id_evaluado, id_cargoevaluado,
                   id_sucursal, correo, id_nivel, id_usuarioevaluador
            FROM rrhh_dim_colaboradorevaluacion WHERE id = %s
        """, (id,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            return jsonify({"error": "Registro no encontrado"}), 404

        id_evaluador_f = id_evaluador if id_evaluador is not None else row["id_evaluador"]
        id_cargoevaluador_f = int(id_cargoevaluador) if id_cargoevaluador is not None else row["id_cargoevaluador"]
        id_evaluado_f = id_evaluado if id_evaluado is not None else row["id_evaluado"]
        id_cargoevaluado_f = int(id_cargoevaluado) if id_cargoevaluado is not None else row["id_cargoevaluado"]
        id_sucursal_f = int(id_sucursal) if id_sucursal is not None else row["id_sucursal"]
        correo_f = correo if 'correo' in data else row["correo"]
        id_nivel_f = int(id_nivel) if id_nivel is not None else (row["id_nivel"] if 'id_nivel' not in data else None)
        id_usuarioevaluador_f = id_usuarioevaluador if 'id_usuarioevaluador' in data else row["id_usuarioevaluador"]

        cursor.execute("""
            UPDATE rrhh_dim_colaboradorevaluacion
            SET id_evaluador = %s, id_cargoevaluador = %s, id_evaluado = %s, id_cargoevaluado = %s,
                id_sucursal = %s, correo = %s, id_nivel = %s, id_usuarioevaluador = %s
            WHERE id = %s
        """, (id_evaluador_f, id_cargoevaluador_f, id_evaluado_f, id_cargoevaluado_f,
              id_sucursal_f, correo_f, id_nivel_f, id_usuarioevaluador_f, id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            "id": id,
            "id_evaluador": id_evaluador_f,
            "id_cargoevaluador": id_cargoevaluador_f,
            "id_evaluado": id_evaluado_f,
            "id_cargoevaluado": id_cargoevaluado_f,
            "id_sucursal": id_sucursal_f,
            "correo": correo_f,
            "id_nivel": id_nivel_f,
            "id_usuarioevaluador": id_usuarioevaluador_f,
            "mensaje": "Registro actualizado correctamente",
        }), 200
    except ValueError:
        return jsonify({"error": "id_cargoevaluador, id_cargoevaluado, id_sucursal e id_nivel deben ser números"}), 400
    except Exception as e:
        logger.exception("Error en actualizar_colaboradorevaluacion")
        return jsonify({"error": str(e)}), 500


# Eliminar un registro
@colaborador_bp.route('/<int:id>', methods=['DELETE', 'OPTIONS'])
@jwt_required()
def eliminar_colaboradorevaluacion(id):
    """Elimina un registro de rrhh_dim_colaboradorevaluacion."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rrhh_dim_colaboradorevaluacion WHERE id = %s", (id,))
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Registro no encontrado"}), 404
        cursor.close()
        conn.close()
        return jsonify({"mensaje": "Registro eliminado correctamente"}), 200
    except Exception as e:
        logger.exception("Error en eliminar_colaboradorevaluacion")
        return jsonify({"error": str(e)}), 500
