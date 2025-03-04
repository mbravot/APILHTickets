import os
import time
from flask import Blueprint, request, jsonify
from models import Rol, db, Ticket, Usuario, TicketEstado, TicketPrioridad, Departamento, TicketComentario, Sucursal, agente_departamento
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
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
from utils import enviar_correo_async


api = Blueprint('api', __name__)
auth = Blueprint('auth', __name__)

# Cargar variables de entorno desde el archivo .env
load_dotenv()

CHILE_TZ = pytz.timezone('America/Santiago')

# Función de notificación por correo
def notificar_creacion_ticket(ticket, usuario, agente):
    asunto = "Nuevo Ticket Creado"
    cuerpo = f"""
    <h1>Nuevo Ticket Creado</h1>
    <p>Se ha creado un nuevo ticket con los siguientes detalles:</p>
    <ul>
        <li><strong>ID:</strong> {ticket.id}</li>
        <li><strong>Título:</strong> {ticket.titulo}</li>
        <li><strong>Descripción:</strong> {ticket.descripcion}</li>
    </ul>
    <p>Por favor, revisa el sistema para más detalles.</p>
    """
    enviar_correo_async(usuario.correo, asunto, cuerpo)  # Acceder al atributo correo con notación de punto
    if agente:
        enviar_correo_async(agente.correo, asunto, cuerpo)  # Acceder al atributo correo con notación de punto

def notificar_cambio_estado(ticket, usuario, agente, nuevo_estado):
    asunto = f"Ticket {ticket.id} Cambió de Estado"
    cuerpo = f"""
    <h1>Cambio de Estado del Ticket</h1>
    <p>El ticket con ID {ticket.id} ha cambiado su estado a <strong>{nuevo_estado}</strong>.</p>
    <p>Por favor, revisa el sistema para más detalles.</p>
    """
    enviar_correo_async(usuario.correo, asunto, cuerpo)  # Acceder al atributo correo con notación de punto
    if agente:
        enviar_correo_async(agente.correo, asunto, cuerpo)  # Acceder al atributo correo con notación de punto

def notificar_cierre_ticket(ticket, usuario, agente):
    asunto = f"Ticket {ticket.id} Cerrado"
    cuerpo = f"""
    <h1>Ticket Cerrado</h1>
    <p>El ticket con ID {ticket.id} ha sido cerrado.</p>
    <p>Por favor, revisa el sistema para más detalles.</p>
    """
    enviar_correo_async(usuario.correo, asunto, cuerpo)  # Acceder al atributo correo con notación de punto
    if agente:
        enviar_correo_async(agente.correo, asunto, cuerpo)  # Acceder al atributo correo con notación de punto

def notificar_comentario(ticket, usuario, agente, comentario):
    asunto = f"Nuevo Comentario en el Ticket {ticket.id}"
    cuerpo = f"""
    <h1>Nuevo Comentario</h1>
    <p>Se ha agregado un nuevo comentario al ticket con ID {ticket.id}:</p>
    <blockquote>{comentario}</blockquote>
    <p>Por favor, revisa el sistema para más detalles.</p>
    """
    enviar_correo_async(usuario.correo, asunto, cuerpo)  # Acceder al atributo correo con notación de punto
    if agente:
        enviar_correo_async(agente.correo, asunto, cuerpo)  # Acceder al atributo correo con notación de punto


def notificar_reasignacion_ticket(ticket, usuario, agente_anterior, agente_nuevo):
    asunto = f"Ticket {ticket.id} Reasignado"
    cuerpo = f"""
    <h1>Ticket Reasignado</h1>
    <p>El ticket con ID {ticket.id} ha sido reasignado.</p>
    <ul>
        <li><strong>Título:</strong> {ticket.titulo}</li>
        <li><strong>Descripción:</strong> {ticket.descripcion}</li>
        <li><strong>Agente Anterior:</strong> {agente_anterior.nombre if agente_anterior else 'Ninguno'}</li>
        <li><strong>Agente Nuevo:</strong> {agente_nuevo.nombre}</li>
    </ul>
    <p>Por favor, revisa el sistema para más detalles.</p>
    """
    # Notificar al usuario que creó el ticket
    enviar_correo_async(usuario.correo, asunto, cuerpo)

    # Notificar al agente anterior (si existe)
    if agente_anterior:
        enviar_correo_async(agente_anterior.correo, asunto, cuerpo)

    # Notificar al nuevo agente
    enviar_correo_async(agente_nuevo.correo, asunto, cuerpo)


# 🔹 Decorador para proteger rutas según el rol  
def role_required(roles_permitidos):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                current_user_id = get_jwt_identity()  # Obtiene el usuario actual desde JWT
                usuario = Usuario.query.get(current_user_id)
                if not usuario or usuario.rol_obj.rol not in roles_permitidos:
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

            if not usuario or usuario.rol_obj.rol not in roles_permitidos:
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

        print(f"🔹 Usuario autenticado: {usuario.nombre} ({usuario.rol_obj.rol})")

        if usuario.rol_obj.rol == "Administrador":
            tickets = Ticket.query.order_by(Ticket.creado.desc()).all()
        elif usuario.rol_obj.rol == "Agente":
            tickets = Ticket.query.filter(
                (Ticket.id_usuario == current_user_id) |
                (Ticket.id_agente == current_user_id)
            ).order_by(Ticket.creado.desc()).all()
        else:  # Usuario normal
            tickets = Ticket.query.filter_by(id_usuario=current_user_id).order_by(Ticket.creado.desc()).all()

        # ✅ Ahora agregamos el campo `adjunto`
        ticket_list = [{
            "id": ticket.id,
            "titulo": ticket.titulo,
            "descripcion": ticket.descripcion,
            "id_usuario": ticket.id_usuario,
            "id_agente": ticket.id_agente,
            "usuario": ticket.usuario.nombre,
            "agente": ticket.agente.nombre if ticket.agente else "Sin asignar",
            "estado": ticket.estado.nombre,
            "prioridad": ticket.prioridad.nombre,
            "departamento": ticket.departamento.nombre,
            "id_departamento": ticket.id_departamento,  # ✅ 🔹 Agrega esta línea
            "creado": ticket.creado.astimezone(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            "adjunto": ticket.adjunto  # ✅ Incluir el adjunto en la respuesta
        } for ticket in tickets]

        return jsonify(ticket_list), 200

    except Exception as e:
        print(f"🔸 Error en get_tickets: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los tickets'}), 500



# Ruta para crear un nuevo ticket
@api.route('/tickets', methods=['POST'])
@jwt_required()
@permiso_requerido(['Administrador', 'Agente', 'Usuario'])
def create_ticket():
    try:
        data = request.get_json()
        current_user_id = int(get_jwt_identity())
        id_departamento = data.get('id_departamento')

        if not id_departamento:
            return jsonify({'error': 'Debe seleccionar un departamento'}), 400

         # ✅ Obtener agentes del departamento (ya corregido)
        agentes = Usuario.query.join(agente_departamento).filter(
            agente_departamento.c.id_departamento == id_departamento
        ).all()

         # ✅ Asignar un agente aleatorio si hay disponibles
        id_agente = random.choice(agentes).id if agentes else None

          # Obtener el estado "Abierto" y prioridad "Baja" si no se especifican
        estado_abierto = TicketEstado.query.filter_by(nombre="Abierto").first()
        prioridad_baja = TicketPrioridad.query.filter_by(nombre="Baja").first()

        nuevo_ticket = Ticket(
            id_usuario=current_user_id,
            id_agente=id_agente,  # Se asigna automáticamente un agente del departamento
            id_estado=data.get('id_estado', estado_abierto.id if estado_abierto else None),  # Estado por defecto "Abierto"
            id_prioridad=data.get('id_prioridad', prioridad_baja.id if prioridad_baja else None),  # Prioridad por defecto "Baja"
            id_departamento=data.get('id_departamento'),
            titulo=data.get('titulo'),
            descripcion=data.get('descripcion')
        )

        db.session.add(nuevo_ticket)
        db.session.commit()

           # Notificar creación del ticket
        usuario = Usuario.query.get(current_user_id)
        agente = Usuario.query.get(id_agente) if id_agente else None
        notificar_creacion_ticket(nuevo_ticket, usuario, agente)  # Pasar los objetos directamente


        return jsonify({'message': 'Ticket creado exitosamente', 'ticket_id': nuevo_ticket.id}), 201

    except Exception as e:
        print(f"🔸 Error en create_ticket: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al crear el ticket'}), 500

# Extensiones permitidas
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'xlsx'}

# Función para verificar si el archivo tiene una extensión válida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ruta para actualizar un ticket y adjuntar un archivo
@api.route('/tickets/<int:id>', methods=['PUT'])
@jwt_required()
def update_ticket(id):
    current_user_id = get_jwt_identity()
    usuario = Usuario.query.get(current_user_id)
    ticket = Ticket.query.get(id)

    if not ticket:
        return jsonify({'message': 'Ticket no encontrado'}), 404

    if usuario.rol_obj.rol != 'Administrador' and ticket.id_usuario != usuario.id:
        return jsonify({'message': 'No tienes permiso para editar este ticket'}), 403

    # Verificar si hay datos JSON para actualizar el título y la descripción
    if request.is_json:
        data = request.get_json()
        ticket.titulo = data.get('titulo', ticket.titulo)
        ticket.descripcion = data.get('descripcion', ticket.descripcion)

    # Manejo de archivo adjunto
    if 'file' in request.files:
        file = request.files['file']

        if file.filename == '':
            return jsonify({'message': 'Nombre de archivo inválido'}), 400

        if not allowed_file(file.filename):
            return jsonify({'message': 'Tipo de archivo no permitido'}), 400

        # Asegurar que la carpeta uploads existe
        upload_folder = 'uploads'
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # Generar un nombre único para el archivo (evita sobrescribir archivos existentes)
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{id}_{current_user_id}_{int(time.time())}.{file_ext}"
        file_path = os.path.join(upload_folder, unique_filename)
        
        # Guardar archivo en el servidor
        file.save(file_path)

        # 🔹 Guardar solo el nombre del archivo en la base de datos
        ticket.adjunto = unique_filename

    try:
        db.session.commit()

        # Notificar cambio de estado si se actualizó el estado
        if 'id_estado' in data:
            nuevo_estado = TicketEstado.query.get(data['id_estado']).nombre
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

    if usuario.rol_obj.rol != 'Administrador' and ticket.id_usuario != usuario.id:
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
@jwt_required()  # 🔹 Primero verificamos si hay un JWT válido
@role_required(['Administrador'])  # Solo los administradores pueden registrar usuarios
def register():
    try:
        data = request.get_json()

        # Verificar si el usuario ya existe
        existing_user = Usuario.query.filter_by(correo=data['correo']).first()
        if existing_user:
            return jsonify({'message': 'El usuario ya existe'}), 400
        
        # Verificar si el rol y la sucursal existen
        #rol = Rol.query.get(data['id_rol'])
        #sucursal = Sucursal.query.get(data['id_sucursal'])

        #if not rol:
          #  return jsonify({'message': 'Rol no válido'}), 400
        #if not sucursal:
            #return jsonify({'message': 'Sucursal no válida'}), 400
        
        # Encriptar la contraseña
        hashed_password = generate_password_hash(data['clave'], method='pbkdf2:sha256')

        nuevo_usuario = Usuario(
            nombre=data['nombre'],
            correo=data['correo'],
            clave=hashed_password,
            id_rol=data['id_rol'],
            id_sucursal=data['id_sucursal']
        )
            
        db.session.add(nuevo_usuario)
        db.session.commit()
        return jsonify({'message': 'Usuario registrado exitosamente'}), 201
    except Exception as e:
        print(f"🔸 Error en register: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al registrar el usuario'}), 500

# Ruta para iniciar sesión
@auth.route('/login', methods=['POST'])
@cross_origin()
def login():
    try:
        data = request.get_json()
        usuario = Usuario.query.filter_by(correo=data['correo']).first()
        if not usuario or not check_password_hash(usuario.clave, data['clave']):
            return jsonify({'message': 'Credenciales inválidas'}), 401
        
         # Acceder a rol_obj para obtener el rol del usuario
        rol = usuario.rol_obj.rol  # Aquí se accede al nombre del rol

        # Cambiar identity a string (necesario para evitar errores con JWT)
        access_token = create_access_token(identity=str(usuario.id))
        return jsonify({
            'access_token': access_token,
            'usuario': {
                'id': usuario.id,
                'nombre': usuario.nombre,
                'correo': usuario.correo,
                'id_rol': usuario.id_rol,
                'rol': rol
            }
        }), 200
    except Exception as e:
        print(f"🔸 Error en login: {str(e)}")
        return jsonify({'error': 'Ocurrió un error en el inicio de sesión'}), 500


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
                'usuario': Usuario.query.get(c.id_usuario).nombre if Usuario.query.get(c.id_usuario) else None,
                'comentario': c.comentario,
                'creado': c.creado.strftime('%Y-%m-%d %H:%M:%S')
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
@role_required(['Usuario', 'Agente', 'Administrador'])
def add_ticket_comentario(ticket_id):
    print(f"🔹 Petición para agregar comentario al ticket ID {ticket_id}")
    try:
        data = request.get_json()
        current_user = int(get_jwt_identity())

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
@role_required(['Administrador', 'Agente'])  # ✅ Permitir también a Agentes
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

        if not nuevo_agente or nuevo_agente.rol_obj.rol != 'Agente':
            return jsonify({'message': 'El usuario seleccionado no es un Agente'}), 400

        # Guardar el agente anterior antes de reasignar
        agente_anterior = Usuario.query.get(ticket.id_agente) if ticket.id_agente else None

        # 🔹 Si es Administrador, puede reasignar a cualquier agente
        if usuario_actual.rol_obj.rol == "Administrador":
            ticket.id_agente = nuevo_agente_id

        # 🔹 Si es Agente, solo puede reasignar a agentes de su departamento
        elif usuario_actual.rol_obj.rol == "Agente":
            # Obtener los agentes del departamento del ticket
            agentes_departamento = Usuario.query.join(agente_departamento).filter(
                agente_departamento.c.id_departamento == ticket.id_departamento
            ).all()

            agentes_permitidos = [agente.id for agente in agentes_departamento]

            if nuevo_agente_id not in agentes_permitidos:
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
@role_required(['Administrador'])
def get_agentes():
    try:
        agentes = Usuario.query.filter(Usuario.id_rol == Rol.query.filter_by(rol='Agente').first().id).all()
        return jsonify([{'id': a.id, 'nombre': a.nombre} for a in agentes]), 200
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
        return jsonify([{'id': r.id, 'rol': r.rol} for r in roles]), 200
    except Exception as e:
        print(f"🔸 Error en get_roles: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los roles'}), 500


# Ruta para filtrar usuarios activos
@api.route('/usuarios', methods=['GET'])
@jwt_required()
@role_required(['Administrador'])  # Solo el administrador puede ver la lista de usuarios
def get_usuarios():
    try:
        usuarios = Usuario.query.filter_by(id_estado=1).all()  # Solo usuarios activos
        usuario_list = [{
            "id": usuario.id,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "rol": usuario.rol_obj.rol,
            "sucursal": usuario.sucursal_obj.nombre,
            "estado": usuario.estado_obj.nombre
        } for usuario in usuarios]

        return jsonify(usuario_list), 200

    except Exception as e:
        print(f"🔸 Error en get_usuarios: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los usuarios'}), 500

# Ruta para actualizar usuarios 
@api.route('/usuarios/<int:user_id>', methods=['PUT'])
@jwt_required()
@role_required(['Administrador'])
def update_usuario(user_id):
    usuario = Usuario.query.get(user_id)
    if not usuario:
        return jsonify({'message': 'Usuario no encontrado'}), 404

    data = request.get_json()
     # Solo actualiza los campos proporcionados
    if 'nombre' in data:
        usuario.nombre = data['nombre']
    if 'correo' in data:
        usuario.correo = data['correo']
    if 'clave' in data and data['clave']:
        usuario.clave = generate_password_hash(data['clave'])  # Encriptar clave solo si se proporciona
    if 'id_rol' in data:
        usuario.id_rol = data['id_rol']
    if 'id_sucursal' in data:
        usuario.id_sucursal = data['id_sucursal']
    if 'id_estado' in data:
        usuario.id_estado = data['id_estado']
    if 'id_departamento' in data:
        usuario.departamentos = Departamento.query.filter(Departamento.id.in_(data['id_departamento'])).all()

    try:
        db.session.commit()
        return jsonify({'message': 'Usuario actualizado correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar usuario: {str(e)}'}), 500
    
# ruta para eliminar un usurio
@api.route('/usuarios/<int:user_id>', methods=['DELETE'])
@jwt_required()
@role_required(['Administrador'])
def delete_usuario(user_id):
    usuario = Usuario.query.get(user_id)
    if not usuario:
        return jsonify({'message': 'Usuario no encontrado'}), 404

    try:
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({'message': 'Usuario eliminado correctamente'}), 200
    except Exception as e:
        db.session.rollback()
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

    # Generar un nombre único para el archivo
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"ticket_{id}_{int(time.time())}.{file_ext}"
    file_path = os.path.join(upload_folder, unique_filename)
    
    # Guardar el archivo en el servidor
    file.save(file_path)

    # 🔹 Guardar el nombre del archivo en la base de datos
    try:
        ticket.adjunto = unique_filename  # Guardamos solo el nombre, no la ruta completa
        db.session.commit()
        print(f"✅ Archivo {unique_filename} guardado en la BD para el ticket {id}")
        return jsonify({'message': 'Archivo subido correctamente', 'adjunto': unique_filename}), 200
    except Exception as e:
        db.session.rollback()
        print(f"🔸 Error al guardar el adjunto en la BD: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al guardar el archivo en la base de datos'}), 500
    

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
@api.route('/usuarios/<int:user_id>/cambiar-clave', methods=['PUT'])
@jwt_required()
def cambiar_clave(user_id):
    try:
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'message': 'Usuario no encontrado'}), 404

        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not check_password_hash(usuario.clave, old_password):
            return jsonify({'message': 'Clave actual incorrecta'}), 400

        usuario.clave = generate_password_hash(new_password)
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

        agentes = Usuario.query.join(agente_departamento).filter(
            agente_departamento.c.id_departamento == id_departamento
        ).all()

        if not agentes:
            print("❌ No hay agentes asignados a este departamento.")
            return jsonify({"error": "No hay agentes en este departamento"}), 404

        agentes_list = [{'id': a.id, 'nombre': a.nombre} for a in agentes]

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
            {"id": 1, "nombre": "Activo"},
            {"id": 2, "nombre": "Inactivo"}
        ]
        return jsonify(estados), 200
    except Exception as e:
        print(f"🔸 Error en get_estados_usuarios: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener los estados de usuario'}), 500


# 🔹 Ruta para asignar agentes a departamentos
@api.route('/agentes/<int:id_agente>/departamentos', methods=['PUT'])
@jwt_required()
@role_required(['Administrador'])
def asignar_departamento_a_agente(id_agente):
    try:
        agente = Usuario.query.get(id_agente)
        if not agente:
            return jsonify({'message': 'Agente no encontrado'}), 404

        data = request.get_json()
        id_departamento = data.get('id_departamento')

        if not id_departamento:
            return jsonify({'message': 'ID de departamento requerido'}), 400

        # Asignar el departamento al agente
        departamento = Departamento.query.get(id_departamento)
        if not departamento:
            return jsonify({'message': 'Departamento no encontrado'}), 404

        agente.departamentos = [departamento]

        db.session.commit()
        return jsonify({'message': 'Agente asignado correctamente al departamento'}), 200

    except Exception as e:
        print(f"🔸 Error en asignar_departamento_a_agente: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Ocurrió un error al asignar el agente'}), 500

# Ruta para obtener agentes por departamentos
@api.route('/agentes/departamentos', methods=['GET'])
@jwt_required()
@role_required(['Administrador'])
def get_agentes_departamentos():
    try:
        agentes = Usuario.query.filter(
            Usuario.id_rol == Rol.query.filter_by(rol='Agente').first().id
        ).all()

        agentes_list = [
            {
                "id": agente.id,
                "nombre": agente.nombre,
                "departamentos": [d.nombre for d in agente.departamentos]  # Lista de departamentos asignados
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

    if nuevo_estado not in ["Abierto", "En Proceso", "Cerrado"]:
        return jsonify({"error": "Estado inválido"}), 400

    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket no encontrado"}), 404

    ticket.id_estado = TicketEstado.query.filter_by(nombre=nuevo_estado).first().id
    db.session.commit()

    return jsonify({"mensaje": "Estado actualizado correctamente"}), 200

# Ruta para crear departamentos
@api.route('/departamentos', methods=['POST'])
@jwt_required()
@role_required(['Administrador'])  # Solo los administradores pueden crear departamentos
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
@role_required(['Administrador'])  # Solo los administradores pueden eliminar departamentos
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
        agentes_asociados = db.session.query(agente_departamento).filter_by(id_departamento=id).count()
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




 