from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from utils.db import get_db_connection
import logging

logger = logging.getLogger(__name__)

competencias_bp = Blueprint('competencias_bp', __name__)


# --- Catálogo rrhh_dim_competencia ---

@competencias_bp.route('', methods=['GET', 'OPTIONS'])
@competencias_bp.route('/', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_competencias():
    """Lista todas las competencias (rrhh_dim_competencia)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM rrhh_dim_competencia ORDER BY nombre ASC")
        filas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([{"id": r["id"], "nombre": r["nombre"]} for r in filas]), 200
    except Exception as e:
        logger.exception("Error en listar_competencias")
        return jsonify({"error": str(e)}), 500

# Obtener una competencia por id
@competencias_bp.route('/<int:id>', methods=['GET', 'OPTIONS'])
@jwt_required()
def obtener_competencia(id):
    """Obtiene una competencia por id."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM rrhh_dim_competencia WHERE id = %s", (id,))
        r = cursor.fetchone()
        cursor.close()
        conn.close()
        if not r:
            return jsonify({"error": "Competencia no encontrada"}), 404
        return jsonify({"id": r["id"], "nombre": r["nombre"]}), 200
    except Exception as e:
        logger.exception("Error en obtener_competencia")
        return jsonify({"error": str(e)}), 500

# Crear una nueva competencia
@competencias_bp.route('', methods=['POST', 'OPTIONS'])
@jwt_required()
def crear_competencia():
    """Crea una nueva competencia (rrhh_dim_competencia)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        nombre = (data.get('nombre') or '').strip() or None
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO rrhh_dim_competencia (nombre) VALUES (%s)", (nombre,))
        conn.commit()
        id_nuevo = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({
            "id": id_nuevo,
            "nombre": nombre,
            "mensaje": "Competencia creada correctamente",
        }), 201
    except Exception as e:
        logger.exception("Error en crear_competencia")
        return jsonify({"error": str(e)}), 500

# Actualizar una competencia
@competencias_bp.route('/<int:id>', methods=['PUT', 'OPTIONS'])
@jwt_required()
def actualizar_competencia(id):
    """Actualiza una competencia (rrhh_dim_competencia)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        nombre = data.get('nombre')
        if nombre is not None:
            nombre = nombre.strip() if nombre else None
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM rrhh_dim_competencia WHERE id = %s", (id,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            return jsonify({"error": "Competencia no encontrada"}), 404
        nombre_final = nombre if nombre is not None else row["nombre"]
        cursor.execute("UPDATE rrhh_dim_competencia SET nombre = %s WHERE id = %s", (nombre_final, id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            "id": id,
            "nombre": nombre_final,
            "mensaje": "Competencia actualizada correctamente",
        }), 200
    except Exception as e:
        logger.exception("Error en actualizar_competencia")
        return jsonify({"error": str(e)}), 500

# Eliminar una competencia
@competencias_bp.route('/<int:id>', methods=['DELETE', 'OPTIONS'])
@jwt_required()
def eliminar_competencia(id):
    """Elimina una competencia (rrhh_dim_competencia)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id FROM rrhh_dim_competencianivel WHERE id_competencia = %s LIMIT 1",
            (id,)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                "error": "No se puede eliminar: la competencia tiene niveles definidos. Elimínelos primero."
            }), 409
        cursor.execute("DELETE FROM rrhh_dim_competencia WHERE id = %s", (id,))
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Competencia no encontrada"}), 404
        cursor.close()
        conn.close()
        return jsonify({"mensaje": "Competencia eliminada correctamente"}), 200
    except Exception as e:
        logger.exception("Error en eliminar_competencia")
        return jsonify({"error": str(e)}), 500


# --- Competencia por nivel (rrhh_dim_competencianivel) ---
# Listar todas las competencias por nivel
@competencias_bp.route('/niveles', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_competencianiveles():
    """Lista competencia-nivel. Query: id_nivel (filtrar por nivel), id_competencia (filtrar por competencia)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        id_nivel = request.args.get('id_nivel', type=int)
        id_competencia = request.args.get('id_competencia', type=int)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT cn.id, cn.id_competencia, cn.id_nivel, cn.definicion,
                   c.nombre AS nombre_competencia, n.nivel AS valor_nivel
            FROM rrhh_dim_competencianivel cn
            INNER JOIN rrhh_dim_competencia c ON cn.id_competencia = c.id
            INNER JOIN rrhh_dim_nivel n ON cn.id_nivel = n.id
            WHERE 1=1
        """
        params = []
        if id_nivel is not None:
            sql += " AND cn.id_nivel = %s"
            params.append(id_nivel)
        if id_competencia is not None:
            sql += " AND cn.id_competencia = %s"
            params.append(id_competencia)
        sql += " ORDER BY c.nombre, n.nivel"
        cursor.execute(sql, params)
        filas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([
            {
                "id": r["id"],
                "id_competencia": r["id_competencia"],
                "id_nivel": r["id_nivel"],
                "definicion": r["definicion"],
                "nombre_competencia": r["nombre_competencia"],
                "valor_nivel": r["valor_nivel"],
            }
            for r in filas
        ]), 200
    except Exception as e:
        logger.exception("Error en listar_competencianiveles")
        return jsonify({"error": str(e)}), 500

# Listar todas las competencias por nivel por id de nivel
@competencias_bp.route('/niveles/<int:id_nivel>', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_competencianiveles_por_nivel(id_nivel):
    """Lista competencia-nivel disponibles para un nivel (útil para asignar a cargos de ese nivel)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT cn.id, cn.id_competencia, cn.id_nivel, cn.definicion,
                   c.nombre AS nombre_competencia, n.nivel AS valor_nivel
            FROM rrhh_dim_competencianivel cn
            INNER JOIN rrhh_dim_competencia c ON cn.id_competencia = c.id
            INNER JOIN rrhh_dim_nivel n ON cn.id_nivel = n.id
            WHERE cn.id_nivel = %s
            ORDER BY c.nombre
        """, (id_nivel,))
        filas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([
            {
                "id": r["id"],
                "id_competencia": r["id_competencia"],
                "id_nivel": r["id_nivel"],
                "definicion": r["definicion"],
                "nombre_competencia": r["nombre_competencia"],
                "valor_nivel": r["valor_nivel"],
            }
            for r in filas
        ]), 200
    except Exception as e:
        logger.exception("Error en listar_competencianiveles_por_nivel")
        return jsonify({"error": str(e)}), 500

# Crear una nueva competencia por nivel
@competencias_bp.route('/niveles', methods=['POST', 'OPTIONS'])
@jwt_required()
def crear_competencianivel():
    """Crea una definición competencia-nivel (rrhh_dim_competencianivel)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        id_competencia = data.get('id_competencia')
        id_nivel = data.get('id_nivel')
        if id_competencia is None or id_nivel is None:
            return jsonify({"error": "id_competencia e id_nivel son requeridos"}), 400
        id_competencia = int(id_competencia)
        id_nivel = int(id_nivel)
        definicion = (data.get('definicion') or '').strip() or None
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rrhh_dim_competencianivel (id_competencia, id_nivel, definicion) VALUES (%s, %s, %s)",
            (id_competencia, id_nivel, definicion)
        )
        conn.commit()
        id_nuevo = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({
            "id": id_nuevo,
            "id_competencia": id_competencia,
            "id_nivel": id_nivel,
            "definicion": definicion,
            "mensaje": "Competencia-nivel creado correctamente",
        }), 201
    except ValueError:
        return jsonify({"error": "id_competencia e id_nivel deben ser números"}), 400
    except Exception as e:
        logger.exception("Error en crear_competencianivel")
        return jsonify({"error": str(e)}), 500

# Actualizar una competencia por nivel
@competencias_bp.route('/niveles/<int:id>', methods=['PUT', 'OPTIONS'])
@jwt_required()
def actualizar_competencianivel(id):
    """Actualiza una definición competencia-nivel."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        definicion = data.get('definicion')
        if definicion is not None:
            definicion = definicion.strip() or None
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, id_competencia, id_nivel, definicion FROM rrhh_dim_competencianivel WHERE id = %s",
            (id,)
        )
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            return jsonify({"error": "Competencia-nivel no encontrado"}), 404
        definicion_final = definicion if definicion is not None else row["definicion"]
        cursor.execute(
            "UPDATE rrhh_dim_competencianivel SET definicion = %s WHERE id = %s",
            (definicion_final, id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            "id": id,
            "id_competencia": row["id_competencia"],
            "id_nivel": row["id_nivel"],
            "definicion": definicion_final,
            "mensaje": "Competencia-nivel actualizado correctamente",
        }), 200
    except Exception as e:
        logger.exception("Error en actualizar_competencianivel")
        return jsonify({"error": str(e)}), 500

# Eliminar una competencia por nivel
@competencias_bp.route('/niveles/<int:id>', methods=['DELETE', 'OPTIONS'])
@jwt_required()
def eliminar_competencianivel(id):
    """Elimina una definición competencia-nivel. No se puede si está asignada a algún cargo."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id FROM rrhh_pivot_cargocompetencia WHERE id_competencianivel = %s LIMIT 1",
            (id,)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                "error": "No se puede eliminar: está asignado a uno o más cargos. Quite las asignaciones primero."
            }), 409
        cursor.execute("DELETE FROM rrhh_dim_competencianivel WHERE id = %s", (id,))
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Competencia-nivel no encontrado"}), 404
        cursor.close()
        conn.close()
        return jsonify({"mensaje": "Competencia-nivel eliminado correctamente"}), 200
    except Exception as e:
        logger.exception("Error en eliminar_competencianivel")
        return jsonify({"error": str(e)}), 500


# --- Asignación competencias a cargo (rrhh_pivot_cargocompetencia) según nivel del cargo ---
# Listar todas las competencias disponibles para un cargo
@competencias_bp.route('/cargo/<int:id_cargo>/disponibles', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_competencias_disponibles_para_cargo(id_cargo):
    """
    Lista las competencia-nivel que se pueden asignar a este cargo según su nivel.
    Carga de rrhh_dim_competencianivel donde id_nivel = nivel del cargo.
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, nivel FROM rrhh_dim_cargo WHERE id = %s", (id_cargo,))
        cargo = cursor.fetchone()
        if not cargo:
            cursor.close()
            conn.close()
            return jsonify({"error": "Cargo no encontrado"}), 404
        id_nivel_cargo = cargo.get("nivel")
        if id_nivel_cargo is None:
            cursor.close()
            conn.close()
            return jsonify({
                "error": "El cargo no tiene nivel asignado. Asigne un nivel al cargo para cargar competencias."
            }), 400
        cursor.execute("""
            SELECT cn.id, cn.id_competencia, cn.id_nivel, cn.definicion,
                   c.nombre AS nombre_competencia, n.nivel AS valor_nivel
            FROM rrhh_dim_competencianivel cn
            INNER JOIN rrhh_dim_competencia c ON cn.id_competencia = c.id
            INNER JOIN rrhh_dim_nivel n ON cn.id_nivel = n.id
            WHERE cn.id_nivel = %s
            ORDER BY c.nombre
        """, (id_nivel_cargo,))
        filas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([
            {
                "id": r["id"],
                "id_competencia": r["id_competencia"],
                "id_nivel": r["id_nivel"],
                "definicion": r["definicion"],
                "nombre_competencia": r["nombre_competencia"],
                "valor_nivel": r["valor_nivel"],
            }
            for r in filas
        ]), 200
    except Exception as e:
        logger.exception("Error en listar_competencias_disponibles_para_cargo")
        return jsonify({"error": str(e)}), 500

# Listar todas las competencias asignadas a un cargo
@competencias_bp.route('/cargo/<int:id_cargo>', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_competencias_por_cargo(id_cargo):
    """Lista las competencias asignadas a un cargo (con nombre competencia, nivel y definición)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.id, p.id_cargo, p.id_competencianivel,
                   cn.id_competencia, cn.id_nivel, cn.definicion,
                   c.nombre AS nombre_competencia, n.nivel AS valor_nivel
            FROM rrhh_pivot_cargocompetencia p
            INNER JOIN rrhh_dim_competencianivel cn ON p.id_competencianivel = cn.id
            INNER JOIN rrhh_dim_competencia c ON cn.id_competencia = c.id
            INNER JOIN rrhh_dim_nivel n ON cn.id_nivel = n.id
            WHERE p.id_cargo = %s
            ORDER BY c.nombre
        """, (id_cargo,))
        filas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([
            {
                "id": r["id"],
                "id_cargo": r["id_cargo"],
                "id_competencianivel": r["id_competencianivel"],
                "id_competencia": r["id_competencia"],
                "id_nivel": r["id_nivel"],
                "definicion": r["definicion"],
                "nombre_competencia": r["nombre_competencia"],
                "valor_nivel": r["valor_nivel"],
            }
            for r in filas
        ]), 200
    except Exception as e:
        logger.exception("Error en listar_competencias_por_cargo")
        return jsonify({"error": str(e)}), 500

# Asignar una competencia a un cargo
@competencias_bp.route('/cargo/<int:id_cargo>', methods=['POST', 'OPTIONS'])
@jwt_required()
def asignar_competencia_cargo(id_cargo):
    """Asigna una competencia-nivel a un cargo. Solo permite id_competencianivel cuyo id_nivel coincida con el nivel del cargo."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json() or {}
        id_competencianivel = data.get('id_competencianivel')
        if id_competencianivel is None:
            return jsonify({"error": "id_competencianivel es requerido"}), 400
        id_competencianivel = int(id_competencianivel)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, nivel FROM rrhh_dim_cargo WHERE id = %s", (id_cargo,))
        cargo = cursor.fetchone()
        if not cargo:
            cursor.close()
            conn.close()
            return jsonify({"error": "Cargo no encontrado"}), 404
        cursor.execute(
            "SELECT id, id_nivel FROM rrhh_dim_competencianivel WHERE id = %s",
            (id_competencianivel,)
        )
        cn = cursor.fetchone()
        if not cn:
            cursor.close()
            conn.close()
            return jsonify({"error": "Competencia-nivel no encontrado"}), 404
        # nivel del cargo (rrhh_dim_cargo.nivel) debe coincidir con id_nivel del competencianivel
        if cargo.get("nivel") != cn["id_nivel"]:
            cursor.close()
            conn.close()
            return jsonify({
                "error": "El nivel del cargo no coincide con el nivel de la competencia. Solo puede asignar competencias del mismo nivel que el cargo."
            }), 400
        cursor.execute(
            "SELECT id FROM rrhh_pivot_cargocompetencia WHERE id_cargo = %s AND id_competencianivel = %s",
            (id_cargo, id_competencianivel)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Esta competencia ya está asignada a este cargo"}), 409
        cursor.execute(
            "INSERT INTO rrhh_pivot_cargocompetencia (id_cargo, id_competencianivel) VALUES (%s, %s)",
            (id_cargo, id_competencianivel)
        )
        conn.commit()
        id_nuevo = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({
            "id": id_nuevo,
            "id_cargo": id_cargo,
            "id_competencianivel": id_competencianivel,
            "mensaje": "Competencia asignada al cargo correctamente",
        }), 201
    except ValueError:
        return jsonify({"error": "id_competencianivel debe ser un número"}), 400
    except Exception as e:
        logger.exception("Error en asignar_competencia_cargo")
        return jsonify({"error": str(e)}), 500

# Eliminar la asignación de una competencia a un cargo
@competencias_bp.route('/asignacion/<int:id>', methods=['DELETE', 'OPTIONS'])
@jwt_required()
def eliminar_asignacion_cargo(id):
    """Elimina la asignación cargo-competencia (borra fila en rrhh_pivot_cargocompetencia)."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rrhh_pivot_cargocompetencia WHERE id = %s", (id,))
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Asignación no encontrada"}), 404
        cursor.close()
        conn.close()
        return jsonify({"mensaje": "Asignación eliminada correctamente"}), 200
    except Exception as e:
        logger.exception("Error en eliminar_asignacion_cargo")
        return jsonify({"error": str(e)}), 500
