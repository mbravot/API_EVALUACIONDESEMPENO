from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import logging

logger = logging.getLogger(__name__)

permisos_bp = Blueprint('permisos_bp', __name__)

# ID del permiso en usuario_dim_permiso que permite acceso a la pantalla (evaluación u otra)
ID_PERMISO_ACCESO_PANTALLA = "7"


def tiene_permiso_acceso_pantalla(usuario_id):
    """Indica si el usuario tiene permiso de acceso a pantalla (id=7). Usado para permitir ver/editar/eliminar todas las evaluaciones."""
    if not usuario_id:
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM usuario_pivot_permiso_usuario pu
        INNER JOIN usuario_dim_permiso p ON pu.id_permiso = p.id
        WHERE pu.id_usuario = %s AND p.id = %s AND p.id_estado = 1
    """, (str(usuario_id).strip(), ID_PERMISO_ACCESO_PANTALLA))
    tiene = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return tiene


@permisos_bp.route('/acceso-pantalla', methods=['GET', 'OPTIONS'])
@jwt_required()
def acceso_pantalla():
    """
    Indica si el usuario puede acceder a la pantalla según permiso id=7 en usuario_dim_permiso.
    El front DEBE permitir acceso a la pantalla solo cuando acceso_permitido es true.
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        usuario_id = get_jwt_identity()
        if not usuario_id:
            return jsonify({"acceso_permitido": False, "error": "Usuario no identificado"}), 401
        usuario_id = str(usuario_id).strip()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM usuario_pivot_permiso_usuario pu
            INNER JOIN usuario_dim_permiso p ON pu.id_permiso = p.id
            WHERE pu.id_usuario = %s AND p.id = %s AND p.id_estado = 1
        """, (usuario_id, ID_PERMISO_ACCESO_PANTALLA))
        acceso_permitido = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        return jsonify({
            "acceso_permitido": acceso_permitido,
            "permiso_id": ID_PERMISO_ACCESO_PANTALLA,
        }), 200
    except Exception as e:
        logger.exception("Error en acceso_pantalla")
        return jsonify({"acceso_permitido": False, "error": str(e)}), 500


@permisos_bp.route('/mios', methods=['GET', 'OPTIONS'])
@permisos_bp.route('/', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_mis_permisos():
    """
    Devuelve los permisos del usuario logueado (usuario_pivot_permiso_usuario + usuario_dim_permiso).
    El front puede comprobar si tiene id=7 (u otro) para permitir acceso a ciertas pantallas.
    Query opcional: id_app (filtrar por aplicación).
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        usuario_id = get_jwt_identity()
        if not usuario_id:
            return jsonify({"error": "Usuario no identificado"}), 401
        usuario_id = str(usuario_id).strip()
        id_app = request.args.get('id_app', type=int)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT p.id, p.nombre, p.id_app, p.id_estado, a.nombre AS app_nombre
            FROM usuario_dim_permiso p
            INNER JOIN usuario_pivot_permiso_usuario pu ON pu.id_permiso = p.id
            LEFT JOIN general_dim_app a ON p.id_app = a.id
            WHERE pu.id_usuario = %s AND p.id_estado = 1
        """
        params = [usuario_id]
        if id_app is not None:
            sql += " AND p.id_app = %s"
            params.append(id_app)
        sql += " ORDER BY p.id_app, p.nombre"
        cursor.execute(sql, params)
        filas = cursor.fetchall()
        cursor.close()
        conn.close()

        permisos = [
            {
                "id": r["id"],
                "nombre": r["nombre"],
                "id_app": r["id_app"],
                "id_estado": r["id_estado"],
                "app_nombre": r.get("app_nombre"),
            }
            for r in filas
        ]
        return jsonify(permisos), 200
    except Exception as e:
        logger.exception("Error en listar_mis_permisos")
        return jsonify({"error": str(e)}), 500


@permisos_bp.route('/tiene/<id_permiso>', methods=['GET', 'OPTIONS'])
@jwt_required()
def tiene_permiso(id_permiso):
    """
    Devuelve true/false si el usuario logueado tiene el permiso indicado.
    Útil para que el front consulte un permiso concreto (ej. id=7) sin cargar toda la lista.
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        usuario_id = get_jwt_identity()
        if not usuario_id:
            return jsonify({"error": "Usuario no identificado"}), 401
        usuario_id = str(usuario_id).strip()
        id_permiso = str(id_permiso).strip()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 1 FROM usuario_pivot_permiso_usuario pu
            INNER JOIN usuario_dim_permiso p ON pu.id_permiso = p.id
            WHERE pu.id_usuario = %s AND pu.id_permiso = %s AND p.id_estado = 1
        """, (usuario_id, id_permiso))
        tiene = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        return jsonify({"permiso_id": id_permiso, "tiene": tiene}), 200
    except Exception as e:
        logger.exception("Error en tiene_permiso")
        return jsonify({"error": str(e)}), 500
