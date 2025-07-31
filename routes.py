import os
import time
import uuid
from flask import Blueprint, request, jsonify, redirect
from models import (db, Usuario, Ticket, TicketComentario, TicketEstado, 
                   TicketPrioridad, Departamento, Sucursal, Rol, Estado, 
                   PerfilUsuario, ticket_pivot_departamento_agente, 
                   usuario_pivot_sucursal_usuario, Categoria, usuario_pivot_app_usuario)
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_cors import cross_origin  # Importar para permitir CORS en rutas específicas
from functools import wraps
from itertools import chain  # Importar para combinar listas sin duplicados
import pytz
from flask import send_from_directory
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from utils import enviar_correo_async, enviar_correo
from cloud_storage import storage_manager
import bcrypt
import hashlib
from datetime import datetime


api = Blueprint('api', __name__)
auth = Blueprint('auth', __name__)

# Cargar variables de entorno desde el archivo .env
load_dotenv()

CHILE_TZ = pytz.timezone('America/Santiago')

# ✅ Decorador para verificar acceso a apps
def app_required(app_id):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_user_id = get_jwt_identity()
            if not verificar_acceso_app(current_user_id, app_id):
                return jsonify({'message': f'No tienes acceso a la aplicación requerida'}), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ✅ Función auxiliar para verificar acceso a apps
def verificar_acceso_app(usuario_id, app_id):
    """Verifica si un usuario tiene acceso a una app específica"""
    app_acceso = db.session.query(usuario_pivot_app_usuario).filter(
        usuario_pivot_app_usuario.c.id_usuario == usuario_id,
        usuario_pivot_app_usuario.c.id_app == app_id
    ).first()
    return app_acceso is not None

# Función de notificación por correo
def notificar_creacion_ticket(ticket, usuario, agente):
    try:
        agente_nombre = agente.nombre_completo if agente else "Sin asignar"
        usuario_nombre = usuario.nombre_completo
        sucursal_obj = Sucursal.query.get(ticket.id_sucursal)
        sucursal_nombre = sucursal_obj.nombre if sucursal_obj else "No asignada"
        
        asunto = "Nuevo Ticket Creado"
        cuerpo = f"""
        <h1>Nuevo Ticket Creado</h1>
        <p>Se ha creado un nuevo ticket con los siguientes detalles:</p>
        <ul>
            <li><strong>ID:</strong> {ticket.id}</li>
            <li><strong>Título:</strong> {ticket.titulo}</li>
            <li><strong>Descripción:</strong> {ticket.descripcion}</li>
            <li><strong>Creado por:</strong> {usuario_nombre}</li>
            <li><strong>Sucursal:</strong> {sucursal_nombre}</li>
            <li><strong>Agente asignado:</strong> {agente_nombre}</li>
        </ul>
        <p>Por favor, revisa el sistema de tickets para más detalles.</p>
        <p>https://tickets.lahornilla.cl/</p>
        <p>Departamento de TI La Hornilla.</p>
        """

        # Enviar notificación al creador del ticket
        enviar_correo_async(usuario.correo, asunto, cuerpo)

        # Enviar notificación al agente asignado (si hay agente)
        if agente:
            enviar_correo_async(agente.correo, asunto, cuerpo)
    except Exception as e:
        print(f"Error en notificar_creacion_ticket: {str(e)}")


# Función para notificar cambio de estado
def notificar_cambio_estado(ticket, usuario, agente, nuevo_estado):
    try:
        agente_nombre = agente.nombre_completo if agente else "Sin asignar"
        usuario_nombre = usuario.nombre_completo
        sucursal_obj = Sucursal.query.get(ticket.id_sucursal)
        sucursal_nombre = sucursal_obj.nombre if sucursal_obj else "No asignada"

        asunto = f"Ticket {ticket.id} Cambió de Estado"
        cuerpo = f"""
        <h1>Cambio de Estado del Ticket</h1>
        <p>El ticket con los siguientes detalles ha cambiado de estado:</p>
        <ul>
            <li><strong>ID:</strong> {ticket.id}</li>
            <li><strong>Título:</strong> {ticket.titulo}</li>
            <li><strong>Descripción:</strong> {ticket.descripcion}</li>
            <li><strong>Creado por:</strong> {usuario_nombre}</li>
            <li><strong>Sucursal:</strong> {sucursal_nombre}</li>
            <li><strong>Agente asignado:</strong> {agente_nombre}</li>
            <li><strong>Nuevo Estado:</strong> {nuevo_estado}</li>
        </ul>
        <p>Por favor, revisa el sistema para más detalles.</p>
        <p>https://tickets.lahornilla.cl/</p>
        <p>Departamento de TI La Hornilla.</p>
        """
        enviar_correo_async(usuario.correo, asunto, cuerpo)
        if agente:
            enviar_correo_async(agente.correo, asunto, cuerpo)
    except Exception as e:
        print(f"Error en notificar_cambio_estado: {str(e)}")

# Función para notificar cierre de ticket
def notificar_cierre_ticket(ticket, usuario, agente):
    try:
        agente_nombre = agente.nombre_completo if agente else "Sin asignar"
        usuario_nombre = usuario.nombre_completo
        sucursal_obj = Sucursal.query.get(ticket.id_sucursal)
        sucursal_nombre = sucursal_obj.nombre if sucursal_obj else "No asignada"

        asunto = f"Ticket {ticket.id} Cerrado"
        cuerpo = f"""
        <h1>Ticket Cerrado</h1>
        <p>El ticket con los siguientes detalles ha sido cerrado:</p>
        <ul>
            <li><strong>ID:</strong> {ticket.id}</li>
            <li><strong>Título:</strong> {ticket.titulo}</li>
            <li><strong>Descripción:</strong> {ticket.descripcion}</li>
            <li><strong>Creado por:</strong> {usuario_nombre}</li>
            <li><strong>Sucursal:</strong> {sucursal_nombre}</li>
            <li><strong>Agente asignado:</strong> {agente_nombre}</li>
        </ul>
        <p>Por favor, revisa el sistema para más detalles.</p>
        <p>https://tickets.lahornilla.cl/</p>
        <p>Departamento de TI La Hornilla.</p>
        """
        enviar_correo_async(usuario.correo, asunto, cuerpo)
        if agente:
            enviar_correo_async(agente.correo, asunto, cuerpo)
    except Exception as e:
        print(f"Error en notificar_cierre_ticket: {str(e)}")

# Función para notificar nuevo comentario
def notificar_comentario(ticket, usuario, agente, comentario):
    try:
        agente_nombre = agente.nombre_completo if agente else "Sin asignar"
        usuario_nombre = usuario.nombre_completo
        sucursal_obj = Sucursal.query.get(ticket.id_sucursal)
        sucursal_nombre = sucursal_obj.nombre if sucursal_obj else "No asignada"

        asunto = f"Nuevo Comentario en el Ticket {ticket.id}"
        cuerpo = f"""
        <h1>Nuevo Comentario en Ticket</h1>
        <p>Se ha agregado un nuevo comentario al ticket con los siguientes detalles:</p>
        <ul>
            <li><strong>ID:</strong> {ticket.id}</li>
            <li><strong>Título:</strong> {ticket.titulo}</li>
            <li><strong>Descripción:</strong> {ticket.descripcion}</li>
            <li><strong>Creado por:</strong> {usuario_nombre}</li>
            <li><strong>Sucursal:</strong> {sucursal_nombre}</li>
            <li><strong>Agente asignado:</strong> {agente_nombre}</li>
        </ul>
        <h3>Comentario:</h3>
        <blockquote>{comentario}</blockquote>
        <p>Por favor, revisa el sistema para más detalles.</p>
        <p>https://tickets.lahornilla.cl/</p>
        <p>Departamento de TI La Hornilla.</p>
        """
        enviar_correo_async(usuario.correo, asunto, cuerpo)
        if agente:
            enviar_correo_async(agente.correo, asunto, cuerpo)
    except Exception as e:
        print(f"Error en notificar_comentario: {str(e)}")

# Función para notificar reasignación de ticket
def notificar_reasignacion_ticket(ticket, usuario, agente_anterior, agente_nuevo):
    try:
        agente_anterior_nombre = agente_anterior.nombre_completo if agente_anterior else "Ninguno"
        agente_nuevo_nombre = agente_nuevo.nombre_completo
        usuario_nombre = usuario.nombre_completo
        sucursal_obj = Sucursal.query.get(ticket.id_sucursal)
        sucursal_nombre = sucursal_obj.nombre if sucursal_obj else "No asignada"

        asunto = f"Ticket {ticket.id} Reasignado"
        cuerpo = f"""
        <h1>Ticket Reasignado</h1>
        <p>El ticket con los siguientes detalles ha sido reasignado:</p>
        <ul>
            <li><strong>ID:</strong> {ticket.id}</li>
            <li><strong>Título:</strong> {ticket.titulo}</li>
            <li><strong>Descripción:</strong> {ticket.descripcion}</li>
            <li><strong>Creado por:</strong> {usuario_nombre}</li>
            <li><strong>Sucursal:</strong> {sucursal_nombre}</li>
            <li><strong>Agente anterior:</strong> {agente_anterior_nombre}</li>
            <li><strong>Nuevo agente asignado:</strong> {agente_nuevo_nombre}</li>
        </ul>
        <p>Por favor, revisa el sistema para más detalles.</p>
        <p>https://tickets.lahornilla.cl/</p>
        <p>Departamento de TI La Hornilla.</p>
        """
        enviar_correo_async(usuario.correo, asunto, cuerpo)
        if agente_anterior:
            enviar_correo_async(agente_anterior.correo, asunto, cuerpo)
        enviar_correo_async(agente_nuevo.correo, asunto, cuerpo)
    except Exception as e:
        print(f"Error en notificar_reasignacion_ticket: {str(e)}")



# 🔹 Decorador para proteger rutas según el rol  
def role_required(roles_permitidos):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                current_user_id = get_jwt_identity()  # Obtiene el usuario actual desde JWT
                usuario = Usuario.query.get(current_user_id)
                if not usuario or usuario.rol_obj.nombre not in roles_permitidos:
                    return jsonify({'message': 'No tienes permiso para realizar esta acción'}), 403
                return func(*args, **kwargs)
            except Exception as e:
                print(f"🔸 Error en role_required: {e}")
                return jsonify({'message': 'Error al verificar permisos'}), 500
        return wrapper
    return decorator


# 🔹 Decorador para permisos segun el rol
def permiso_requerido(roles_permitidos):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_user_id = get_jwt_identity()
            usuario = Usuario.query.get(current_user_id)
            if not usuario or usuario.rol_obj.nombre not in roles_permitidos:
                return jsonify({'message': 'Acceso denegado'}), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Ruta para obtener tickets
@api.route('/tickets', methods=['GET'])
@jwt_required()
@app_required(1)  # ✅ Requiere acceso a la app con id=1
def get_tickets():
    try:
        current_user_id = get_jwt_identity()
        usuario = Usuario.query.get(current_user_id)

        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Obtener tickets según el rol del usuario
        if usuario.rol_obj.nombre == "ADMINISTRADOR":
            # Administradores ven todos los tickets
            tickets = Ticket.query.order_by(Ticket.fecha_creacion.desc()).all()
        elif usuario.rol_obj.nombre == "AGENTE":
            # Obtener los departamentos asignados al agente
            departamentos_ids = [d.id for d in usuario.departamentos]
            
            # Agentes ven tickets de sus departamentos asignados
            tickets = Ticket.query.filter(
                Ticket.id_departamento.in_(departamentos_ids)
            ).order_by(Ticket.fecha_creacion.desc()).all()
        else:  # Usuario normal
            # Usuarios normales ven sus propios tickets
            tickets = Ticket.query.filter_by(id_usuario=current_user_id).order_by(Ticket.fecha_creacion.desc()).all()

        ticket_list = []
        for ticket in tickets:
            sucursal_obj = Sucursal.query.get(ticket.id_sucursal)
            nombre_sucursal = sucursal_obj.nombre if sucursal_obj else "No asignada"
            ticket_list.append({
                "id": ticket.id,
                "titulo": ticket.titulo,
                "descripcion": ticket.descripcion,
                "id_usuario": ticket.id_usuario,
                "id_agente": ticket.id_agente,
                "usuario": (
                    ticket.usuario.nombre_completo
                    if ticket.usuario else "Sin usuario"
                ),
                "agente": (
                    ticket.agente.nombre_completo
                    if ticket.agente else "Sin asignar"
                ),
                "estado": ticket.estado.nombre,
                "prioridad": ticket.prioridad.nombre,
                "departamento": ticket.departamento.nombre if ticket.departamento else None,
                "id_departamento": ticket.id_departamento,
                "id_categoria": ticket.id_categoria,
                "categoria": ticket.categoria.nombre if ticket.categoria else None,
                "sucursal": nombre_sucursal,
                "fecha_creacion": ticket.fecha_creacion.astimezone(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_creacion else None,
                "fecha_cierre": ticket.fecha_cierre.astimezone(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_cierre else None,
                "adjunto": ticket.adjunto,
                "id_prioridad": ticket.id_prioridad,
                "id_estado": ticket.id_estado
            })

        return jsonify(ticket_list), 200

    except Exception as e:
        print(f"🔸 Error en get_tickets: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los tickets'}), 500

@api.route('/tickets/<int:id>', methods=['GET'])
@jwt_required()
def get_ticket(id):
    ticket = Ticket.query.get(id)
    if not ticket:
        return jsonify({'message': 'Ticket no encontrado'}), 404

    # Obtener comentarios del ticket
    comentarios = TicketComentario.query.filter_by(id_ticket=id).all()
    comentarios_list = [
        {
            'id': c.id,
            'id_ticket': c.id_ticket,
            'id_usuario': c.id_usuario,
            'usuario': (
                Usuario.query.get(c.id_usuario).nombre_completo
                if Usuario.query.get(c.id_usuario) else None
            ),
            'comentario': c.comentario,
            'creado': c.timestamp.strftime('%Y-%m-%d %H:%M:%S') if c.timestamp else None
        }
        for c in comentarios
    ]

    sucursal_obj = Sucursal.query.get(ticket.id_sucursal)
    nombre_sucursal = sucursal_obj.nombre if sucursal_obj else "No asignada"
    ticket_data = {
        "id": ticket.id,
        "titulo": ticket.titulo,
        "descripcion": ticket.descripcion,
        "id_usuario": ticket.id_usuario,
        "id_agente": ticket.id_agente,
        "usuario": (
            ticket.usuario.nombre_completo
            if ticket.usuario else "Sin usuario"
        ),
        "agente": (
            ticket.agente.nombre_completo
            if ticket.agente else "Sin asignar"
        ),
        "estado": ticket.estado.nombre if ticket.estado else None,
        "prioridad": ticket.prioridad.nombre if ticket.prioridad else None,
        "departamento": ticket.departamento.nombre if ticket.departamento else None,
        "id_departamento": ticket.id_departamento,
        "id_categoria": ticket.id_categoria,
        "categoria": ticket.categoria.nombre if ticket.categoria else None,
        "sucursal": nombre_sucursal,
        "fecha_creacion": ticket.fecha_creacion.astimezone(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_creacion else None,
        "fecha_cierre": ticket.fecha_cierre.astimezone(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_cierre else None,
        "adjunto": ticket.adjunto,
        "comentarios": comentarios_list,
        "id_prioridad": ticket.id_prioridad,
        "id_estado": ticket.id_estado
    }
    return jsonify(ticket_data), 200

# Ruta para crear un nuevo ticket
@api.route('/tickets', methods=['POST'])
@jwt_required()
@permiso_requerido(['ADMINISTRADOR', 'AGENTE', 'USUARIO'])
@app_required(1)  # ✅ Requiere acceso a la app con id=1
def create_ticket():
    try:
        data = request.get_json()
        current_user_id = str(get_jwt_identity())
        current_user = Usuario.query.get(current_user_id)
        id_departamento = data.get('id_departamento')
        id_categoria = data.get('id_categoria')

        if not id_departamento:
            return jsonify({'error': 'Debe seleccionar un departamento'}), 400
        
        if not id_categoria:
            return jsonify({'error': 'Debe seleccionar una categoría'}), 400

        # Verificar que la categoría pertenece al departamento
        categoria = Categoria.query.get(id_categoria)
        if not categoria or categoria.id_departamento != id_departamento:
            return jsonify({'error': 'La categoría no pertenece al departamento seleccionado'}), 400

        # ✅ Obtener el agente responsable de la categoría
        id_agente = None
        if categoria and categoria.id_usuario:
            # Verificar que el agente asignado a la categoría pertenece al departamento
            agente_categoria = Usuario.query.get(categoria.id_usuario)
            if agente_categoria and agente_categoria.rol_obj.nombre == 'AGENTE':
                # Verificar que el agente pertenece al departamento
                agente_en_departamento = db.session.query(ticket_pivot_departamento_agente).filter(
                    ticket_pivot_departamento_agente.c.id_usuario == categoria.id_usuario,
                    ticket_pivot_departamento_agente.c.id_departamento == id_departamento
                ).first()
                
                if agente_en_departamento:
                    id_agente = str(categoria.id_usuario)
        
        # Si no hay agente asignado a la categoría, asignar aleatoriamente
        if not id_agente:
            agentes = Usuario.query.join(ticket_pivot_departamento_agente).filter(
                ticket_pivot_departamento_agente.c.id_departamento == id_departamento
            ).all()
            id_agente = str(random.choice(agentes).id) if agentes else None

        # Obtener el estado "Abierto" y prioridad "Baja" si no se especifican
        estado_abierto = TicketEstado.query.filter_by(nombre="Abierto").first()
        prioridad_baja = TicketPrioridad.query.filter_by(nombre="Baja").first()

        nuevo_ticket = Ticket(
            id_usuario=current_user_id,
            id_agente=id_agente,
            id_sucursal=current_user.id_sucursalactiva,  # Usar la sucursal activa del usuario
            id_estado=data.get('id_estado', estado_abierto.id if estado_abierto else None),
            id_prioridad=data.get('id_prioridad', prioridad_baja.id if prioridad_baja else None),
            id_departamento=id_departamento,
            id_categoria=id_categoria,
            titulo=data.get('titulo'),
            descripcion=data.get('descripcion')
        )

        db.session.add(nuevo_ticket)
        db.session.commit()

        # Notificar creación del ticket
        agente = Usuario.query.get(id_agente) if id_agente else None
        notificar_creacion_ticket(nuevo_ticket, current_user, agente)

        return jsonify({'message': 'Ticket creado exitosamente', 'ticket_id': nuevo_ticket.id}), 201

    except Exception as e:
        return jsonify({'error': 'Ocurrió un error al crear el ticket'}), 500

# Extensiones permitidas
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'xlsx'}

# Función para verificar si el archivo tiene una extensión válida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ruta para actualizar un ticket
@api.route('/tickets/<int:id>', methods=['PUT'])
@jwt_required()
def update_ticket(id):
    current_user_id = get_jwt_identity()
    usuario = Usuario.query.get(current_user_id)
    ticket = Ticket.query.get(id)

    if not ticket:
        return jsonify({'message': 'Ticket no encontrado'}), 404

    if usuario.rol_obj.nombre == 'ADMINISTRADOR':
        pass  # Puede editar cualquier ticket
    elif usuario.rol_obj.nombre == 'AGENTE':
        departamentos_ids = [d.id for d in usuario.departamentos]
        if ticket.id_departamento not in departamentos_ids:
            return jsonify({'message': 'No tienes permiso para editar este ticket'}), 403
    else:
        if ticket.id_usuario != usuario.id:
            return jsonify({'message': 'No tienes permiso para editar este ticket'}), 403

    data = request.get_json() or {}

    # Validación mínima
    if not data:
        return jsonify({'message': 'Datos JSON no proporcionados'}), 400

    ticket.titulo = data.get('titulo', ticket.titulo)
    ticket.descripcion = data.get('descripcion', ticket.descripcion)

    # Actualizar categoría si se proporciona
    if 'id_categoria' in data:
        categoria = Categoria.query.get(data['id_categoria'])
        if not categoria or categoria.id_departamento != ticket.id_departamento:
            return jsonify({'error': 'La categoría no pertenece al departamento del ticket'}), 400
        ticket.id_categoria = data['id_categoria']

    # Manejo de archivo opcional
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'Nombre de archivo inválido'}), 400
        if not allowed_file(file.filename):
            return jsonify({'message': 'Tipo de archivo no permitido'}), 400

        upload_folder = 'uploads'
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"t{id}_{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        ticket.adjunto = unique_filename

    # ✅ Validación de estado, solo si se envía en el payload
    nuevo_estado = None
    if 'id_estado' in data:
        estado_obj = TicketEstado.query.get(data['id_estado'])
        if not estado_obj:
            return jsonify({'error': 'Estado no válido'}), 400
        ticket.id_estado = data['id_estado']
        nuevo_estado = estado_obj.nombre

    try:
        db.session.commit()

        # Solo si se cambió el estado, disparamos notificación
        if nuevo_estado:
            agente = Usuario.query.get(ticket.id_agente) if ticket.id_agente else None
            notificar_cambio_estado(ticket, usuario, agente, nuevo_estado)

        return jsonify({'message': 'Ticket actualizado correctamente', 'adjunto': ticket.adjunto}), 200
    except Exception as e:
        db.session.rollback()
        print(f"🔸 Error en update_ticket: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al actualizar el ticket'}), 500




# Ruta para eliminar un ticket
@api.route('/tickets/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_ticket(id):
    current_user_id = get_jwt_identity()
    usuario = Usuario.query.get(current_user_id)
    ticket = Ticket.query.get(id)

    if not ticket:
        return jsonify({'message': 'Ticket no encontrado'}), 404

    if usuario.rol_obj.nombre == 'ADMINISTRADOR':
        pass  # Puede eliminar cualquier ticket
    elif usuario.rol_obj.nombre == 'AGENTE':
        departamentos_ids = [d.id for d in usuario.departamentos]
        if ticket.id_departamento not in departamentos_ids:
            return jsonify({'message': 'No tienes permiso para eliminar este ticket'}), 403
    else:
        if ticket.id_usuario != usuario.id:
            return jsonify({'message': 'No tienes permiso para eliminar este ticket'}), 403

    db.session.delete(ticket)
    db.session.commit()
    return jsonify({'message': 'Ticket eliminado correctamente'})

# Rutas para obtener prioridades, departamentos y estados
@api.route('/prioridades', methods=['GET'])
@jwt_required()
def get_prioridades():
    try:
        prioridades = TicketPrioridad.query.all()
        return jsonify([{'id': p.id, 'nombre': p.nombre} for p in prioridades]), 200
    except Exception as e:
        print(f"🔸 Error en get_prioridades: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener las prioridades'}), 500

@api.route('/departamentos', methods=['GET'])
@jwt_required()
def get_departamentos():
    try:
        departamentos = Departamento.query.all()
        return jsonify([{'id': d.id, 'nombre': d.nombre} for d in departamentos]), 200
    except Exception as e:
        print(f"🔸 Error en get_departamentos: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los departamentos'}), 500

@api.route('/estados', methods=['GET'])
@jwt_required()
def get_estados():
    try:
        estados = TicketEstado.query.all()
        return jsonify([{'id': e.id, 'nombre': e.nombre} for e in estados]), 200
    except Exception as e:
        print(f"🔸 Error en get_estados: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los estados'}), 500

# Ruta para registro de usuarios
@auth.route('/register', methods=['POST'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def register():
    try:
        data = request.get_json()
        # Log para debug removido
        
        # Validar campos requeridos
        campos_requeridos = ['usuario', 'clave', 'correo', 'id_rol', 'id_sucursalactiva', 'sucursales_autorizadas']
        for campo in campos_requeridos:
            if campo not in data:
                return jsonify({'error': f'El campo {campo} es requerido'}), 400

        # Verificar si el usuario ya existe
        existing_user = Usuario.query.filter_by(correo=data['correo']).first()
        if existing_user:
            return jsonify({'message': 'El usuario ya existe'}), 400

        # Verificar si el usuario ya existe
        existing_username = Usuario.query.filter_by(usuario=data['usuario']).first()
        if existing_username:
            return jsonify({'message': 'El nombre de usuario ya existe'}), 400

        # Generar ID único para el usuario
        user_id = str(uuid.uuid4())

        # Encriptar la contraseña
        hashed_password = bcrypt.hashpw(data['clave'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Asegurarse de que la sucursal activa esté en las sucursales autorizadas
        sucursales_autorizadas = set(data['sucursales_autorizadas'])
        if data['id_sucursalactiva'] not in sucursales_autorizadas:
            sucursales_autorizadas.add(data['id_sucursalactiva'])
            # Log removido

        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            id=user_id,
            usuario=data['usuario'],
            nombre=data['nombre'],
            apellido_paterno=data['apellido_paterno'],
            apellido_materno=data.get('apellido_materno'),
            correo=data['correo'],
            clave=hashed_password,
            fecha_creacion=datetime.now().date(),
            id_rol=data.get('id_rol', 3),
            id_sucursalactiva=data.get('id_sucursalactiva'),
            id_estado=data.get('id_estado', 1),
            id_perfil=data.get('id_perfil', 1)
        )
            
        # Agregar sucursales autorizadas (incluyendo la sucursal activa)
        sucursales = Sucursal.query.filter(Sucursal.id.in_(sucursales_autorizadas)).all()
        nuevo_usuario.sucursales_autorizadas = sucursales
        # Log removido

        db.session.add(nuevo_usuario)
        db.session.commit()

        # Obtener el usuario creado para la respuesta
        usuario_creado = Usuario.query.get(user_id)
        return jsonify({
            'message': 'Usuario registrado exitosamente',
            'usuario': {
                'id': usuario_creado.id,
                'usuario': usuario_creado.usuario,
                'nombre': usuario_creado.nombre_completo,
                'correo': usuario_creado.correo,
                'rol': usuario_creado.rol_obj.nombre
            }
        }), 201
    except Exception as e:
        print(f"🔸 Error en register: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Ocurrió un error al registrar el usuario: {str(e)}'}), 500

# Ruta para iniciar sesión
@auth.route('/login', methods=['POST'])
@cross_origin()
def login():
    try:
        data = request.get_json()
        usuario = Usuario.query.filter_by(correo=data.get('correo')).first()
        
        if not usuario or not bcrypt.checkpw(data['clave'].encode('utf-8'), usuario.clave.encode('utf-8')):
            return jsonify({'message': 'Credenciales inválidas'}), 401
        
        # ✅ Verificar que el usuario esté activo (id_estado=1)
        if usuario.id_estado != 1:
            return jsonify({'message': 'Tu cuenta no está activa. Contacta al administrador.'}), 403
        
        # ✅ Verificar que el usuario tenga acceso a la app con id_app=1
        app_acceso = db.session.query(usuario_pivot_app_usuario).filter(
            usuario_pivot_app_usuario.c.id_usuario == usuario.id,
            usuario_pivot_app_usuario.c.id_app == 1
        ).first()
        
        if not app_acceso:
            return jsonify({'message': 'No tienes acceso a esta aplicación'}), 403
        
        # Acceder a rol_obj para obtener el rol del usuario
        rol = usuario.rol_obj.nombre  # Aquí se accede al nombre del rol

        # Obtener información de la sucursal activa
        sucursal_activa = Sucursal.query.get(usuario.id_sucursalactiva)

        # Crear access token y refresh token
        access_token = create_access_token(identity=str(usuario.id))
        refresh_token = create_refresh_token(identity=str(usuario.id))

        # Obtener las sucursales autorizadas
        sucursales_autorizadas = [
            {
                'id': sucursal.id,
                'nombre': sucursal.nombre
            } for sucursal in usuario.sucursales_autorizadas
        ]

        response_data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'usuario': {
                'id': usuario.id,
                'usuario': usuario.usuario,
                'nombre': usuario.nombre_completo,
                'correo': usuario.correo,
                'id_rol': usuario.id_rol,
                'rol': rol,
                'sucursal_activa': {
                    'id': sucursal_activa.id if sucursal_activa else None,
                    'nombre': sucursal_activa.nombre if sucursal_activa else None
                },
                'sucursales_autorizadas': sucursales_autorizadas
            }
        }
        return jsonify(response_data), 200
    except Exception as e:
        print(f"🔸 Error en login: {str(e)}")
        return jsonify({'error': 'Ocurrió un error en el inicio de sesión'}), 500

# Nueva ruta para refresh token
@auth.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        current_user_id = get_jwt_identity()
        new_access_token = create_access_token(identity=current_user_id)
        return jsonify({'access_token': new_access_token}), 200
    except Exception as e:
        print(f"🔸 Error en refresh token: {str(e)}")
        return jsonify({'error': 'Error al refrescar el token'}), 500

# Ruta para obtener comentarios de un ticket
@api.route('/tickets/<int:ticket_id>/comentarios', methods=['GET'])
@jwt_required()
def get_ticket_comentarios(ticket_id):
    try:
        comentarios = TicketComentario.query.filter_by(id_ticket=ticket_id).all()
        comentarios_list = [
            {
                'id': c.id,
                'id_ticket': c.id_ticket,
                'id_usuario': c.id_usuario,
                'usuario': (
                    Usuario.query.get(c.id_usuario).nombre_completo
                    if Usuario.query.get(c.id_usuario) else None
                ),
                'comentario': c.comentario,
                'creado': c.timestamp.strftime('%Y-%m-%d %H:%M:%S') if c.timestamp else None
            }
            for c in comentarios
        ]
        return jsonify(comentarios_list), 200
    except Exception as e:
        print(f"🔸 Error al obtener comentarios: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los comentarios'}), 500


# Ruta para agregar un comentario a un ticket
@api.route('/tickets/<int:ticket_id>/comentarios', methods=['POST'])
@jwt_required()
@role_required(['USUARIO', 'AGENTE', 'ADMINISTRADOR'])
def add_ticket_comentario(ticket_id):
    try:
        data = request.get_json()
        current_user = get_jwt_identity()
        nuevo_comentario = TicketComentario(
            id_ticket=ticket_id,
            id_usuario=current_user,
            comentario=data.get('comentario')
        )
        db.session.add(nuevo_comentario)
        db.session.commit()

       # Notificar nuevo comentario
        ticket = Ticket.query.get(ticket_id)
        usuario = Usuario.query.get(ticket.id_usuario)
        agente = Usuario.query.get(ticket.id_agente) if ticket.id_agente else None
        notificar_comentario(ticket, usuario, agente, data.get('comentario'))
        return jsonify({'message': 'Comentario agregado correctamente'}), 201
    except Exception as e:
        print(f"🔸 Error al agregar comentario: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al agregar el comentario'}), 500


@api.route('/tickets/<int:ticket_id>/asignar', methods=['PUT'])
@jwt_required()
@role_required(['ADMINISTRADOR', 'AGENTE'])  # ✅ Permitir también a Agentes
def assign_ticket(ticket_id):
    try:
        current_user_id = get_jwt_identity()
        usuario_actual = Usuario.query.get(current_user_id)
        ticket = Ticket.query.get(ticket_id)

        if not ticket:
            return jsonify({'message': 'Ticket no encontrado'}), 404

        data = request.get_json()
        # ✅ Aceptar tanto 'id_agente' como 'agente_id' para compatibilidad
        nuevo_agente_id = data.get('id_agente') or data.get('agente_id')
        nuevo_agente = Usuario.query.get(nuevo_agente_id)

        # ✅ Validación del rol de agente
        if not nuevo_agente:
            return jsonify({'message': 'Usuario no encontrado'}), 400
        
        # Verificar que el usuario tenga rol de agente
        rol_es_agente = False
        
        # Verificar por ID de rol (2 = AGENTE)
        if nuevo_agente.id_rol == 2:
            rol_es_agente = True
        
        # Verificar por nombre de rol (más flexible)
        elif nuevo_agente.rol_obj and nuevo_agente.rol_obj.nombre:
            rol_nombre = nuevo_agente.rol_obj.nombre.upper()
            if 'AGENTE' in rol_nombre:
                rol_es_agente = True
        
        # Si no es agente, verificar si es administrador (puede reasignar)
        elif nuevo_agente.id_rol == 1 or (nuevo_agente.rol_obj and 'ADMIN' in nuevo_agente.rol_obj.nombre.upper()):
            rol_es_agente = True
        
        if not rol_es_agente:
            return jsonify({'message': 'El usuario seleccionado no es un Agente'}), 400

        # Guardar el agente anterior antes de reasignar
        agente_anterior = Usuario.query.get(ticket.id_agente) if ticket.id_agente else None

        # 🔹 Si es Administrador, puede reasignar a cualquier agente
        if usuario_actual.rol_obj.nombre == "ADMINISTRADOR":
            ticket.id_agente = nuevo_agente_id

        # 🔹 Si es Agente, solo puede reasignar a agentes de su departamento
        elif usuario_actual.rol_obj.nombre == "AGENTE":
            # Verificar que el agente actual pertenece al departamento del ticket
            agente_en_departamento = db.session.query(ticket_pivot_departamento_agente).filter(
                ticket_pivot_departamento_agente.c.id_usuario == current_user_id,
                ticket_pivot_departamento_agente.c.id_departamento == ticket.id_departamento
            ).first()
            
            if not agente_en_departamento:
                return jsonify({'message': 'No tienes permiso para reasignar tickets de este departamento'}), 403
            
            # Verificar que el nuevo agente pertenece al mismo departamento
            nuevo_agente_en_departamento = db.session.query(ticket_pivot_departamento_agente).filter(
                ticket_pivot_departamento_agente.c.id_usuario == nuevo_agente_id,
                ticket_pivot_departamento_agente.c.id_departamento == ticket.id_departamento
            ).first()
            
            if not nuevo_agente_en_departamento:
                return jsonify({'message': 'Solo puedes reasignar a agentes de tu mismo departamento'}), 403

            ticket.id_agente = nuevo_agente_id

        else:
            return jsonify({'message': 'No tienes permiso para reasignar tickets'}), 403

        # 🔹 Cambiar estado a "En Proceso" automáticamente si aún no lo está
        estado_en_proceso = TicketEstado.query.filter_by(nombre="En Proceso").first()
        if estado_en_proceso and ticket.id_estado != estado_en_proceso.id:
            ticket.id_estado = estado_en_proceso.id

        db.session.commit()

        # Notificar reasignación del ticket
        usuario = Usuario.query.get(ticket.id_usuario)
        notificar_reasignacion_ticket(ticket, usuario, agente_anterior, nuevo_agente)

        return jsonify({'message': 'Ticket reasignado correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ocurrió un error al reasignar el ticket'}), 500


# Ruta de debug para verificar roles de usuarios
@api.route('/debug/usuarios-roles', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def debug_usuarios_roles():
    try:
        usuarios = Usuario.query.all()
        usuarios_info = []
        
        for usuario in usuarios:
            usuarios_info.append({
                'id': usuario.id,
                'nombre': usuario.nombre_completo,
                'id_rol': usuario.id_rol,
                'rol_nombre': usuario.rol_obj.nombre if usuario.rol_obj else 'Sin rol',
                'correo': usuario.correo,
                'es_agente': usuario.id_rol == 2 or (usuario.rol_obj and 'AGENTE' in usuario.rol_obj.nombre.upper())
            })
        
        return jsonify(usuarios_info), 200
    except Exception as e:
        return jsonify({'error': 'Error al obtener información de usuarios'}), 500

# Ruta para obtener agentes disponibles para reasignación (Agentes y Administradores)
@api.route('/agentes', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR', 'AGENTE'])
def get_agentes():
    try:
        current_user_id = get_jwt_identity()
        usuario_actual = Usuario.query.get(current_user_id)
        
        # Si es administrador, puede ver todos los agentes
        if usuario_actual.rol_obj.nombre == 'ADMINISTRADOR':
            agentes = Usuario.query.filter(Usuario.id_rol == Rol.query.filter_by(nombre='AGENTE').first().id).all()
            return jsonify([
                {
                    'id': a.id,
                    'nombre': a.nombre_completo
                }
                for a in agentes
            ]), 200
        
        # Si es agente, solo puede ver agentes de su departamento
        elif usuario_actual.rol_obj.nombre == 'AGENTE':
            # Obtener departamentos del agente actual
            departamentos_agente = db.session.query(ticket_pivot_departamento_agente.c.id_departamento).filter(
                ticket_pivot_departamento_agente.c.id_usuario == current_user_id
            ).all()
            
            departamentos_ids = [d[0] for d in departamentos_agente]
            
            # Obtener agentes que pertenecen a los mismos departamentos
            agentes = Usuario.query.join(ticket_pivot_departamento_agente).filter(
                Usuario.id_rol == Rol.query.filter_by(nombre='AGENTE').first().id,
                ticket_pivot_departamento_agente.c.id_departamento.in_(departamentos_ids)
            ).distinct().all()
            
            return jsonify([
                {
                    'id': a.id,
                    'nombre': a.nombre_completo
                }
                for a in agentes
            ]), 200
        
        else:
            return jsonify({'error': 'No tienes permiso para ver agentes'}), 403
    except Exception as e:
        return jsonify({'error': 'Ocurrió un error al obtener la lista de agentes'}), 500


# Ruta para obtener agentes disponibles para reasignar tickets (Agentes y Administradores)
@api.route('/tickets/<int:ticket_id>/agentes-disponibles', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR', 'AGENTE'])
def get_agentes_disponibles_para_reasignacion(ticket_id):
    try:
        current_user_id = get_jwt_identity()
        usuario_actual = Usuario.query.get(current_user_id)
        ticket = Ticket.query.get(ticket_id)
        
        if not ticket:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        # Si es administrador, puede ver todos los agentes del departamento
        if usuario_actual.rol_obj.nombre == 'ADMINISTRADOR':
            agentes = Usuario.query.join(ticket_pivot_departamento_agente).filter(
                Usuario.id_rol == Rol.query.filter_by(nombre='AGENTE').first().id,
                ticket_pivot_departamento_agente.c.id_departamento == ticket.id_departamento
            ).all()
        
        # Si es agente, verificar que pertenece al departamento del ticket
        elif usuario_actual.rol_obj.nombre == 'AGENTE':
            agente_en_departamento = db.session.query(ticket_pivot_departamento_agente).filter(
                ticket_pivot_departamento_agente.c.id_usuario == current_user_id,
                ticket_pivot_departamento_agente.c.id_departamento == ticket.id_departamento
            ).first()
            
            if not agente_en_departamento:
                return jsonify({'error': 'No tienes permiso para ver agentes de este departamento'}), 403
            
            # Obtener agentes del mismo departamento
            agentes = Usuario.query.join(ticket_pivot_departamento_agente).filter(
                Usuario.id_rol == Rol.query.filter_by(nombre='AGENTE').first().id,
                ticket_pivot_departamento_agente.c.id_departamento == ticket.id_departamento
            ).all()
        
        else:
            return jsonify({'error': 'No tienes permiso para ver agentes'}), 403
        
        return jsonify([
            {
                'id': a.id,
                'nombre': a.nombre_completo,
                'correo': a.correo
            }
            for a in agentes
        ]), 200
        
    except Exception as e:
        return jsonify({'error': 'Ocurrió un error al obtener los agentes disponibles'}), 500

# Ruta para obtener sucursales
@api.route('/sucursales', methods=['GET'])
@jwt_required()
def get_sucursales():
    try:
        sucursales = Sucursal.query.all()
        return jsonify([{'id': s.id, 'nombre': s.nombre} for s in sucursales]), 200
    except Exception as e:
        return jsonify({'error': f'Error al obtener sucursales: {str(e)}'}), 500


# Ruta para obtener todos los roles
@api.route('/roles', methods=['GET'])
@jwt_required()  # Solo requiere autenticación
def get_roles():
    try:
        roles = Rol.query.all()
        return jsonify([{'id': r.id, 'rol': r.nombre} for r in roles]), 200
    except Exception as e:
        print(f"🔸 Error en get_roles: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los roles'}), 500

# 🔹 Ruta de depuración para ver todos los roles disponibles
@api.route('/debug/roles', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def debug_roles():
    try:
        roles = Rol.query.all()
        # Logs de debug removidos
        
        return jsonify([{
            'id': r.id, 
            'nombre': r.nombre,
            'nombre_upper': r.nombre.upper() if r.nombre else None
        } for r in roles]), 200
    except Exception as e:
        print(f"🔸 Error en debug_roles: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los roles'}), 500

# 🔹 Ruta de depuración para ver agentes y sus departamentos
@api.route('/debug/agentes-departamentos', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def debug_agentes_departamentos():
    try:
        # Obtener todos los usuarios con rol AGENTE
        rol_agente = Rol.query.filter_by(nombre='AGENTE').first()
        if not rol_agente:
            return jsonify({'error': 'Rol AGENTE no encontrado'}), 404
        
        agentes = Usuario.query.filter(Usuario.id_rol == rol_agente.id).all()
        
        # Logs de debug removidos
        agentes_info = []
        
        for agente in agentes:
            agentes_info.append({
                'id': agente.id,
                'nombre': agente.nombre_completo,
                'correo': agente.correo,
                'rol': agente.rol_obj.nombre,
                'departamentos': [{'id': d.id, 'nombre': d.nombre} for d in agente.departamentos]
            })
        
        return jsonify(agentes_info), 200
    except Exception as e:
        print(f"🔸 Error en debug_agentes_departamentos: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener la información de agentes'}), 500

# 🔹 Ruta de depuración para ver información de una categoría específica
@api.route('/debug/categoria/<categoria_id>', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def debug_categoria(categoria_id):
    try:
        categoria = Categoria.query.get(categoria_id)
        if not categoria:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        # Logs de debug removidos
        
        return jsonify({
            'id': categoria.id,
            'nombre': categoria.nombre,
            'departamento': {
                'id': categoria.departamento.id,
                'nombre': categoria.departamento.nombre
            },
            'usuario_responsable': {
                'id': categoria.usuario_responsable.id,
                'nombre': categoria.usuario_responsable.nombre_completo
            } if categoria.usuario_responsable else None
        }), 200
    except Exception as e:
        print(f"🔸 Error en debug_categoria: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener la información de la categoría'}), 500

# 🔹 Ruta de depuración para ver asignaciones de agentes a departamentos
@api.route('/debug/agentes-departamentos-tabla', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def debug_agentes_departamentos_tabla():
    try:
        # Obtener todas las asignaciones de la tabla pivot
        asignaciones = db.session.query(ticket_pivot_departamento_agente).all()
        
        # Logs de debug removidos
        
        return jsonify([{
            'id_usuario': a.id_usuario,
            'id_departamento': a.id_departamento,
            'agente_nombre': Usuario.query.get(a.id_usuario).nombre_completo if Usuario.query.get(a.id_usuario) else 'N/A',
            'departamento_nombre': Departamento.query.get(a.id_departamento).nombre if Departamento.query.get(a.id_departamento) else 'N/A'
        } for a in asignaciones]), 200
    except Exception as e:
        print(f"🔸 Error en debug_agentes_departamentos_tabla: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener las asignaciones'}), 500

# 🔹 Ruta de prueba para verificar agentes por departamento
@api.route('/debug/test-agentes-departamento/<int:departamento_id>', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def test_agentes_por_departamento(departamento_id):
    try:
        # Log de debug removido
        
        # Obtener el rol AGENTE
        rol_agente = Rol.query.filter_by(nombre='AGENTE').first()
        if not rol_agente:
            return jsonify({'error': 'Rol AGENTE no encontrado'}), 404
        
        # Obtener agentes del departamento específico
        agentes = db.session.query(Usuario).join(
            ticket_pivot_departamento_agente,
            Usuario.id == ticket_pivot_departamento_agente.c.id_usuario
        ).filter(
            Usuario.id_rol == rol_agente.id,
            ticket_pivot_departamento_agente.c.id_departamento == departamento_id
        ).all()
        
        # Logs de debug removidos
        
        return jsonify([{
            'id': agente.id,
            'nombre': agente.nombre_completo,
            'correo': agente.correo,
            'rol': agente.rol_obj.nombre
        } for agente in agentes]), 200
    except Exception as e:
        print(f"🔸 Error en test_agentes_por_departamento: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los agentes'}), 500

# 🔹 Ruta para ver todos los departamentos y sus agentes
@api.route('/debug/departamentos-agentes', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def debug_departamentos_agentes():
    try:
        # Obtener todos los departamentos
        departamentos = Departamento.query.all()
        
        # Obtener el rol AGENTE
        rol_agente = Rol.query.filter_by(nombre='AGENTE').first()
        if not rol_agente:
            return jsonify({'error': 'Rol AGENTE no encontrado'}), 404
        
        resultado = []
        
        for departamento in departamentos:
            # Log de debug removido
            
            # Obtener agentes del departamento
            agentes = db.session.query(Usuario).join(
                ticket_pivot_departamento_agente,
                Usuario.id == ticket_pivot_departamento_agente.c.id_usuario
            ).filter(
                Usuario.id_rol == rol_agente.id,
                ticket_pivot_departamento_agente.c.id_departamento == departamento.id
            ).all()
            
            # Logs de debug removidos
            
            resultado.append({
                'departamento': {
                    'id': departamento.id,
                    'nombre': departamento.nombre
                },
                'agentes': [{
                    'id': agente.id,
                    'nombre': agente.nombre_completo,
                    'correo': agente.correo
                } for agente in agentes]
            })
        
        return jsonify(resultado), 200
    except Exception as e:
        print(f"🔸 Error en debug_departamentos_agentes: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener la información'}), 500

# 🔹 Ruta para ver todas las categorías y sus departamentos
@api.route('/debug/categorias-departamentos', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def debug_categorias_departamentos():
    try:
        # Obtener todas las categorías
        categorias = Categoria.query.all()
        
        resultado = []
        
        for categoria in categorias:
            # Logs de debug removidos
            
            resultado.append({
                'categoria': {
                    'id': categoria.id,
                    'nombre': categoria.nombre
                },
                'departamento': {
                    'id': categoria.departamento.id,
                    'nombre': categoria.departamento.nombre
                }
            })
        
        return jsonify(resultado), 200
    except Exception as e:
        print(f"🔸 Error en debug_categorias_departamentos: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener la información'}), 500

# 🔹 Ruta para buscar categoría por nombre
@api.route('/debug/buscar-categoria/<nombre>', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def buscar_categoria_por_nombre(nombre):
    try:
        # Buscar categorías que contengan el nombre
        categorias = Categoria.query.filter(Categoria.nombre.ilike(f'%{nombre}%')).all()
        
        resultado = []
        
        for categoria in categorias:
            # Logs de debug removidos
            
            resultado.append({
                'categoria': {
                    'id': categoria.id,
                    'nombre': categoria.nombre
                },
                'departamento': {
                    'id': categoria.departamento.id,
                    'nombre': categoria.departamento.nombre
                }
            })
        
        return jsonify(resultado), 200
    except Exception as e:
        print(f"🔸 Error en buscar_categoria_por_nombre: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al buscar la categoría'}), 500

# 🔹 Ruta para verificar categoría específica por ID
@api.route('/debug/verificar-categoria/<int:categoria_id>', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def verificar_categoria_especifica(categoria_id):
    try:
        categoria = Categoria.query.get(categoria_id)
        
        if not categoria:
            return jsonify({'error': f'Categoría con ID {categoria_id} no encontrada'}), 404
        
        # Logs de debug removidos
        
        resultado = {
            'categoria': {
                'id': categoria.id,
                'nombre': categoria.nombre
            },
            'departamento': {
                'id': categoria.departamento.id,
                'nombre': categoria.departamento.nombre
            }
        }
        
        return jsonify(resultado), 200
    except Exception as e:
        print(f"🔸 Error en verificar_categoria_especifica: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al verificar la categoría'}), 500

# 🔹 Ruta para verificar asignaciones de agentes a departamentos
@api.route('/debug/verificar-asignaciones-agentes', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def verificar_asignaciones_agentes():
    try:
        # Log de debug removido
        
        # Obtener todos los agentes
        rol_agente = Rol.query.filter_by(nombre='AGENTE').first()
        if not rol_agente:
            rol_agente = Rol.query.filter_by(nombre='Agente').first()
        if not rol_agente:
            rol_agente = Rol.query.filter_by(nombre='agente').first()
        
        if not rol_agente:
            return jsonify({'error': 'Rol AGENTE no encontrado'}), 404
        
        agentes = Usuario.query.filter_by(id_rol=rol_agente.id).all()
        
        resultado = []
        
        for agente in agentes:
            # Logs de debug removidos
            
            # Obtener departamentos asignados directamente de la tabla pivot
            departamentos_asignados = db.session.query(Departamento).join(
                ticket_pivot_departamento_agente,
                Departamento.id == ticket_pivot_departamento_agente.c.id_departamento
            ).filter(
                ticket_pivot_departamento_agente.c.id_usuario == agente.id
            ).all()
            
            resultado.append({
                'agente': {
                    'id': agente.id,
                    'nombre': agente.nombre_completo,
                    'correo': agente.correo
                },
                'departamentos': [{
                    'id': d.id,
                    'nombre': d.nombre
                } for d in departamentos_asignados]
            })
        
        # Log de debug removido
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"🔸 Error en verificar_asignaciones_agentes: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al verificar las asignaciones'}), 500

# 🔹 Ruta temporal para obtener agentes por departamento (solución al problema del frontend)
@api.route('/admin/departamentos/<int:departamento_id>/agentes-disponibles', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def get_agentes_disponibles_por_departamento(departamento_id):
    try:
        print(f"🔍 ===== CONSULTA POR DEPARTAMENTO =====")
        print(f"🔍 Departamento ID: {departamento_id}")
        
        # Obtener el departamento
        departamento = Departamento.query.get(departamento_id)
        if not departamento:
            return jsonify({'error': 'Departamento no encontrado'}), 404
        
        print(f"🔍 Departamento: {departamento.nombre}")
        
        # Obtener el ID del rol AGENTE
        rol_agente = Rol.query.filter_by(nombre='AGENTE').first()
        if not rol_agente:
            rol_agente = Rol.query.filter_by(nombre='Agente').first()
        if not rol_agente:
            rol_agente = Rol.query.filter_by(nombre='agente').first()
        
        if not rol_agente:
            return jsonify({'error': 'Rol AGENTE no encontrado'}), 404
        
        # Obtener agentes del departamento
        agentes_departamento = db.session.query(Usuario).join(
            ticket_pivot_departamento_agente,
            Usuario.id == ticket_pivot_departamento_agente.c.id_usuario
        ).filter(
            Usuario.id_rol == rol_agente.id,
            ticket_pivot_departamento_agente.c.id_departamento == departamento_id
        ).all()
        
        print(f"🔍 Agentes encontrados: {len(agentes_departamento)}")
        for agente in agentes_departamento:
            print(f"  - {agente.nombre_completo}")
        
        # Ordenar alfabéticamente
        agentes_departamento.sort(key=lambda x: x.nombre_completo.lower())
        
        # Crear la respuesta JSON
        response_data = [{
            'id': agente.id,
            'nombre': agente.nombre_completo,
            'correo': agente.correo,
            'rol': agente.rol_obj.nombre,
            'debug_info': {
                'departamento_id': departamento_id,
                'departamento_nombre': departamento.nombre
            }
        } for agente in agentes_departamento]
        
        print(f"🔍 ===== FIN CONSULTA POR DEPARTAMENTO =====")
        
        # Crear respuesta con headers para evitar caché
        response = jsonify(response_data)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Departamento-ID'] = str(departamento_id)
        response.headers['X-Departamento-Nombre'] = departamento.nombre
        
        return response, 200
        
    except Exception as e:
        print(f"🔸 Error en get_agentes_disponibles_por_departamento: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los agentes'}), 500

# 🔹 Ruta para asignar agentes a departamentos (para testing)
@api.route('/debug/asignar-agente-departamento/<agente_id>/<int:departamento_id>', methods=['POST'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def asignar_agente_departamento_debug(agente_id, departamento_id):
    try:
        print(f"🔍 ===== ASIGNANDO AGENTE A DEPARTAMENTO =====")
        print(f"🔍 Agente ID: {agente_id}")
        print(f"🔍 Departamento ID: {departamento_id}")
        
        # Verificar que el agente existe
        agente = Usuario.query.get(agente_id)
        if not agente:
            return jsonify({'error': 'Agente no encontrado'}), 404
        
        # Verificar que el departamento existe
        departamento = Departamento.query.get(departamento_id)
        if not departamento:
            return jsonify({'error': 'Departamento no encontrado'}), 404
        
        print(f"🔍 Agente: {agente.nombre_completo}")
        print(f"🔍 Departamento: {departamento.nombre}")
        
        # Verificar si ya existe la asignación
        asignacion_existente = db.session.query(ticket_pivot_departamento_agente).filter(
            ticket_pivot_departamento_agente.c.id_usuario == agente_id,
            ticket_pivot_departamento_agente.c.id_departamento == departamento_id
        ).first()
        
        if asignacion_existente:
            return jsonify({'message': 'La asignación ya existe'}), 200
        
        # Crear nueva asignación
        nueva_asignacion = ticket_pivot_departamento_agente.insert().values(
            id_usuario=agente_id,
            id_departamento=departamento_id
        )
        
        db.session.execute(nueva_asignacion)
        db.session.commit()
        
        print(f"🔍 Asignación creada exitosamente")
        print(f"🔍 ===== FIN ASIGNACIÓN =====")
        
        return jsonify({'message': 'Agente asignado al departamento exitosamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"🔸 Error en asignar_agente_departamento_debug: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al asignar el agente'}), 500

# 🔹 Ruta para verificar y corregir asignaciones de agentes
@api.route('/debug/corregir-asignaciones-agentes', methods=['POST'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def corregir_asignaciones_agentes():
    try:
        print(f"🔍 ===== CORRIGIENDO ASIGNACIONES DE AGENTES =====")
        
        # Obtener todos los agentes
        rol_agente = Rol.query.filter_by(nombre='AGENTE').first()
        if not rol_agente:
            return jsonify({'error': 'Rol AGENTE no encontrado'}), 404
        
        agentes = Usuario.query.filter_by(id_rol=rol_agente.id).all()
        
        # Asignaciones correctas según la imagen
        asignaciones_correctas = {
            'baac9a2e-4c8c-4cf9-8545-b93e67628b60': [3],  # Maria Jose Mella -> QUÍMICOS
            '87934f06-be75-4ad4-9e1b-f6ce07beb363': [3],  # Patricia Marin -> QUÍMICOS
            '0dd1484f-a2cb-41e9-8ef9-487bf9de0282': [1],  # Teresa Chacan -> CDG Y TI
            '156df4e0-8f0d-46c5-aa7a-cd92a50409f5': [2],  # Hector Molt -> HOSPITAL
            '44536470-225c-4e3a-8ac4-5dc6d45b5cf2': [4]   # Miguel Bravo -> OFICINA CENTRAL
        }
        
        # Eliminar todas las asignaciones existentes
        db.session.execute(ticket_pivot_departamento_agente.delete())
        db.session.commit()
        print(f"🔍 Asignaciones existentes eliminadas")
        
        # Crear nuevas asignaciones correctas
        for agente_id, departamentos in asignaciones_correctas.items():
            for departamento_id in departamentos:
                nueva_asignacion = ticket_pivot_departamento_agente.insert().values(
                    id_usuario=agente_id,
                    id_departamento=departamento_id
                )
                db.session.execute(nueva_asignacion)
                print(f"🔍 Asignado agente {agente_id} al departamento {departamento_id}")
        
        db.session.commit()
        print(f"🔍 ===== ASIGNACIONES CORREGIDAS =====")
        
        return jsonify({'message': 'Asignaciones de agentes corregidas exitosamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"🔸 Error en corregir_asignaciones_agentes: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al corregir las asignaciones'}), 500

# Ruta para filtrar usuarios activos
@api.route('/usuarios', methods=['GET'])
@jwt_required()
def get_usuarios():
    try:
        current_user_id = get_jwt_identity()
        current_user = Usuario.query.get(current_user_id)
        
        if not current_user:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        # Si es administrador, puede ver todos los usuarios
        if current_user.rol_obj.nombre == 'ADMINISTRADOR':
            usuarios = Usuario.query.all()
        # Si es agente, solo ve usuarios de sus sucursales autorizadas
        elif current_user.rol_obj.nombre == 'AGENTE':
            sucursales_ids = [s.id for s in current_user.sucursales_autorizadas]
            usuarios = Usuario.query.filter(
                Usuario.id_sucursalactiva.in_(sucursales_ids)
            ).all()
        # Si es usuario normal, solo ve su propia información
        else:
            usuarios = [current_user]

        usuario_list = [{
            "id": usuario.id,
            "usuario": usuario.usuario,
            "nombre": usuario.nombre_completo,
            "correo": usuario.correo,
            "rol": usuario.rol_obj.nombre,
            "sucursal_activa": {
                "id": usuario.sucursal_obj.id if usuario.sucursal_obj else None,
                "nombre": usuario.sucursal_obj.nombre if usuario.sucursal_obj else "No asignada"
            },
            "sucursales_autorizadas": [
                {
                    "id": sucursal.id,
                    "nombre": sucursal.nombre
                } for sucursal in usuario.sucursales_autorizadas
            ],
            "estado": usuario.estado_obj.nombre,
            "id_departamento": [d.id for d in usuario.departamentos] if usuario.departamentos else None
        } for usuario in usuarios]

        # Ordenar alfabéticamente por nombre
        usuario_list.sort(key=lambda x: x['nombre'].lower())

        return jsonify(usuario_list), 200

    except Exception as e:
        print(f"🔸 Error en get_usuarios: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los usuarios'}), 500

# Ruta para actualizar usuarios 
@api.route('/usuarios/<user_id>', methods=['PUT'])
@jwt_required()
def update_usuario(user_id):
    try:
        current_user_id = get_jwt_identity()
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'message': 'Usuario no encontrado'}), 404

        # Solo permitir que un usuario edite su propio perfil o que un ADMINISTRADOR edite a cualquiera
        current_user = Usuario.query.get(current_user_id)
        if current_user.id != user_id and current_user.rol_obj.nombre != 'ADMINISTRADOR':
            return jsonify({'message': 'No tienes permiso para editar este usuario'}), 403

        data = request.get_json()

        # Actualizar campos básicos
        if 'nombre' in data:
            usuario.nombre = data['nombre']
        if 'apellido_paterno' in data:
            usuario.apellido_paterno = data['apellido_paterno']
        if 'apellido_materno' in data:
            usuario.apellido_materno = data['apellido_materno']
        if 'usuario' in data:
            usuario.usuario = data['usuario']
        if 'correo' in data:
            usuario.correo = data['correo']
        if 'clave' in data and data['clave']:
            usuario.clave = bcrypt.hashpw(data['clave'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        if 'id_rol' in data:
            usuario.id_rol = data['id_rol']
        if 'id_estado' in data:
            usuario.id_estado = data['id_estado']
        if 'id_perfil' in data:
            usuario.id_perfil = data['id_perfil']

        # Actualizar sucursal activa
        if 'id_sucursalactiva' in data:
            # Verificar que la sucursal activa esté en las sucursales autorizadas
            if 'sucursales_autorizadas' in data and data['id_sucursalactiva'] not in data['sucursales_autorizadas']:
                return jsonify({'error': 'La sucursal activa debe estar en las sucursales autorizadas'}), 400
            usuario.id_sucursalactiva = data['id_sucursalactiva']

        # Actualizar sucursales autorizadas
        if 'sucursales_autorizadas' in data:
            # Obtener las sucursales de la base de datos
            sucursales = Sucursal.query.filter(Sucursal.id.in_(data['sucursales_autorizadas'])).all()
            # Actualizar la relación
            usuario.sucursales_autorizadas = sucursales

        # Commit de los cambios
        db.session.commit()

        # Obtener el usuario actualizado para la respuesta
        usuario_actualizado = Usuario.query.get(user_id)
        return jsonify({
            'message': 'Usuario actualizado correctamente',
            'usuario': {
                'id': usuario_actualizado.id,
                'usuario': usuario_actualizado.usuario,
                'nombre': usuario_actualizado.nombre_completo,
                'correo': usuario_actualizado.correo,
                'rol': usuario_actualizado.rol_obj.nombre,
                'sucursal_activa': {
                    'id': usuario_actualizado.sucursal_obj.id,
                    'nombre': usuario_actualizado.sucursal_obj.nombre
                },
                'sucursales_autorizadas': [
                    {
                        'id': sucursal.id,
                        'nombre': sucursal.nombre
                    } for sucursal in usuario_actualizado.sucursales_autorizadas
                ],
                'estado': usuario_actualizado.estado_obj.nombre
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al actualizar usuario: {str(e)}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        return jsonify({'error': f'Error al actualizar usuario: {str(e)}'}), 500

# ruta para eliminar un usurio
@api.route('/usuarios/<user_id>', methods=['DELETE'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def delete_usuario(user_id):
    usuario = Usuario.query.get(user_id)
    if not usuario:
        return jsonify({'message': 'Usuario no encontrado'}), 404
    try:
        # Verificar si el usuario tiene tickets asociados
        tickets_asociados = Ticket.query.filter_by(id_usuario=user_id).count()
        if tickets_asociados > 0:
            return jsonify({'error': 'No se puede eliminar el usuario porque tiene tickets asociados'}), 400
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({'message': 'Usuario eliminado correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"🔸 Error al eliminar usuario: {str(e)}")
        return jsonify({'error': f'Error al eliminar usuario: {str(e)}'}), 500


# Importar archivos a tickets
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'xlsx'}  # Tipos de archivos permitidos

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api.route('/tickets/<int:id>/upload', methods=['POST'])
@jwt_required()
def upload_file(id):
    ticket = Ticket.query.get(id)
    if not ticket:
        return jsonify({'message': 'Ticket no encontrado'}), 404

    if 'file' not in request.files:
        return jsonify({'message': 'No se envió ningún archivo'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'message': 'Nombre de archivo inválido'}), 400

    if not allowed_file(file.filename):
        return jsonify({'message': 'Tipo de archivo no permitido'}), 400

    # Obtener la lista actual de archivos adjuntos
    archivos_actuales = ticket.adjunto.split(',') if ticket.adjunto else []

    # Calcular el hash MD5 del archivo subido
    file_content = file.read()
    file_hash = hashlib.md5(file_content).hexdigest()
    file.seek(0)  # Volver al inicio para subir después

    # Revisar si ya existe un archivo con el mismo hash en Cloud Storage
    hashes_existentes = set()
    for nombre_archivo in archivos_actuales:
        if storage_manager.file_exists(nombre_archivo):
            # Descargar temporalmente para calcular hash
            try:
                blob = storage_manager.bucket.blob(nombre_archivo)
                content = blob.download_as_bytes()
                hash_existente = hashlib.md5(content).hexdigest()
                hashes_existentes.add(hash_existente)
            except Exception as e:
                print(f"⚠️ Error al verificar hash de {nombre_archivo}: {str(e)}")
                continue
    
    if file_hash in hashes_existentes:
        return jsonify({'message': 'Archivo duplicado, ya existe en el ticket', 'adjunto': ticket.adjunto}), 200

    # Subir archivo a Cloud Storage
    upload_result = storage_manager.upload_file(file, id)
    
    if not upload_result['success']:
        return jsonify({'error': upload_result['error']}), 500

    filename = upload_result['filename']
    file_url = upload_result['url']

    # Guardar el nombre del archivo en la base de datos
    try:
        archivos_actuales.append(filename)
        ticket.adjunto = ','.join(archivos_actuales)
        db.session.commit()
        print(f"Archivo {filename} subido a Cloud Storage y guardado en la BD para el ticket {id}")
        return jsonify({
            'message': 'Archivo subido correctamente', 
            'adjunto': ticket.adjunto,
            'url': file_url
        }), 200
    except Exception as e:
        db.session.rollback()
        # Intentar eliminar el archivo de Cloud Storage si falló la BD
        storage_manager.delete_file(filename)
        print(f"🔸 Error al guardar el adjunto en la BD: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al guardar el archivo en la base de datos'}), 500


@api.route('/tickets/<int:id>/adjunto/<nombre_adjunto>', methods=['DELETE'])
@jwt_required()
def eliminar_adjunto(id, nombre_adjunto):
    ticket = Ticket.query.get(id)
    if not ticket:
        return jsonify({'message': 'Ticket no encontrado'}), 404

    # Lista de adjuntos actual
    archivos_actuales = ticket.adjunto.split(',') if ticket.adjunto else []

    if nombre_adjunto not in archivos_actuales:
        return jsonify({'message': 'Adjunto no encontrado en este ticket'}), 404

    # Eliminar el archivo de Cloud Storage
    delete_result = storage_manager.delete_file(nombre_adjunto)
    
    if not delete_result['success']:
        print(f"⚠️ Error al eliminar archivo de Cloud Storage: {delete_result['error']}")
        # Continuar con la eliminación de la BD aunque falle Cloud Storage

    # Quitar el adjunto de la lista y actualizar la base de datos
    archivos_actuales.remove(nombre_adjunto)
    ticket.adjunto = ','.join(archivos_actuales)
    try:
        db.session.commit()
        print(f"Adjunto {nombre_adjunto} eliminado de la BD para el ticket {id}")
        return jsonify({'message': 'Adjunto eliminado correctamente', 'adjunto': ticket.adjunto}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al eliminar adjunto: {str(e)}'}), 500


    # Ruta para cerrar ticket
@api.route('/tickets/<int:id>/cerrar', methods=['PUT'])
@jwt_required()
def cerrar_ticket(id):
    ticket = Ticket.query.get(id)
    if not ticket:
        return jsonify({'message': 'Ticket no encontrado'}), 404

    # Verificar si el ticket está en estado "En Proceso"
    estado_en_proceso = TicketEstado.query.filter_by(nombre="En Proceso").first()
    if ticket.id_estado != estado_en_proceso.id:
        return jsonify({'message': 'El ticket solo puede cerrarse si está en estado "En Proceso"'}), 400

    estado_cerrado = TicketEstado.query.filter_by(nombre="Cerrado").first()
    if not estado_cerrado:
        return jsonify({'message': 'No se encontró el estado "Cerrado"'}), 500

    ticket.id_estado = estado_cerrado.id
    ticket.fecha_cierre = datetime.now(CHILE_TZ)

    try:
        db.session.commit()

         # Notificar cierre del ticket
        usuario = Usuario.query.get(ticket.id_usuario)
        agente = Usuario.query.get(ticket.id_agente) if ticket.id_agente else None
        notificar_cierre_ticket(ticket, usuario, agente)

        return jsonify({'message': 'Ticket cerrado correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ocurrió un error al cerrar el ticket: {str(e)}'}), 500


# Ruta para cambiar clave
@api.route('/usuarios/<user_id>/cambiar-clave', methods=['PUT'])
@jwt_required()
def cambiar_clave(user_id):
    try:
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'message': 'Usuario no encontrado'}), 404

        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        # Usar bcrypt para verificar la clave actual
        if not bcrypt.checkpw(old_password.encode('utf-8'), usuario.clave.encode('utf-8')):
            return jsonify({'message': 'Clave actual incorrecta'}), 400

        usuario.clave = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.session.commit()

        return jsonify({'message': 'Clave actualizada correctamente'}), 200
    except Exception as e:
        print(f"❌ Error en cambiar_clave: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al cambiar la clave'}), 500


@api.route('/uploads/<filename>')
def uploaded_file(filename):
    # Redirigir directamente a la URL de Cloud Storage
    file_url = storage_manager.get_file_url(filename)
    if file_url:
        return redirect(file_url, code=302)
    else:
        return jsonify({'error': 'Archivo no encontrado'}), 404


# 🔹 **Ruta para obtener agentes por departamento**
@api.route('/departamentos/<int:id_departamento>/agentes', methods=['GET'])
@jwt_required()
def get_agentes_por_departamento(id_departamento):
    try:
        print(f"🔹 Buscando agentes para el departamento ID: {id_departamento}")

        agentes = Usuario.query.join(ticket_pivot_departamento_agente).filter(
            ticket_pivot_departamento_agente.c.id_departamento == id_departamento
        ).all()

        if not agentes:
            print("❌ No hay agentes asignados a este departamento.")
            return jsonify({"error": "No hay agentes en este departamento"}), 404

        agentes_list = [{
            'id': a.id,
            'nombre': a.nombre_completo,
            'correo': a.correo
        } for a in agentes]

        print(f"Agentes encontrados: {agentes_list}")
        return jsonify(agentes_list), 200

    except Exception as e:
        print(f"❌ Error en get_agentes_por_departamento: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los agentes'}), 500


# 🔹 Ruta para obtener los estados de usuario (Activo/Inactivo)
@api.route('/usuarios/estados', methods=['GET'])
@jwt_required()
def get_estados_usuarios():
    try:
        estados = [
            {"id": 1, "nombre": "ACTIVO"},
            {"id": 2, "nombre": "INACTIVO"}
        ]
        return jsonify(estados), 200
    except Exception as e:
        print(f"🔸 Error en get_estados_usuarios: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los estados de usuario'}), 500


# 🔹 Ruta para asignar agentes a departamentos
@api.route('/agentes/<id_agente>/departamentos', methods=['PUT'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def asignar_departamentos_a_agente(id_agente):
    try:
        agente = Usuario.query.get(id_agente)
        if not agente:
            return jsonify({'message': 'Agente no encontrado'}), 404

        data = request.get_json()
        id_departamentos = data.get('id_departamentos')  # Espera una lista

        if not id_departamentos or not isinstance(id_departamentos, list):
            return jsonify({'message': 'Se requiere una lista de IDs de departamentos'}), 400

        # Asignar los departamentos al agente
        departamentos = Departamento.query.filter(Departamento.id.in_(id_departamentos)).all()
        agente.departamentos = departamentos

        db.session.commit()
        return jsonify({'message': 'Departamentos asignados correctamente al agente'}), 200

    except Exception as e:
        print(f"🔸 Error en asignar_departamentos_a_agente: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Ocurrió un error al asignar los departamentos al agente'}), 500

# Ruta para obtener agentes por departamentos
@api.route('/agentes/departamentos', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def get_agentes_departamentos():
    try:
        agentes = Usuario.query.filter(
            Usuario.id_rol == Rol.query.filter_by(nombre='Agente').first().id
        ).all()

        agentes_list = [
            {
                'id': agente.id,
                'nombre': agente.nombre_completo,
                'departamentos': [
                    {
                        'id': d.id,
                        'nombre': d.nombre
                    } for d in agente.departamentos
                ]
            } for agente in agentes
        ]

        return jsonify(agentes_list), 200

    except Exception as e:
        print(f"🔸 Error en get_agentes_departamentos: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los agentes'}), 500


# Ruta para cambiar estado ticket
@api.route('/tickets/<int:ticket_id>/estado', methods=['PUT'])
@jwt_required()
def cambiar_estado_ticket(ticket_id):
    data = request.get_json()
    nuevo_estado = data.get('estado')

    # Aceptar estados en mayúsculas
    estados_validos = ["ABIERTO", "EN PROCESO", "CERRADO"]
    if nuevo_estado not in estados_validos:
        return jsonify({"error": "Estado inválido"}), 400

    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket no encontrado"}), 404

    # Buscar el estado en la base de datos usando mayúsculas
    estado_obj = TicketEstado.query.filter(db.func.upper(TicketEstado.nombre) == nuevo_estado).first()
    if not estado_obj:
        return jsonify({"error": "Estado no encontrado en la base de datos"}), 400

    ticket.id_estado = estado_obj.id
    db.session.commit()

    return jsonify({"mensaje": "Estado actualizado correctamente"}), 200

# Ruta para crear departamentos
@api.route('/departamentos', methods=['POST'])
@jwt_required()
@role_required(['ADMINISTRADOR'])  # Solo los administradores pueden crear departamentos
def crear_departamento():
    try:
        data = request.get_json()
        nombre = data.get('nombre')

        if not nombre:
            return jsonify({'error': 'El nombre del departamento es requerido'}), 400

        # Verificar si el departamento ya existe
        departamento_existente = Departamento.query.filter_by(nombre=nombre).first()
        if departamento_existente:
            return jsonify({'error': 'El departamento ya existe'}), 400

        # Crear el nuevo departamento
        nuevo_departamento = Departamento(nombre=nombre)
        db.session.add(nuevo_departamento)
        db.session.commit()

        return jsonify({'message': 'Departamento creado exitosamente', 'id': nuevo_departamento.id}), 201

    except Exception as e:
        print(f"🔸 Error en crear_departamento: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Ocurrió un error al crear el departamento'}), 500


# Ruta para eliminar departamentos
@api.route('/departamentos/<int:id>', methods=['DELETE'])
@jwt_required()
@role_required(['ADMINISTRADOR'])  # Solo los administradores pueden eliminar departamentos
def eliminar_departamento(id):
    try:
        departamento = Departamento.query.get(id)

        if not departamento:
            return jsonify({'error': 'Departamento no encontrado'}), 404

        # Verificar si el departamento tiene tickets asociados
        tickets_asociados = Ticket.query.filter_by(id_departamento=id).count()
        if tickets_asociados > 0:
            return jsonify({'error': 'No se puede eliminar el departamento porque tiene tickets asociados'}), 400

        # Verificar si el departamento tiene agentes asignados
        agentes_asociados = db.session.query(ticket_pivot_departamento_agente).filter_by(id_departamento=id).count()
        if agentes_asociados > 0:
            return jsonify({'error': 'No se puede eliminar el departamento porque tiene agentes asignados'}), 400

        # Eliminar el departamento
        db.session.delete(departamento)
        db.session.commit()

        return jsonify({'message': 'Departamento eliminado correctamente'}), 200

    except Exception as e:
        print(f"🔸 Error en eliminar_departamento: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Ocurrió un error al eliminar el departamento'}), 500


@api.route('/departamentos/<int:id>', methods=['PUT'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def editar_departamento(id):
    departamento = Departamento.query.get(id)
    if not departamento:
        return jsonify({'error': 'Departamento no encontrado'}), 404

    data = request.get_json()
    if 'nombre' in data:
        departamento.nombre = data['nombre']

    try:
        db.session.commit()
        return jsonify({'message': 'Departamento actualizado correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar departamento: {str(e)}'}), 500


@api.route('/agentes/agrupados-por-sucursal', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def get_agentes_agrupados_por_sucursal():
    try:
        # Obtén el id del rol AGENTE
        id_rol_agente = Rol.query.filter_by(nombre='AGENTE').first().id
        agentes = Usuario.query.filter(Usuario.id_rol == id_rol_agente).all()
        agentes_por_sucursal = {}

        for agente in agentes:
            sucursal = agente.sucursal_obj.nombre if agente.sucursal_obj else "Sin sucursal"
            if sucursal not in agentes_por_sucursal:
                agentes_por_sucursal[sucursal] = []
            agentes_por_sucursal[sucursal].append({
                "id": agente.id,
                "nombre": agente.nombre_completo,
                "correo": agente.correo
            })

        resultado = [
            {"sucursal": sucursal, "agentes": lista}
            for sucursal, lista in agentes_por_sucursal.items()
        ]
        return jsonify(resultado), 200
    except Exception as e:
        print(f"🔸 Error en get_agentes_agrupados_por_sucursal: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los agentes agrupados por sucursal'}), 500


# Ruta para obtener categorías por departamento
@api.route('/categorias', methods=['GET'])
@jwt_required()
def get_categorias_por_departamento():
    try:
        departamento_id = request.args.get('departamento_id')
        if not departamento_id:
            return jsonify({'error': 'Se requiere el ID del departamento'}), 400

        categorias = Categoria.query.filter_by(id_departamento=departamento_id).all()
        return jsonify([{
            'id': c.id, 
            'nombre': c.nombre,
            'id_usuario': c.id_usuario,
            'usuario_responsable': c.usuario_responsable.nombre_completo if c.usuario_responsable else None
        } for c in categorias]), 200
    except Exception as e:
        print(f"🔸 Error en get_categorias_por_departamento: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener las categorías'}), 500

# ✅ ADMINISTRADOR: Obtener todas las categorías con usuarios asignados
@api.route('/admin/categorias', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def get_all_categorias():
    try:
        categorias = Categoria.query.all()
        return jsonify([{
            'id': c.id,
            'nombre': c.nombre,
            'id_departamento': c.id_departamento,
            'departamento': c.departamento.nombre,
            'id_usuario': c.id_usuario,
            'usuario_responsable': c.usuario_responsable.nombre_completo if c.usuario_responsable else None
        } for c in categorias]), 200
    except Exception as e:
        print(f"🔸 Error al obtener todas las categorías: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener las categorías'}), 500

# ✅ ADMINISTRADOR: Crear nueva categoría
@api.route('/admin/categorias', methods=['POST'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def crear_categoria():
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        id_departamento = data.get('id_departamento')
        id_usuario = data.get('id_usuario')  # Opcional
        
        if not nombre or not id_departamento:
            return jsonify({'error': 'Se requiere nombre y departamento'}), 400
        
        # Verificar que el departamento existe
        departamento = Departamento.query.get(id_departamento)
        if not departamento:
            return jsonify({'error': 'Departamento no encontrado'}), 404
        
        # Si se asigna un usuario, verificar que pertenece al departamento
        if id_usuario:
            usuario = Usuario.query.get(id_usuario)
            if not usuario:
                return jsonify({'error': 'Usuario no encontrado'}), 404
            
            # Verificar que el usuario pertenece al departamento
            usuario_en_departamento = db.session.query(ticket_pivot_departamento_agente).filter(
                ticket_pivot_departamento_agente.c.id_usuario == id_usuario,
                ticket_pivot_departamento_agente.c.id_departamento == id_departamento
            ).first()
            
            if not usuario_en_departamento:
                return jsonify({'error': 'El usuario debe pertenecer al departamento de la categoría'}), 400
        
        # Generar ID único para la categoría
        import uuid
        categoria_id = str(uuid.uuid4())
        
        nueva_categoria = Categoria(
            id=categoria_id,
            nombre=nombre,
            id_departamento=id_departamento,
            id_usuario=id_usuario
        )
        
        db.session.add(nueva_categoria)
        db.session.commit()
        
        return jsonify({
            'message': 'Categoría creada exitosamente',
            'categoria': {
                'id': nueva_categoria.id,
                'nombre': nueva_categoria.nombre,
                'id_departamento': nueva_categoria.id_departamento,
                'departamento': nueva_categoria.departamento.nombre,
                'id_usuario': nueva_categoria.id_usuario,
                'usuario_responsable': nueva_categoria.usuario_responsable.nombre_completo if nueva_categoria.usuario_responsable else None
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"🔸 Error al crear categoría: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al crear la categoría'}), 500

# ✅ ADMINISTRADOR: Editar categoría
@api.route('/admin/categorias/<categoria_id>', methods=['PUT'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def editar_categoria(categoria_id):
    try:
        categoria = Categoria.query.get(categoria_id)
        if not categoria:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        data = request.get_json()
        nombre = data.get('nombre')
        id_departamento = data.get('id_departamento')
        id_usuario = data.get('id_usuario')
        
        if nombre:
            categoria.nombre = nombre
        
        if id_departamento:
            # Verificar que el departamento existe
            departamento = Departamento.query.get(id_departamento)
            if not departamento:
                return jsonify({'error': 'Departamento no encontrado'}), 404
            categoria.id_departamento = id_departamento
        
        if id_usuario is not None:  # Permite asignar None para quitar usuario
            if id_usuario:
                usuario = Usuario.query.get(id_usuario)
                if not usuario:
                    return jsonify({'error': 'Usuario no encontrado'}), 404
                
                # Verificar que el usuario pertenece al departamento
                usuario_en_departamento = db.session.query(ticket_pivot_departamento_agente).filter(
                    ticket_pivot_departamento_agente.c.id_usuario == id_usuario,
                    ticket_pivot_departamento_agente.c.id_departamento == categoria.id_departamento
                ).first()
                
                if not usuario_en_departamento:
                    return jsonify({'error': 'El usuario debe pertenecer al departamento de la categoría'}), 400
            
            categoria.id_usuario = id_usuario
        
        db.session.commit()
        
        return jsonify({
            'message': 'Categoría actualizada exitosamente',
            'categoria': {
                'id': categoria.id,
                'nombre': categoria.nombre,
                'id_departamento': categoria.id_departamento,
                'departamento': categoria.departamento.nombre,
                'id_usuario': categoria.id_usuario,
                'usuario_responsable': categoria.usuario_responsable.nombre_completo if categoria.usuario_responsable else None
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"🔸 Error al editar categoría: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al editar la categoría'}), 500

# ✅ ADMINISTRADOR: Eliminar categoría
@api.route('/admin/categorias/<categoria_id>', methods=['DELETE'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def eliminar_categoria(categoria_id):
    try:
        categoria = Categoria.query.get(categoria_id)
        if not categoria:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        # Verificar si hay tickets usando esta categoría
        tickets_con_categoria = Ticket.query.filter_by(id_categoria=categoria_id).count()
        if tickets_con_categoria > 0:
            return jsonify({'error': f'No se puede eliminar la categoría porque tiene {tickets_con_categoria} ticket(s) asociado(s)'}), 400
        
        db.session.delete(categoria)
        db.session.commit()
        
        return jsonify({'message': 'Categoría eliminada exitosamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"🔸 Error al eliminar categoría: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al eliminar la categoría'}), 500

# ✅ ADMINISTRADOR: Obtener agentes disponibles para asignar a categoría
@api.route('/admin/categorias/<categoria_id>/agentes-disponibles', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def get_agentes_disponibles_para_categoria(categoria_id):
    try:
        categoria = Categoria.query.get(categoria_id)
        if not categoria:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        # Obtener el ID del rol AGENTE
        rol_agente = Rol.query.filter_by(nombre='AGENTE').first()
        if not rol_agente:
            rol_agente = Rol.query.filter_by(nombre='Agente').first()
        if not rol_agente:
            rol_agente = Rol.query.filter_by(nombre='agente').first()
        
        if not rol_agente:
            return jsonify({'error': 'Rol AGENTE no encontrado'}), 404
        
        # Obtener agentes que pertenecen al departamento de la categoría
        agentes_departamento = db.session.query(Usuario).join(
            ticket_pivot_departamento_agente,
            Usuario.id == ticket_pivot_departamento_agente.c.id_usuario
        ).join(
            Rol,
            Usuario.id_rol == Rol.id
        ).filter(
            ticket_pivot_departamento_agente.c.id_departamento == categoria.id_departamento,
            Rol.nombre == 'AGENTE'
        ).all()
        
        # Ordenar alfabéticamente
        agentes_departamento.sort(key=lambda x: x.nombre_completo.lower())
        
        return jsonify([{
            'id': agente.id,
            'nombre': agente.nombre_completo,
            'correo': agente.correo,
            'rol': agente.rol_obj.nombre
        } for agente in agentes_departamento]), 200
        
    except Exception as e:
        print(f"Error al obtener agentes disponibles para categoría: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los agentes disponibles'}), 500

# 🔹 Ruta de debug para verificar la función completa
@api.route('/debug/agentes-categoria-completo/<categoria_id>', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def debug_agentes_categoria_completo(categoria_id):
    try:
        categoria = Categoria.query.get(categoria_id)
        if not categoria:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        # Obtener el rol AGENTE
        rol_agente = Rol.query.filter_by(nombre='AGENTE').first()
        if not rol_agente:
            return jsonify({'error': 'Rol AGENTE no encontrado'}), 404
        
        # Obtener agentes del departamento
        agentes = db.session.query(Usuario).join(
            ticket_pivot_departamento_agente,
            Usuario.id == ticket_pivot_departamento_agente.c.id_usuario
        ).filter(
            Usuario.id_rol == rol_agente.id,
            ticket_pivot_departamento_agente.c.id_departamento == categoria.id_departamento
        ).all()
        
        # Crear respuesta detallada
        response_data = {
            'categoria': {
                'id': categoria.id,
                'nombre': categoria.nombre,
                'departamento_id': categoria.id_departamento,
                'departamento_nombre': categoria.departamento.nombre
            },
            'rol_agente': {
                'id': rol_agente.id,
                'nombre': rol_agente.nombre
            },
            'agentes_encontrados': len(agentes),
            'agentes': [{
                'id': agente.id,
                'nombre': agente.nombre_completo,
                'correo': agente.correo,
                'rol': agente.rol_obj.nombre
            } for agente in agentes]
        }
        
        return jsonify(response_data), 200
    except Exception as e:
        print(f"🔸 Error en debug_agentes_categoria_completo: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener la información'}), 500

# Ruta para obtener apps disponibles
@api.route('/apps', methods=['GET'])
@jwt_required()
def get_apps():
    try:
        from models import App
        apps = App.query.all()
        return jsonify([{
            'id': app.id,
            'nombre': app.nombre,
            'descripcion': app.descripcion,
            'url': app.URL
        } for app in apps]), 200
    except Exception as e:
        print(f"🔸 Error al obtener apps: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener las apps'}), 500

# Ruta para obtener apps del usuario
@api.route('/usuario/apps', methods=['GET'])
@jwt_required()
def get_usuario_apps():
    try:
        current_user_id = get_jwt_identity()
        usuario = Usuario.query.get(current_user_id)
        
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Obtener las apps a las que tiene acceso el usuario
        apps_usuario = usuario.apps
        
        return jsonify([{
            'id': app.id,
            'nombre': app.nombre,
            'descripcion': app.descripcion,
            'url': app.URL
        } for app in apps_usuario]), 200
    except Exception as e:
        print(f"🔸 Error al obtener apps del usuario: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener las apps del usuario'}), 500

# ✅ ADMINISTRADOR: Obtener todas las apps disponibles
@api.route('/admin/apps', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def get_all_apps():
    try:
        from models import App
        apps = App.query.all()
        return jsonify([{
            'id': app.id,
            'nombre': app.nombre,
            'descripcion': app.descripcion,
            'url': app.URL
        } for app in apps]), 200
    except Exception as e:
        print(f"🔸 Error al obtener todas las apps: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener las apps'}), 500

# ✅ ADMINISTRADOR: Obtener usuarios con sus apps asignadas (versión completa)
@api.route('/admin/usuarios-apps', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def get_usuarios_con_apps():
    try:
        usuarios = Usuario.query.all()
        usuarios_apps = []
        
        for usuario in usuarios:
            apps_usuario = [{
                'id': app.id, 
                'nombre': app.nombre,
                'descripcion': app.descripcion,
                'url': app.URL
            } for app in usuario.apps]
            
            # Obtener el nombre completo para ordenamiento
            nombre_usuario = usuario.nombre_completo
            
            usuarios_apps.append({
                'id': usuario.id,
                'nombre': nombre_usuario,
                'correo': usuario.correo,
                'rol': usuario.rol_obj.nombre,
                'estado': usuario.estado_obj.nombre,
                'apps': apps_usuario
            })
        
        # Ordenar alfabéticamente por nombre
        usuarios_apps.sort(key=lambda x: x['nombre'].lower())
        
        return jsonify(usuarios_apps), 200
    except Exception as e:
        print(f"🔸 Error al obtener usuarios con apps: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los usuarios con apps'}), 500

# ✅ ADMINISTRADOR: Obtener usuarios con apps (versión optimizada para frontend)
@api.route('/admin/usuarios/apps', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def get_usuarios_apps_optimizado():
    try:
        usuarios = Usuario.query.all()
        usuarios_apps = []
        
        for usuario in usuarios:
            # Solo incluir información esencial para optimizar la respuesta
            apps_usuario = [{
                'id': app.id, 
                'nombre': app.nombre
            } for app in usuario.apps]
            
            usuarios_apps.append({
                'id': usuario.id,
                'nombre': usuario.nombre_completo,
                'correo': usuario.correo,
                'rol': usuario.rol_obj.nombre,
                'estado': usuario.estado_obj.nombre,
                'apps': apps_usuario
            })
        
        # Ordenar alfabéticamente por nombre
        usuarios_apps.sort(key=lambda x: x['nombre'].lower())
        
        return jsonify(usuarios_apps), 200
    except Exception as e:
        print(f"🔸 Error al obtener usuarios con apps (optimizado): {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los usuarios con apps'}), 500

# ✅ ADMINISTRADOR: Asignar apps a un usuario
@api.route('/admin/usuarios/<user_id>/apps', methods=['PUT'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def asignar_apps_a_usuario(user_id):
    try:
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        data = request.get_json()
        app_ids = data.get('app_ids', [])
        
        if not isinstance(app_ids, list):
            return jsonify({'error': 'app_ids debe ser una lista'}), 400
        
        # Obtener las apps de la base de datos
        from models import App
        apps = App.query.filter(App.id.in_(app_ids)).all()
        
        # Limpiar asignaciones existentes
        usuario.apps = []
        db.session.commit()
        
        # Asignar las nuevas apps con IDs únicos
        for app in apps:
            # Generar ID único para cada asignación
            import uuid
            pivot_id = str(uuid.uuid4())
            
            # Insertar directamente en la tabla pivot
            db.session.execute(
                usuario_pivot_app_usuario.insert().values(
                    id=pivot_id,
                    id_usuario=usuario.id,
                    id_app=app.id
                )
            )
        
        db.session.commit()
        
        # Obtener las apps actualizadas para la respuesta
        apps_actualizadas = [{
            'id': app.id, 
            'nombre': app.nombre,
            'descripcion': app.descripcion,
            'url': app.URL
        } for app in usuario.apps]
        
        return jsonify({
            'message': 'Apps asignadas correctamente',
            'usuario': {
                'id': usuario.id,
                'nombre': usuario.nombre_completo,
                'correo': usuario.correo,
                'apps': apps_actualizadas
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"🔸 Error al asignar apps al usuario: {str(e)}")
        return jsonify({'error': f'Error al asignar apps al usuario: {str(e)}'}), 500

# ✅ ADMINISTRADOR: Obtener apps de un usuario específico
@api.route('/admin/usuarios/<user_id>/apps', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def get_apps_de_usuario(user_id):
    try:
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        apps_usuario = [{
            'id': app.id, 
            'nombre': app.nombre,
            'descripcion': app.descripcion,
            'url': app.URL
        } for app in usuario.apps]
        
        return jsonify({
            'usuario': {
                'id': usuario.id,
                'nombre': usuario.nombre_completo,
                'correo': usuario.correo,
                'rol': usuario.rol_obj.nombre
            },
            'apps': apps_usuario
        }), 200
    except Exception as e:
        print(f"🔸 Error al obtener apps del usuario: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener las apps del usuario'}), 500

# ✅ ADMINISTRADOR: Crear nueva app
@api.route('/admin/apps', methods=['POST'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def crear_app():
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        descripcion = data.get('descripcion')
        url = data.get('url')
        
        if not nombre:
            return jsonify({'error': 'El nombre de la app es requerido'}), 400
        
        # Verificar si la app ya existe
        from models import App
        app_existente = App.query.filter_by(nombre=nombre).first()
        if app_existente:
            return jsonify({'error': 'La app ya existe'}), 400
        
        # Crear la nueva app
        nueva_app = App(
            nombre=nombre,
            descripcion=descripcion,
            URL=url
        )
        db.session.add(nueva_app)
        db.session.commit()
        
        return jsonify({
            'message': 'App creada exitosamente',
            'app': {
                'id': nueva_app.id,
                'nombre': nueva_app.nombre,
                'descripcion': nueva_app.descripcion,
                'url': nueva_app.URL
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"🔸 Error al crear app: {str(e)}")
        return jsonify({'error': f'Error al crear la app: {str(e)}'}), 500

# ✅ ADMINISTRADOR: Editar app
@api.route('/admin/apps/<int:app_id>', methods=['PUT'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def editar_app(app_id):
    try:
        from models import App
        app = App.query.get(app_id)
        if not app:
            return jsonify({'error': 'App no encontrada'}), 404
        
        data = request.get_json()
        nombre = data.get('nombre')
        descripcion = data.get('descripcion')
        url = data.get('url')
        
        if nombre:
            # Verificar si el nuevo nombre ya existe en otra app
            app_existente = App.query.filter(App.nombre == nombre, App.id != app_id).first()
            if app_existente:
                return jsonify({'error': 'Ya existe una app con ese nombre'}), 400
            
            app.nombre = nombre
        
        if descripcion is not None:
            app.descripcion = descripcion
        
        if url is not None:
            app.URL = url
        
        db.session.commit()
        
        return jsonify({
            'message': 'App actualizada correctamente',
            'app': {
                'id': app.id,
                'nombre': app.nombre,
                'descripcion': app.descripcion,
                'url': app.URL
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"🔸 Error al editar app: {str(e)}")
        return jsonify({'error': f'Error al editar la app: {str(e)}'}), 500

# ✅ ADMINISTRADOR: Eliminar app
@api.route('/admin/apps/<int:app_id>', methods=['DELETE'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def eliminar_app(app_id):
    try:
        from models import App
        app = App.query.get(app_id)
        if not app:
            return jsonify({'error': 'App no encontrada'}), 404
        
        # Verificar si la app tiene usuarios asignados
        if app.usuarios:
            return jsonify({'error': 'No se puede eliminar la app porque tiene usuarios asignados'}), 400
        
        db.session.delete(app)
        db.session.commit()
        
        return jsonify({'message': 'App eliminada correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"🔸 Error al eliminar app: {str(e)}")
        return jsonify({'error': f'Error al eliminar la app: {str(e)}'}), 500

@api.route('/tickets/mi-departamento', methods=['GET'])
@jwt_required()
@role_required(['AGENTE'])
@app_required(1)
def get_tickets_mi_departamento():
    """Endpoint para agentes: ver tickets de su departamento asignado"""
    try:
        current_user_id = get_jwt_identity()
        usuario = Usuario.query.get(current_user_id)

        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Obtener los departamentos asignados al agente
        departamentos_ids = [d.id for d in usuario.departamentos]
        
        # Agentes ven tickets de sus departamentos asignados
        tickets = Ticket.query.filter(
            Ticket.id_departamento.in_(departamentos_ids)
        ).order_by(Ticket.fecha_creacion.desc()).all()

        ticket_list = []
        for ticket in tickets:
            sucursal_obj = Sucursal.query.get(ticket.id_sucursal)
            nombre_sucursal = sucursal_obj.nombre if sucursal_obj else "No asignada"
            ticket_list.append({
                "id": ticket.id,
                "titulo": ticket.titulo,
                "descripcion": ticket.descripcion,
                "id_usuario": ticket.id_usuario,
                "id_agente": ticket.id_agente,
                "usuario": (
                    ticket.usuario.nombre_completo
                    if ticket.usuario else "Sin usuario"
                ),
                "agente": (
                    ticket.agente.nombre_completo
                    if ticket.agente else "Sin asignar"
                ),
                "estado": ticket.estado.nombre,
                "prioridad": ticket.prioridad.nombre,
                "departamento": ticket.departamento.nombre if ticket.departamento else None,
                "id_departamento": ticket.id_departamento,
                "id_categoria": ticket.id_categoria,
                "categoria": ticket.categoria.nombre if ticket.categoria else None,
                "sucursal": nombre_sucursal,
                "fecha_creacion": ticket.fecha_creacion.astimezone(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_creacion else None,
                "fecha_cierre": ticket.fecha_cierre.astimezone(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_cierre else None,
                "adjunto": ticket.adjunto,
                "id_prioridad": ticket.id_prioridad,
                "id_estado": ticket.id_estado
            })

        return jsonify(ticket_list), 200

    except Exception as e:
        print(f"🔸 Error en get_tickets_mi_departamento: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los tickets de mi departamento'}), 500

@api.route('/tickets/mis-tickets', methods=['GET'])
@jwt_required()
@role_required(['AGENTE'])
@app_required(1)
def get_mis_tickets():
    """Endpoint para agentes: ver tickets que ELLOS crearon (independiente del departamento)"""
    try:
        current_user_id = get_jwt_identity()
        usuario = Usuario.query.get(current_user_id)

        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Agentes ven SOLO los tickets que ELLOS crearon
        tickets = Ticket.query.filter_by(id_usuario=current_user_id).order_by(Ticket.fecha_creacion.desc()).all()

        ticket_list = []
        for ticket in tickets:
            sucursal_obj = Sucursal.query.get(ticket.id_sucursal)
            nombre_sucursal = sucursal_obj.nombre if sucursal_obj else "No asignada"
            ticket_list.append({
                "id": ticket.id,
                "titulo": ticket.titulo,
                "descripcion": ticket.descripcion,
                "id_usuario": ticket.id_usuario,
                "id_agente": ticket.id_agente,
                "usuario": (
                    ticket.usuario.nombre_completo
                    if ticket.usuario else "Sin usuario"
                ),
                "agente": (
                    ticket.agente.nombre_completo
                    if ticket.agente else "Sin asignar"
                ),
                "estado": ticket.estado.nombre,
                "prioridad": ticket.prioridad.nombre,
                "departamento": ticket.departamento.nombre if ticket.departamento else None,
                "id_departamento": ticket.id_departamento,
                "id_categoria": ticket.id_categoria,
                "categoria": ticket.categoria.nombre if ticket.categoria else None,
                "sucursal": nombre_sucursal,
                "fecha_creacion": ticket.fecha_creacion.astimezone(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_creacion else None,
                "fecha_cierre": ticket.fecha_cierre.astimezone(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_cierre else None,
                "adjunto": ticket.adjunto,
                "id_prioridad": ticket.id_prioridad,
                "id_estado": ticket.id_estado
            })

        return jsonify(ticket_list), 200

    except Exception as e:
        print(f"🔸 Error en get_mis_tickets: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener mis tickets'}), 500
