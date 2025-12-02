# Usar imagen oficial de Python
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Crear directorio para logs
RUN mkdir -p logs

# Crear directorio para uploads
RUN mkdir -p uploads

# Exponer puerto
EXPOSE 8080

# Configurar variables de entorno para producción
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0

# Comando para ejecutar la aplicación
# Optimizado para Cloud Run: 1 worker con threads para mejor uso de memoria
# Timeout aumentado a 300s para permitir inicialización lenta
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "300", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "50", "--preload", "app:app"] 