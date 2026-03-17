from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from utils.db import get_db_connection
import logging

logger = logging.getLogger(__name__)

colaboradores_bp = Blueprint('colaboradores_bp', __name__)


@colaboradores_bp.route('', methods=['GET', 'OPTIONS'])
@colaboradores_bp.route('/', methods=['GET', 'OPTIONS'])
@jwt_required()
def listar_colaboradores():
    """
    Lista todos los colaboradores desde general_dim_colaborador,
    devolviendo id y nombre_completo para poblar desplegables.
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, nombre, apellido_paterno, apellido_materno
            FROM general_dim_colaborador
            ORDER BY nombre, apellido_paterno, apellido_materno
            """
        )
        filas = cursor.fetchall()
        cursor.close()
        conn.close()

        def nombre_completo(r):
            return " ".join(
                filter(
                    None,
                    [
                        r.get("nombre"),
                        r.get("apellido_paterno"),
                        r.get("apellido_materno"),
                    ],
                )
            ).strip() or None

        return jsonify(
            [
                {
                    "id": r["id"],
                    "nombre_completo": nombre_completo(r),
                }
                for r in filas
            ]
        ), 200
    except Exception as e:
        logger.exception("Error en listar_colaboradores")
        return jsonify({"error": str(e)}), 500


@colaboradores_bp.route('/<string:id>', methods=['GET', 'OPTIONS'])
@jwt_required()
def obtener_colaborador(id):
    """
    Obtiene un colaborador por id desde general_dim_colaborador.
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, nombre, apellido_paterno, apellido_materno
            FROM general_dim_colaborador
            WHERE id = %s
            """,
            (id,),
        )
        r = cursor.fetchone()
        cursor.close()
        conn.close()
        if not r:
            return jsonify({"error": "Colaborador no encontrado"}), 404

        nombre_completo = " ".join(
            filter(
                None,
                [
                    r.get("nombre"),
                    r.get("apellido_paterno"),
                    r.get("apellido_materno"),
                ],
            )
        ).strip() or None

        return jsonify(
            {
                "id": r["id"],
                "nombre_completo": nombre_completo,
            }
        ), 200
    except Exception as e:
        logger.exception("Error en obtener_colaborador")
        return jsonify({"error": str(e)}), 500

