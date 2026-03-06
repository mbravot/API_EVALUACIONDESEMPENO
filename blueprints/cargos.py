from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from utils.db import get_db_connection
import logging

logger = logging.getLogger(__name__)

cargos_bp = Blueprint('cargos_bp', __name__)

# Listar todos los cargos
@cargos_bp.route('', methods=['GET', 'OPTIONS'])
@cargos_bp.route('/', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_cargos():
    """Lista todos los cargos (rrhh_dim_cargo)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, nivel FROM rrhh_dim_cargo ORDER BY nombre ASC")
        filas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([
            {"id": r["id"], "nombre": r["nombre"], "nivel": r["nivel"]}
            for r in filas
        ]), 200
    except Exception as e:
        logger.exception("Error en listar_cargos")
        return jsonify({"error": str(e)}), 500

# Obtener un cargo por id
@cargos_bp.route('/<int:id>', methods=['GET', 'OPTIONS'])
@jwt_required()
def obtener_cargo(id):
    """Obtiene un cargo por id."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, nivel FROM rrhh_dim_cargo WHERE id = %s", (id,))
        r = cursor.fetchone()
        cursor.close()
        conn.close()
        if not r:
            return jsonify({"error": "Cargo no encontrado"}), 404
        return jsonify({"id": r["id"], "nombre": r["nombre"], "nivel": r["nivel"]}), 200
    except Exception as e:
        logger.exception("Error en obtener_cargo")
        return jsonify({"error": str(e)}), 500

# Crear un nuevo cargo
@cargos_bp.route('', methods=['POST', 'OPTIONS'])
@jwt_required()
def crear_cargo():
    """Crea un nuevo cargo (rrhh_dim_cargo)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        nombre = (data.get('nombre') or '').strip()
        if not nombre:
            return jsonify({"error": "nombre es requerido"}), 400
        nivel = data.get('nivel')
        if nivel is not None:
            nivel = int(nivel)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rrhh_dim_cargo (nombre, nivel) VALUES (%s, %s)",
            (nombre, nivel)
        )
        conn.commit()
        id_nuevo = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({
            "id": id_nuevo,
            "nombre": nombre,
            "nivel": nivel,
            "mensaje": "Cargo creado correctamente",
        }), 201
    except ValueError:
        return jsonify({"error": "nivel debe ser un número"}), 400
    except Exception as e:
        logger.exception("Error en crear_cargo")
        return jsonify({"error": str(e)}), 500

# Actualizar un cargo
@cargos_bp.route('/<int:id>', methods=['PUT', 'OPTIONS'])
@jwt_required()
def actualizar_cargo(id):
    """Actualiza un cargo (rrhh_dim_cargo)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        nombre = (data.get('nombre') or '').strip()
        nivel = data.get('nivel')
        if nombre is not None and nombre == '':
            return jsonify({"error": "nombre no puede estar vacío"}), 400
        if nivel is not None:
            nivel = int(nivel)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, nivel FROM rrhh_dim_cargo WHERE id = %s", (id,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            return jsonify({"error": "Cargo no encontrado"}), 404
        nombre_final = nombre if nombre else row["nombre"]
        nivel_final = nivel if nivel is not None else row["nivel"]
        cursor.execute(
            "UPDATE rrhh_dim_cargo SET nombre = %s, nivel = %s WHERE id = %s",
            (nombre_final, nivel_final, id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            "id": id,
            "nombre": nombre_final,
            "nivel": nivel_final,
            "mensaje": "Cargo actualizado correctamente",
        }), 200
    except ValueError:
        return jsonify({"error": "nivel debe ser un número"}), 400
    except Exception as e:
        logger.exception("Error en actualizar_cargo")
        return jsonify({"error": str(e)}), 500

# Eliminar un cargo
@cargos_bp.route('/<int:id>', methods=['DELETE', 'OPTIONS'])
@jwt_required()
def eliminar_cargo(id):
    """Elimina un cargo (rrhh_dim_cargo)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rrhh_dim_cargo WHERE id = %s", (id,))
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Cargo no encontrado"}), 404
        cursor.close()
        conn.close()
        return jsonify({"mensaje": "Cargo eliminado correctamente"}), 200
    except Exception as e:
        logger.exception("Error en eliminar_cargo")
        return jsonify({"error": str(e)}), 500
