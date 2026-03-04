from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
#from blueprints.auth import token_requerido
import uuid

opciones_bp = Blueprint('opciones_bp', __name__)


# Obtener sucursales del usuario logueado
@opciones_bp.route('/sucursales', methods=['GET', 'OPTIONS'])
@jwt_required()
def obtener_sucursales():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursales permitidas para el usuario
        cursor.execute("""
            SELECT DISTINCT s.id, s.nombre, s.ubicacion
            FROM general_dim_sucursal s
            JOIN usuario_pivot_sucursal_usuario p ON s.id = p.id_sucursal
            WHERE p.id_usuario = %s
            ORDER BY s.nombre ASC
        """, (usuario_id,))

        sucursales = cursor.fetchall()
        cursor.close()
        conn.close()

        if not sucursales:
            return jsonify([]), 200

        return jsonify(sucursales), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Listar todas las rutas registradas
@opciones_bp.route('/rutas', methods=['GET'])
def listar_rutas():
    rutas = []
    for rule in opciones_bp.url_map.iter_rules():
        rutas.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'route': str(rule)
        })
    return jsonify(rutas), 200
