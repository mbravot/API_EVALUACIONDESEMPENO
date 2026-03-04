from flask import Blueprint, request, jsonify
import bcrypt
from config import Config
from utils.db import get_db_connection
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token
from datetime import date
import logging

# Configurar logging
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth_bp', __name__)


# 🔹 Iniciar sesión
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        usuario = data.get('usuario')
        clave = data.get('clave')

        if not usuario or not clave:
            return jsonify({"error": "Faltan datos de usuario o clave"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar usuario y verificar estado y acceso a la app
        sql = """
            SELECT u.*, s.nombre as sucursal_nombre, s.ubicacion as sucursal_comuna
            FROM general_dim_usuario u
            LEFT JOIN general_dim_sucursal s ON u.id_sucursalactiva = s.id
            WHERE u.usuario = %s 
            AND u.id_estado = 1
            AND EXISTS (
                SELECT 1 
                FROM usuario_pivot_app_usuario p 
                WHERE p.id_usuario = u.id 
                AND p.id_app = 9 -- Acá se debe cambiar por el id de la app
            )
        """
        cursor.execute(sql, (usuario,))
        user = cursor.fetchone()

        if not user or not bcrypt.checkpw(clave.encode('utf-8'), user['clave'].encode('utf-8')):
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario o clave incorrectos / No tiene acceso a la app"}), 401

        # Crear token con información adicional
        access_token = create_access_token(
            identity=user['id'],
            additional_claims={
                'rol': user['id_rol'],
                'perfil': user['id_perfil'],
                'sucursal': user['id_sucursalactiva'],
                'sucursal_nombre': user['sucursal_nombre']
            }
        )

        cursor.close()
        conn.close()

        return jsonify({
            "access_token": access_token,
            "usuario": user['usuario'],
            "nombre": user['nombre'],
            "id_sucursal": user['id_sucursalactiva'],
            "sucursal_nombre": user['sucursal_nombre'],
            "id_rol": user['id_rol'],
            "id_perfil": user['id_perfil']
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Refrescar el token
@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT u.*, s.nombre as sucursal_nombre
            FROM general_dim_usuario u
            LEFT JOIN general_dim_sucursal s ON u.id_sucursalactiva = s.id
            WHERE u.id = %s 
            AND u.id_estado = 1
            AND EXISTS (
                SELECT 1 
                FROM usuario_pivot_app_usuario p 
                WHERE p.id_usuario = u.id 
                AND p.id_app = 9
            )
        """
        cursor.execute(sql, (usuario_id,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no encontrado o sin acceso"}), 401

        access_token = create_access_token(
            identity=user['id'],
            additional_claims={
                'rol': user['id_rol'],
                'perfil': user['id_perfil'],
                'sucursal': user['id_sucursalactiva'],
                'sucursal_nombre': user['sucursal_nombre']
            }
        )

        cursor.close()
        conn.close()

        return jsonify({
            "access_token": access_token,
            "usuario": user['usuario'],
            "nombre": user['nombre'],
            "id_sucursal": user['id_sucursalactiva'],
            "sucursal_nombre": user['sucursal_nombre'],
            "id_rol": user['id_rol'],
            "id_perfil": user['id_perfil']
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Cambiar la clave del usuario
@auth_bp.route('/cambiar-clave', methods=['POST'])
@jwt_required()
def cambiar_clave():
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        clave_actual = data.get('clave_actual')
        nueva_clave = data.get('nueva_clave')

        if not clave_actual or not nueva_clave:
            return jsonify({"error": "Faltan datos de clave"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar clave actual
        cursor.execute("SELECT clave FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        user = cursor.fetchone()

        if not user or not bcrypt.checkpw(clave_actual.encode('utf-8'), user['clave'].encode('utf-8')):
            cursor.close()
            conn.close()
            return jsonify({"error": "Clave actual incorrecta"}), 401

        # Generar nuevo hash con bcrypt
        salt = bcrypt.gensalt()
        nueva_clave_hash = bcrypt.hashpw(nueva_clave.encode('utf-8'), salt)

        # Actualizar clave
        cursor.execute("UPDATE general_dim_usuario SET clave = %s WHERE id = %s", 
                      (nueva_clave_hash.decode('utf-8'), usuario_id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Clave actualizada correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Cambiar la sucursal activa del usuario logueado
@auth_bp.route('/cambiar-sucursal', methods=['POST'])
@jwt_required()
def cambiar_sucursal():
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        nueva_sucursal_id = data.get('id_sucursal')

        if not nueva_sucursal_id:
            return jsonify({"error": "El ID de la sucursal es requerido"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar que el usuario tenga acceso a la sucursal
        cursor.execute("""
            SELECT 1 
            FROM usuario_pivot_sucursal_usuario 
            WHERE id_usuario = %s AND id_sucursal = %s
        """, (usuario_id, nueva_sucursal_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "No tienes acceso a esta sucursal"}), 403

        # Actualizar la sucursal activa
        cursor.execute("""
            UPDATE general_dim_usuario 
            SET id_sucursalactiva = %s 
            WHERE id = %s
        """, (nueva_sucursal_id, usuario_id))
        
        conn.commit()

        # Obtener el nombre de la sucursal para la respuesta
        cursor.execute("""
            SELECT nombre 
            FROM general_dim_sucursal 
            WHERE id = %s
        """, (nueva_sucursal_id,))
        
        sucursal = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            "message": "Sucursal actualizada correctamente",
            "id_sucursal": nueva_sucursal_id,
            "sucursal_nombre": sucursal['nombre'] if sucursal else None
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Obtener información del usuario logueado
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def obtener_usuario_actual():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT u.id, u.usuario, u.nombre, u.apellido_paterno, u.apellido_materno, 
                   u.correo, u.id_sucursalactiva, u.id_estado, u.id_rol, u.id_perfil, 
                   u.fecha_creacion, s.nombre as sucursal_nombre
            FROM general_dim_usuario u
            LEFT JOIN general_dim_sucursal s ON u.id_sucursalactiva = s.id
            WHERE u.id = %s
        """, (usuario_id,))
        
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()

        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404

        return jsonify(usuario), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Actualizar información del usuario logueado
@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def actualizar_usuario_actual():
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        
        # Campos que se pueden actualizar
        nombre = data.get('nombre')
        apellido_paterno = data.get('apellido_paterno')
        apellido_materno = data.get('apellido_materno')
        correo = data.get('correo')
        
        if not any([nombre, apellido_paterno, apellido_materno, correo]):
            return jsonify({"error": "Al menos un campo debe ser proporcionado para actualizar"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Construir la consulta dinámicamente
        campos_actualizar = []
        valores = []
        
        if nombre is not None:
            campos_actualizar.append("nombre = %s")
            valores.append(nombre)
        if apellido_paterno is not None:
            campos_actualizar.append("apellido_paterno = %s")
            valores.append(apellido_paterno)
        if apellido_materno is not None:
            campos_actualizar.append("apellido_materno = %s")
            valores.append(apellido_materno)
        if correo is not None:
            campos_actualizar.append("correo = %s")
            valores.append(correo)
        
        valores.append(usuario_id)
        
        sql = f"""
            UPDATE general_dim_usuario 
            SET {', '.join(campos_actualizar)}
            WHERE id = %s
        """
        
        cursor.execute(sql, valores)
        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no encontrado"}), 404

        cursor.close()
        conn.close()

        return jsonify({"message": "Información del usuario actualizada correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
