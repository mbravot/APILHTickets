#!/usr/bin/env python3
"""
Script para obtener información de la instancia de Google Cloud SQL
"""

def get_cloud_sql_connection_info():
    """Muestra información para configurar la conexión a Cloud SQL"""
    
    print("🔹 Configuración para Google Cloud SQL")
    print("=" * 50)
    
    print("\n📋 Para obtener la IP de tu instancia de Cloud SQL:")
    print("1. Ve a Google Cloud Console")
    print("2. Navega a SQL > Instancias")
    print("3. Selecciona tu instancia 'gestion-la-hornilla'")
    print("4. En la pestaña 'Conexiones', busca 'Dirección IP pública'")
    
    print("\n🔧 Configuración para desarrollo local (Windows):")
    print("DATABASE_URL=mysql+pymysql://UserApp:&8y7c()tu9t/+,6`@[TU_IP_PUBLICA]:3306/lahornilla_base_normalizada")
    
    print("\n🔧 Configuración para producción (Google Cloud):")
    print("DATABASE_URL=mysql+pymysql://UserApp:&8y7c()tu9t/+,6`@/lahornilla_base_normalizada?unix_socket=/cloudsql/[PROJECT_ID]:[REGION]:gestion-la-hornilla")
    
    print("\n📝 Pasos para configurar:")
    print("1. Reemplaza [TU_IP_PUBLICA] con la IP de tu instancia")
    print("2. Reemplaza [PROJECT_ID] con tu Project ID")
    print("3. Reemplaza [REGION] con tu región (ej: us-central1)")
    print("4. Asegúrate de que el firewall permita conexiones desde tu IP")
    
    print("\n🔒 Configuración del firewall:")
    print("1. En Google Cloud Console > SQL > Instancias")
    print("2. Selecciona tu instancia > Conexiones")
    print("3. En 'Redes autorizadas', agrega tu IP actual")
    print("4. O usa '0.0.0.0/0' para permitir todas las IPs (solo para desarrollo)")

if __name__ == "__main__":
    get_cloud_sql_connection_info() 