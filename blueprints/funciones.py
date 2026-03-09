from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from utils.db import get_db_connection
import logging

logger = logging.getLogger(__name__)

funciones_bp = Blueprint('funciones_bp', __name__)


# --- Catálogo de funciones (rrhh_dim_funcion) - disponibles para asignar a cargos ---

def _listar_catalogo_funciones():
    """Consulta el catálogo rrhh_dim_funcion."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre FROM rrhh_dim_funcion ORDER BY nombre ASC")
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"id": r["id"], "nombre": r["nombre"]} for r in filas]


@funciones_bp.route('', methods=['GET', 'OPTIONS'])
@funciones_bp.route('/', methods=['GET', 'OPTIONS'])
@funciones_bp.route('/catalogo', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_funciones():
    """Lista todas las funciones disponibles para asignar a un cargo (catálogo rrhh_dim_funcion)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        return jsonify(_listar_catalogo_funciones()), 200
    except Exception as e:
        logger.exception("Error en listar_funciones")
        return jsonify({"error": str(e)}), 500

# Endpoint para crear una nueva función en el catálogo
@funciones_bp.route('', methods=['POST', 'OPTIONS'])
@funciones_bp.route('/catalogo', methods=['POST', 'OPTIONS'])
@jwt_required()
def crear_funcion():
    """Crea una nueva función en el catálogo (rrhh_dim_funcion)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        nombre = (data.get('nombre') or '').strip()
        if not nombre:
            return jsonify({"error": "nombre es requerido"}), 400
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO rrhh_dim_funcion (nombre) VALUES (%s)", (nombre,))
        conn.commit()
        id_nuevo = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({
            "id": id_nuevo,
            "nombre": nombre,
            "mensaje": "Función creada correctamente",
        }), 201
    except Exception as e:
        logger.exception("Error en crear_funcion")
        return jsonify({"error": str(e)}), 500

# Endpoint para actualizar una función en el catálogo
@funciones_bp.route('/catalogo/<int:id>', methods=['PUT', 'OPTIONS'])
@jwt_required()
def actualizar_funcion(id):
    """Actualiza una función del catálogo (rrhh_dim_funcion)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        nombre = (data.get('nombre') or '').strip()
        if not nombre:
            return jsonify({"error": "nombre es requerido"}), 400
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE rrhh_dim_funcion SET nombre = %s WHERE id = %s", (nombre, id))
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Función no encontrada"}), 404
        cursor.close()
        conn.close()
        return jsonify({
            "id": id,
            "nombre": nombre,
            "mensaje": "Función actualizada correctamente",
        }), 200
    except Exception as e:
        logger.exception("Error en actualizar_funcion")
        return jsonify({"error": str(e)}), 500

# Endpoint para eliminar una función del catálogo
@funciones_bp.route('/catalogo/<int:id>', methods=['DELETE', 'OPTIONS'])
@jwt_required()
def eliminar_funcion(id):
    """Elimina una función del catálogo (rrhh_dim_funcion). No se puede si está asignada a algún cargo."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id FROM rrhh_pivot_cargofuncion WHERE id_funcion = %s LIMIT 1",
            (id,)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                "error": "No se puede eliminar: la función está asignada a uno o más cargos. Quite las asignaciones primero."
            }), 409
        cursor.execute("DELETE FROM rrhh_dim_funcion WHERE id = %s", (id,))
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Función no encontrada"}), 404
        cursor.close()
        conn.close()
        return jsonify({"mensaje": "Función eliminada correctamente"}), 200
    except Exception as e:
        logger.exception("Error en eliminar_funcion")
        return jsonify({"error": str(e)}), 500


# --- Funciones por cargo (rrhh_pivot_cargofuncion + rrhh_dim_funcion) ---
# Listar todas las funciones asignadas a un cargo
@funciones_bp.route('/cargo/<int:id_cargo>', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_funciones_por_cargo(id_cargo):
    """Lista las funciones asignadas a un cargo (cargo del evaluado)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.id, p.id_cargo, p.id_funcion, f.nombre AS nombre_funcion
            FROM rrhh_pivot_cargofuncion p
            INNER JOIN rrhh_dim_funcion f ON p.id_funcion = f.id
            WHERE p.id_cargo = %s
            ORDER BY f.nombre ASC
        """, (id_cargo,))
        filas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([
            {
                "id": r["id"],
                "id_cargo": r["id_cargo"],
                "id_funcion": r["id_funcion"],
                "nombre_funcion": r["nombre_funcion"],
            }
            for r in filas
        ]), 200
    except Exception as e:
        logger.exception("Error en listar_funciones_por_cargo")
        return jsonify({"error": str(e)}), 500

# Endpoint para asignar una función a un cargo
@funciones_bp.route('/cargo/<int:id_cargo>', methods=['POST', 'OPTIONS'])
@jwt_required()
def crear_funcion_cargo(id_cargo):
    """Asigna una función a un cargo (inserta en rrhh_pivot_cargofuncion)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        id_funcion = data.get('id_funcion')
        if id_funcion is None:
            return jsonify({"error": "id_funcion es requerido"}), 400
        id_funcion = int(id_funcion)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT id FROM rrhh_pivot_cargofuncion WHERE id_cargo = %s AND id_funcion = %s",
            (id_cargo, id_funcion)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "La función ya está asignada a este cargo"}), 409

        cursor.execute(
            "INSERT INTO rrhh_pivot_cargofuncion (id_cargo, id_funcion) VALUES (%s, %s)",
            (id_cargo, id_funcion)
        )
        conn.commit()
        id_nuevo = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({
            "id": id_nuevo,
            "id_cargo": id_cargo,
            "id_funcion": id_funcion,
            "mensaje": "Función asignada al cargo correctamente",
        }), 201
    except ValueError:
        return jsonify({"error": "id_funcion debe ser un número"}), 400
    except Exception as e:
        logger.exception("Error en crear_funcion_cargo")
        return jsonify({"error": str(e)}), 500

# Endpoint para actualizar la asignación de una función a un cargo
@funciones_bp.route('/<int:id>', methods=['PUT', 'OPTIONS'])
@jwt_required()
def actualizar_funcion_cargo(id):
    """Actualiza la asignación cargo-función (cambia id_funcion en rrhh_pivot_cargofuncion)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        id_funcion = data.get('id_funcion')
        if id_funcion is None:
            return jsonify({"error": "id_funcion es requerido"}), 400
        id_funcion = int(id_funcion)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, id_cargo FROM rrhh_pivot_cargofuncion WHERE id = %s", (id,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            return jsonify({"error": "Asignación cargo-función no encontrada"}), 404

        cursor.execute(
            "UPDATE rrhh_pivot_cargofuncion SET id_funcion = %s WHERE id = %s",
            (id_funcion, id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            "id": id,
            "id_cargo": row["id_cargo"],
            "id_funcion": id_funcion,
            "mensaje": "Asignación actualizada correctamente",
        }), 200
    except ValueError:
        return jsonify({"error": "id_funcion debe ser un número"}), 400
    except Exception as e:
        logger.exception("Error en actualizar_funcion_cargo")
        return jsonify({"error": str(e)}), 500

# Endpoint para eliminar la asignación de una función a un cargo
@funciones_bp.route('/<int:id>', methods=['DELETE', 'OPTIONS'])
@jwt_required()
def eliminar_funcion_cargo(id):
    """Elimina la asignación función-cargo (borra fila en rrhh_pivot_cargofuncion)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rrhh_pivot_cargofuncion WHERE id = %s", (id,))
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Asignación cargo-función no encontrada"}), 404
        cursor.close()
        conn.close()
        return jsonify({"mensaje": "Asignación eliminada correctamente"}), 200
    except Exception as e:
        logger.exception("Error en eliminar_funcion_cargo")
        return jsonify({"error": str(e)}), 500
