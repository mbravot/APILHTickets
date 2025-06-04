import os
import time
import uuid
from flask import Blueprint, request, jsonify
from models import Rol, db, Ticket, Usuario, TicketEstado, TicketPrioridad, Departamento, TicketComentario, Sucursal, ticket_pivot_departamento_agente, Colaborador, Categoria
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
import bcrypt
import hashlib
from datetime import datetime


api = Blueprint('api', __name__)
auth = Blueprint('auth', __name__)

# Cargar variables de entorno desde el archivo .env
load_dotenv()

CHILE_TZ = pytz.timezone('America/Santiago')

# Función de notificación por correo
def notificar_creacion_ticket(ticket, usuario, agente):
    try:
        agente_nombre = agente.colaborador_obj.nombre if agente and agente.colaborador_obj else agente.correo if agente else "Sin asignar"
        usuario_nombre = usuario.colaborador_obj.nombre if usuario.colaborador_obj else usuario.correo
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
        agente_nombre = agente.colaborador_obj.nombre if agente and agente.colaborador_obj else agente.correo if agente else "Sin asignar"
        usuario_nombre = usuario.colaborador_obj.nombre if usuario.colaborador_obj else usuario.correo
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
        agente_nombre = agente.colaborador_obj.nombre if agente and agente.colaborador_obj else agente.correo if agente else "Sin asignar"
        usuario_nombre = usuario.colaborador_obj.nombre if usuario.colaborador_obj else usuario.correo
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
        agente_nombre = agente.colaborador_obj.nombre if agente and agente.colaborador_obj else agente.correo if agente else "Sin asignar"
        usuario_nombre = usuario.colaborador_obj.nombre if usuario.colaborador_obj else usuario.correo
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
        agente_anterior_nombre = agente_anterior.colaborador_obj.nombre if agente_anterior and agente_anterior.colaborador_obj else agente_anterior.correo if agente_anterior else "Ninguno"
        agente_nuevo_nombre = agente_nuevo.colaborador_obj.nombre if agente_nuevo.colaborador_obj else agente_nuevo.correo
        usuario_nombre = usuario.colaborador_obj.nombre if usuario.colaborador_obj else usuario.correo
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
            if usuario:
                print("Rol del usuario autenticado:", usuario.rol_obj.nombre)
            print("Roles permitidos:", roles_permitidos)
            if not usuario or usuario.rol_obj.nombre not in roles_permitidos:
                return jsonify({'message': 'Acceso denegado'}), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Ruta para obtener tickets
@api.route('/tickets', methods=['GET'])
@jwt_required()
def get_tickets():
    print("🔹 Recibida petición: GET /api/tickets")

    try:
        current_user_id = get_jwt_identity()
        usuario = Usuario.query.get(current_user_id)

        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404

        print(f"🔹 Usuario autenticado: {usuario.usuario} ({usuario.rol_obj.nombre})")

        # Obtener tickets según el rol del usuario
        if usuario.rol_obj.nombre == "ADMINISTRADOR":
            # Administradores ven todos los tickets
            tickets = Ticket.query.order_by(Ticket.fecha_creacion.desc()).all()
        elif usuario.rol_obj.nombre == "AGENTE":
            # Obtener los departamentos asignados al agente
            departamentos_ids = [d.id for d in usuario.departamentos]
            print(f"Departamentos del agente: {departamentos_ids}")
            
            # Agentes ven tickets de sus departamentos asignados
            tickets = Ticket.query.filter(
                Ticket.id_departamento.in_(departamentos_ids)
            ).order_by(Ticket.fecha_creacion.desc()).all()
            
            print(f"Tickets encontrados para el agente: {len(tickets)}")
        else:  # Usuario normal
            # Usuarios normales ven sus propios tickets
            tickets = Ticket.query.filter_by(id_usuario=current_user_id).order_by(Ticket.fecha_creacion.desc()).all()

        ticket_list = []
        for ticket in tickets:
            # DEBUG: Log para depuración de sucursal
            print(f"Ticket ID: {ticket.id} | id_sucursal: {ticket.id_sucursal}")
            sucursal_obj = Sucursal.query.get(ticket.id_sucursal)
            print(f"Sucursal encontrada: {sucursal_obj}")
            nombre_sucursal = sucursal_obj.nombre if sucursal_obj else "No asignada"
            ticket_list.append({
                "id": ticket.id,
                "titulo": ticket.titulo,
                "descripcion": ticket.descripcion,
                "id_usuario": ticket.id_usuario,
                "id_agente": ticket.id_agente,
                "usuario": (
                    ticket.usuario.colaborador_obj.nombre
                    if ticket.usuario and ticket.usuario.colaborador_obj
                    else ticket.usuario.usuario if ticket.usuario else "Sin usuario"
                ),
                "agente": (
                    ticket.agente.colaborador_obj.nombre
                    if ticket.agente and ticket.agente.colaborador_obj
                    else ticket.agente.usuario if ticket.agente else "Sin asignar"
                ),
                "estado": ticket.estado.nombre,
                "prioridad": ticket.prioridad.nombre,
                "departamento": ticket.departamento.nombre if ticket.departamento else None,
                "id_departamento": ticket.id_departamento,
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
                Usuario.query.get(c.id_usuario).colaborador_obj.nombre
                if Usuario.query.get(c.id_usuario) and Usuario.query.get(c.id_usuario).colaborador_obj
                else Usuario.query.get(c.id_usuario).usuario if Usuario.query.get(c.id_usuario) else None
            ),
            'comentario': c.comentario,
            'creado': c.timestamp.strftime('%Y-%m-%d %H:%M:%S') if c.timestamp else None
        }
        for c in comentarios
    ]

    # DEBUG: Log para depuración de sucursal en detalle
    print(f"Ticket ID: {ticket.id} | id_sucursal: {ticket.id_sucursal}")
    sucursal_obj = Sucursal.query.get(ticket.id_sucursal)
    print(f"Sucursal encontrada: {sucursal_obj}")
    nombre_sucursal = sucursal_obj.nombre if sucursal_obj else "No asignada"
    ticket_data = {
        "id": ticket.id,
        "titulo": ticket.titulo,
        "descripcion": ticket.descripcion,
        "id_usuario": ticket.id_usuario,
        "id_agente": ticket.id_agente,
        "usuario": (
            ticket.usuario.colaborador_obj.nombre
            if ticket.usuario and ticket.usuario.colaborador_obj
            else ticket.usuario.usuario if ticket.usuario else None
        ),
        "agente": (
            ticket.agente.colaborador_obj.nombre
            if ticket.agente and ticket.agente.colaborador_obj
            else ticket.agente.usuario if ticket.agente else None
        ),
        "estado": ticket.estado.nombre if ticket.estado else None,
        "prioridad": ticket.prioridad.nombre if ticket.prioridad else None,
        "departamento": ticket.departamento.nombre if ticket.departamento else None,
        "id_departamento": ticket.id_departamento,
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

        # ✅ Obtener agentes del departamento
        agentes = Usuario.query.join(ticket_pivot_departamento_agente).filter(
            ticket_pivot_departamento_agente.c.id_departamento == id_departamento
        ).all()

        # ✅ Asignar un agente aleatorio si hay disponibles
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
        print(f"🔸 Error en create_ticket: {str(e)}")
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
        print("Datos recibidos para registro:", data)  # Log para debug
        
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
            print(f"Sucursal activa {data['id_sucursalactiva']} agregada a sucursales autorizadas")

        # Crear nuevo usuario con la nueva estructura
        nuevo_usuario = Usuario(
            id=user_id,
            id_colaborador=data.get('id_colaborador'),  # Opcional
            id_sucursalactiva=data['id_sucursalactiva'],
            usuario=data['usuario'],
            clave=hashed_password,
            fecha_creacion=datetime.now().date(),
            id_estado=1,  # Activo por defecto
            correo=data['correo'],
            id_rol=data['id_rol']
        )
            
        # Agregar sucursales autorizadas (incluyendo la sucursal activa)
        sucursales = Sucursal.query.filter(Sucursal.id.in_(sucursales_autorizadas)).all()
        nuevo_usuario.sucursales_autorizadas = sucursales
        print(f"Sucursales autorizadas asignadas: {[s.id for s in sucursales]}")

        db.session.add(nuevo_usuario)
        db.session.commit()

        # Obtener el usuario creado para la respuesta
        usuario_creado = Usuario.query.get(user_id)
        return jsonify({
            'message': 'Usuario registrado exitosamente',
            'usuario': {
                'id': usuario_creado.id,
                'nombre': usuario_creado.colaborador_obj.nombre if usuario_creado.colaborador_obj else usuario_creado.usuario,
                'correo': usuario_creado.correo,
                'rol': usuario_creado.rol_obj.nombre,
                'sucursal_activa': {
                    'id': usuario_creado.sucursal_obj.id,
                    'nombre': usuario_creado.sucursal_obj.nombre
                },
                'sucursales_autorizadas': [
                    {
                        'id': sucursal.id,
                        'nombre': sucursal.nombre
                    } for sucursal in usuario_creado.sucursales_autorizadas
                ],
                'estado': usuario_creado.estado_obj.nombre
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
        print("Correo recibido:", data.get('correo'))
        usuario = Usuario.query.filter_by(correo=data.get('correo')).first()
        print("Usuario encontrado:", usuario)
        if usuario:
            print("Hash en BD:", usuario.clave)
            print("Comparación bcrypt:", bcrypt.checkpw(data['clave'].encode('utf-8'), usuario.clave.encode('utf-8')))
        if not usuario or not bcrypt.checkpw(data['clave'].encode('utf-8'), usuario.clave.encode('utf-8')):
            return jsonify({'message': 'Credenciales inválidas'}), 401
        
        # Acceder a rol_obj para obtener el rol del usuario
        rol = usuario.rol_obj.nombre  # Aquí se accede al nombre del rol

        # Obtener información de la sucursal activa
        sucursal_activa = Sucursal.query.get(usuario.id_sucursalactiva)
        print("Sucursal activa encontrada:", sucursal_activa)
        print("ID Sucursal:", usuario.id_sucursalactiva)
        print("Nombre Sucursal:", sucursal_activa.nombre if sucursal_activa else None)

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
                'nombre': usuario.colaborador_obj.nombre if usuario.colaborador_obj else usuario.usuario,
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
        print("Respuesta de login:", response_data)
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
    print(f"🔹 Petición para obtener comentarios del ticket ID {ticket_id}")
    try:
        comentarios = TicketComentario.query.filter_by(id_ticket=ticket_id).all()
        comentarios_list = [
            {
                'id': c.id,
                'id_ticket': c.id_ticket,
                'id_usuario': c.id_usuario,
                'usuario': (
                    Usuario.query.get(c.id_usuario).colaborador_obj.nombre
                    if Usuario.query.get(c.id_usuario) and Usuario.query.get(c.id_usuario).colaborador_obj
                    else Usuario.query.get(c.id_usuario).usuario if Usuario.query.get(c.id_usuario) else None
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
    print(f"🔹 Petición para agregar comentario al ticket ID {ticket_id}")
    try:
        data = request.get_json()
        print("Datos recibidos para comentario:", data)
        print("ID recibido para comentario:", ticket_id)
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
        nuevo_agente_id = data.get('id_agente')
        nuevo_agente = Usuario.query.get(nuevo_agente_id)

        if not nuevo_agente or nuevo_agente.rol_obj.nombre != 'AGENTE':
            return jsonify({'message': 'El usuario seleccionado no es un Agente'}), 400

        # Guardar el agente anterior antes de reasignar
        agente_anterior = Usuario.query.get(ticket.id_agente) if ticket.id_agente else None

        # 🔹 Si es Administrador, puede reasignar a cualquier agente
        if usuario_actual.rol_obj.nombre == "ADMINISTRADOR":
            ticket.id_agente = nuevo_agente_id

        # 🔹 Si es Agente, solo puede reasignar a agentes de su departamento
        elif usuario_actual.rol_obj.nombre == "AGENTE":
            # Obtener los agentes del departamento del ticket
            agentes_departamento = Usuario.query.join(ticket_pivot_departamento_agente).filter(
                ticket_pivot_departamento_agente.c.id_departamento == ticket.id_departamento
            ).all()

            agentes_permitidos = [str(agente.id) for agente in agentes_departamento]

            if str(nuevo_agente_id) not in agentes_permitidos:
                return jsonify({'message': 'No puedes reasignar fuera de tu departamento'}), 403

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
        print(f"🔸 Error en assign_ticket: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al reasignar el ticket'}), 500


# Ruta para obtener un agente (solo Administradores)
@api.route('/agentes', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def get_agentes():
    try:
        agentes = Usuario.query.filter(Usuario.id_rol == Rol.query.filter_by(nombre='Agente').first().id).all()
        return jsonify([
            {
                'id': a.id,
                'nombre': a.colaborador_obj.nombre if a.colaborador_obj else a.usuario
            }
            for a in agentes
        ]), 200
    except Exception as e:
        print(f"🔸 Error en get_agentes: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener la lista de agentes'}), 500


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

        for usuario in usuarios:
            print(f"Usuario: {usuario.usuario} | ID: {usuario.id} | Departamentos: {[d.id for d in usuario.departamentos]}")
        usuario_list = [{
            "id": usuario.id,
            "nombre": usuario.colaborador_obj.nombre if usuario.colaborador_obj else usuario.usuario,
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

        return jsonify(usuario_list), 200

    except Exception as e:
        print(f"🔸 Error en get_usuarios: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los usuarios'}), 500

# Ruta para actualizar usuarios 
@api.route('/usuarios/<user_id>', methods=['PUT'])
@jwt_required()
def update_usuario(user_id):
    current_user_id = get_jwt_identity()
    usuario = Usuario.query.get(user_id)
    if not usuario:
        return jsonify({'message': 'Usuario no encontrado'}), 404

    # Solo permitir que un usuario edite su propio perfil o que un ADMINISTRADOR edite a cualquiera
    current_user = Usuario.query.get(current_user_id)
    if current_user.id != user_id and current_user.rol_obj.nombre != 'ADMINISTRADOR':
        return jsonify({'message': 'No tienes permiso para editar este usuario'}), 403

    data = request.get_json()
    print("Datos recibidos para actualización:", data)  # Log para debug

    # Actualizar campos básicos
    if 'nombre' in data:
        usuario.nombre = data['nombre']
    if 'correo' in data:
        usuario.correo = data['correo']
    if 'clave' in data and data['clave']:
        usuario.clave = bcrypt.hashpw(data['clave'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    if 'id_rol' in data:
        usuario.id_rol = data['id_rol']
    if 'id_estado' in data:
        usuario.id_estado = data['id_estado']
    if 'id_colaborador' in data:
        usuario.id_colaborador = data['id_colaborador']

    # Actualizar sucursal activa
    if 'id_sucursalactiva' in data:
        # Verificar que la sucursal activa esté en las sucursales autorizadas
        if 'sucursales_autorizadas' in data and data['id_sucursalactiva'] not in data['sucursales_autorizadas']:
            return jsonify({'error': 'La sucursal activa debe estar en las sucursales autorizadas'}), 400
        usuario.id_sucursalactiva = data['id_sucursalactiva']

    # Actualizar sucursales autorizadas
    if 'sucursales_autorizadas' in data:
        print("Actualizando sucursales autorizadas:", data['sucursales_autorizadas'])  # Log para debug
        # Obtener las sucursales de la base de datos
        sucursales = Sucursal.query.filter(Sucursal.id.in_(data['sucursales_autorizadas'])).all()
        # Actualizar la relación
        usuario.sucursales_autorizadas = sucursales
        print("Sucursales autorizadas actualizadas:", [s.id for s in usuario.sucursales_autorizadas])  # Log para debug

    try:
        db.session.commit()
        # Obtener el usuario actualizado para la respuesta
        usuario_actualizado = Usuario.query.get(user_id)
        return jsonify({
            'message': 'Usuario actualizado correctamente',
            'usuario': {
                'id': usuario_actualizado.id,
                'nombre': usuario_actualizado.colaborador_obj.nombre if usuario_actualizado.colaborador_obj else usuario_actualizado.usuario,
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
        print(f"Error al guardar cambios: {str(e)}")  # Log para debug
        return jsonify({'error': f'Error al actualizar usuario: {str(e)}'}), 500

# ruta para eliminar un usurio
@api.route('/usuarios/<user_id>', methods=['DELETE'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def delete_usuario(user_id):
    print(f"Intentando eliminar usuario: {user_id}")
    usuario = Usuario.query.get(user_id)
    if not usuario:
        print("Usuario no encontrado")
        return jsonify({'message': 'Usuario no encontrado'}), 404
    try:
        # Verificar si el usuario tiene tickets asociados
        tickets_asociados = Ticket.query.filter_by(id_usuario=user_id).count()
        if tickets_asociados > 0:
            print("No se puede eliminar el usuario porque tiene tickets asociados")
            return jsonify({'error': 'No se puede eliminar el usuario porque tiene tickets asociados'}), 400
        db.session.delete(usuario)
        db.session.commit()
        print("Usuario eliminado correctamente")
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
    print(f"🔹 Recibida petición: POST /api/tickets/{id}/upload")

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

    # Asegurar que la carpeta uploads existe
    upload_folder = 'uploads'
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Obtener la lista actual de archivos adjuntos
    archivos_actuales = ticket.adjunto.split(',') if ticket.adjunto else []

    # Calcular el hash MD5 del archivo subido
    file_content = file.read()
    file_hash = hashlib.md5(file_content).hexdigest()
    file.seek(0)  # Volver al inicio para guardar después

    # Revisar si ya existe un archivo con el mismo hash
    hashes_existentes = set()
    for nombre_archivo in archivos_actuales:
        ruta_archivo = os.path.join(upload_folder, nombre_archivo)
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, 'rb') as f:
                hash_existente = hashlib.md5(f.read()).hexdigest()
                hashes_existentes.add(hash_existente)
    if file_hash in hashes_existentes:
        return jsonify({'message': 'Archivo duplicado, ya existe en el ticket', 'adjunto': ticket.adjunto}), 200

    # Generar un nombre único usando id y UUID
    file_ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
    unique_filename = f"t{id}_{uuid.uuid4().hex}.{file_ext}"
    file_path = os.path.join(upload_folder, unique_filename)

    # Guardar el archivo en el servidor
    file.save(file_path)

    # Guardar el nombre del archivo en la base de datos
    try:
        archivos_actuales.append(unique_filename)
        ticket.adjunto = ','.join(archivos_actuales)
        db.session.commit()
        print(f"✅ Archivo {unique_filename} guardado en la BD para el ticket {id}")
        return jsonify({'message': 'Archivo subido correctamente', 'adjunto': ticket.adjunto}), 200
    except Exception as e:
        db.session.rollback()
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

    # Eliminar el archivo físico
    upload_folder = 'uploads'
    file_path = os.path.join(upload_folder, nombre_adjunto)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Quitar el adjunto de la lista y actualizar la base de datos
    archivos_actuales.remove(nombre_adjunto)
    ticket.adjunto = ','.join(archivos_actuales)
    try:
        db.session.commit()
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


UPLOAD_FOLDER = 'uploads'

@api.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


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
            'nombre': (
                a.colaborador_obj.nombre if a.colaborador_obj else a.usuario
            )
        } for a in agentes]

        print(f"✅ Agentes encontrados: {agentes_list}")
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
                "id": agente.id,
                "nombre": agente.colaborador_obj.nombre if agente.colaborador_obj else agente.usuario,
                "departamentos": [d.nombre for d in agente.departamentos]
            }
            for agente in agentes
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
                "nombre": agente.colaborador_obj.nombre if agente.colaborador_obj else agente.usuario,
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


@api.route('/colaboradores', methods=['GET'])
@jwt_required()
@role_required(['ADMINISTRADOR'])
def get_colaboradores():
    try:
        colaboradores = Colaborador.query.all()
        lista = [{
            "id": c.id,
            "nombre_completo": f"{c.nombre} {c.apellido_paterno} {(c.apellido_materno or '').strip()}".strip()
        } for c in colaboradores]
        return jsonify(lista), 200
    except Exception as e:
        print(f"Error al obtener colaboradores: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los colaboradores'}), 500

# Ruta para obtener categorías por departamento
@api.route('/categorias', methods=['GET'])
@jwt_required()
def get_categorias_por_departamento():
    try:
        departamento_id = request.args.get('departamento_id')
        if not departamento_id:
            return jsonify({'error': 'Se requiere el ID del departamento'}), 400

        categorias = Categoria.query.filter_by(id_departamento=departamento_id).all()
        return jsonify([{'id': c.id, 'nombre': c.nombre} for c in categorias]), 200
    except Exception as e:
        print(f"🔸 Error en get_categorias_por_departamento: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener las categorías'}), 500




 