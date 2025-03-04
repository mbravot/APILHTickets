from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship

db = SQLAlchemy()

CHILE_TZ = pytz.timezone('America/Santiago')  

# 🔹 Tabla intermedia para la relación muchos a muchos entre Agentes y Departamentos
agente_departamento = Table(
    'agente_departamento',
    db.metadata,
    Column('id_agente', Integer, ForeignKey('usuarios.id'), primary_key=True),
    Column('id_departamento', Integer, ForeignKey('departamento.id'), primary_key=True)
)

# 🔹 Modelo Estado
class Estado(db.Model):
    __tablename__ = 'estado'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    usuarios = db.relationship('Usuario', back_populates='estado_obj')

# 🔹 Modelo Sucursal
class Sucursal(db.Model):
    __tablename__ = 'sucursales'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    usuarios = db.relationship('Usuario', back_populates='sucursal_obj')

# 🔹 Modelo Rol
class Rol(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    rol = db.Column(db.String(45), nullable=False)
    usuarios = db.relationship('Usuario', back_populates='rol_obj', lazy='dynamic')

# 🔹 Modelo Usuario
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    clave = db.Column(db.String(255), nullable=False)
    id_rol = db.Column(Integer, db.ForeignKey('roles.id'), nullable=False)
    id_sucursal = db.Column(Integer, db.ForeignKey('sucursales.id'), nullable=False)
    id_estado = db.Column(Integer, db.ForeignKey('estado.id'), nullable=False, default=1)  # 1 = Activo, 2 = Inactivo
    creado = db.Column(DateTime, default=lambda: datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(CHILE_TZ))

    # ✅ Relaciones corregidas
    rol_obj = db.relationship('Rol', back_populates='usuarios')
    sucursal_obj = db.relationship('Sucursal', back_populates='usuarios')  
    estado_obj = db.relationship('Estado', back_populates='usuarios')  

    # ✅ Relación con Departamentos (Muchos a Muchos)
    departamentos = relationship("Departamento", secondary=agente_departamento, back_populates="agentes")

# 🔹 Modelo TicketEstado
class TicketEstado(db.Model):
    __tablename__ = 'ticket_estado'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

# 🔹 Modelo TicketPrioridad
class TicketPrioridad(db.Model):
    __tablename__ = 'ticket_prioridad'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

# 🔹 Modelo Departamento
class Departamento(db.Model):
    __tablename__ = 'departamento'
    id = db.Column(Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)

    # ✅ Relación con Agentes (Muchos a Muchos)
    agentes = relationship("Usuario", secondary=agente_departamento, back_populates="departamentos")

# 🔹 Modelo Ticket
class Ticket(db.Model):
    __tablename__ = 'tickets'
    id = db.Column(Integer, primary_key=True)
    id_usuario = db.Column(Integer, db.ForeignKey('usuarios.id'), nullable=False)  # Usuario que creó el ticket
    id_agente = db.Column(Integer, db.ForeignKey('usuarios.id'), nullable=True)  # Agente asignado al ticket
    id_estado = db.Column(Integer, db.ForeignKey('ticket_estado.id'), nullable=False)
    id_prioridad = db.Column(Integer, db.ForeignKey('ticket_prioridad.id'), nullable=False)
    id_departamento = db.Column(Integer, db.ForeignKey('departamento.id'), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(Text, nullable=False)
    creado = db.Column(DateTime, default=lambda: datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(CHILE_TZ))
    actualizado = db.Column(DateTime, default=lambda: datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(CHILE_TZ), onupdate=datetime.utcnow)
    adjunto = db.Column(db.String(255), nullable=True) 

    # Relaciones con otros modelos
    usuario = db.relationship('Usuario', foreign_keys=[id_usuario], backref='tickets_creados', lazy='joined')
    agente = db.relationship('Usuario', foreign_keys=[id_agente], backref='tickets_asignados', lazy='joined')  
    estado = db.relationship('TicketEstado', backref='tickets', lazy='joined')
    prioridad = db.relationship('TicketPrioridad', backref='tickets', lazy='joined')
    departamento = db.relationship('Departamento', backref='tickets', lazy='joined')

# 🔹 Modelo TicketComentario
class TicketComentario(db.Model):
    __tablename__ = 'ticket_comentario'
    id = db.Column(db.Integer, primary_key=True)
    id_ticket = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    comentario = db.Column(Text, nullable=False)
    creado = db.Column(DateTime, default=lambda: datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(CHILE_TZ))

    # Relaciones con Ticket y Usuario
    ticket = db.relationship('Ticket', backref='comentarios', lazy='joined')
    usuario = db.relationship('Usuario', backref='comentarios', lazy='joined')

    #fin  
