import pandas as pd
import numpy as np
import random
from faker import Faker
from datetime import datetime, timedelta
from typing import List, Dict, Any, TypedDict, Optional

# ==========================================
# NOTA TÉCNICA: ALCANCE Y SIMPLIFICACIONES DEL MODELO
# ==========================================
# 1. Estructura BOM (Bill of Materials):
#    Se implementa una asignación FIJA de materias primas por SKU (1 Activo + N Excipientes).
#    Esto permite análisis consistentes de impacto ("Si falla MP-X, afecta a Producto-Y").
#    Sin embargo, las CANTIDADES de consumo son estocásticas (variables) y no siguen una
#    fórmula cuantitativa estricta.
#
# 2. Gestión de Stocks (Simplificación):
#    El modelo asume disponibilidad infinita de los lotes de MP aprobados.
#    La selección del lote para consumir se realiza de forma aleatoria sobre el histórico
#    de lotes aprobados, sin realizar descuento de stock (Balance de Masa) ni validar
#    fechas de vencimiento. 
#    Si no hay histórico de compras para una MP requerida, la orden se genera sin consumo
#    asociado (simulando quiebre de stock o error de registro).
# ==========================================

# ==================================================
# 0. CONFIGURACIÓN Y DEFINICIÓN DE TIPOS
# ==================================================
fake = Faker('es_AR')
np.random.seed(42)
random.seed(42)

print("🏭 INICIANDO SIMULACIÓN 'PHARMA TAD'...")

# --- Definición de Tipos (TypedDirect) ---
class Producto(TypedDict):
    SKU: str
    Nombre: str
    Tipo: str
    Segmentacion: str
    Origen_Fabricacion: str
    Estacionalidad: Optional[str]

class Proveedor(TypedDict):
    ID_Proveedor: str
    Nombre_Fantasia: str
    Pais: str
    Tipo: str

class MateriaPrima(TypedDict):
    Codigo_MP: str
    Nombre_MP: str
    Categoria: str

class AnalisisCalidad(TypedDict):
    Nro_Analisis: str
    Codigo_MP: str
    ID_Proveedor: str
    Fecha_Recepcion: datetime
    Cantidad_Recibida: float
    Es_Muestra: str
    Estado_Calidad: str

class OrdenProduccion(TypedDict):
    Nro_Orden: str
    SKU: str
    Fecha_Inicio: datetime
    Cantidad_Programada: int
    Lote_Producto: str

class Consumo(TypedDict):
    Nro_Orden: str
    Codigo_MP: str
    Nro_Analisis: str
    Cantidad_Consumida: float
    Posicion: int

class ItemBOM(TypedDict):
    SKU_Producto: str
    Codigo_MP: str
    Cantidad_Teorica_por_1000_unid: float

# ==================================================
# 1.0 DIMENSIÓN MATERIAS PRIMAS Y PROVEEDORES
# ==================================================

print("    Generando Maestro de Materias Primas y Proveedores...")

n_proveedores: int = 30
proveedores_list: List[Proveedor] = []
# A. Proveedores
for i in range(1, n_proveedores + 1):
    es_tercerista = (i > 25)
    prov: Proveedor = {
        'ID_Proveedor': f'PROV-{i:03d}',
        'Nombre_Fantasia': fake.company(),
        'Pais': fake.country(),
        'Tipo': 'Tercerista' if es_tercerista else 'Fabricante MP'
    }
    proveedores_list.append(prov)
df_proveedores = pd.DataFrame(proveedores_list)
df_proveedores.to_csv('data/raw/dim_proveedores.csv', index=False, encoding='utf-8-sig')

# B. Materias Primas (Nombres Reales - Combinatoria)
activos_base = ['Paracetamol', 'Ibuprofeno', 'Metformina', 'Atorvastatina', 'Amoxicilina', 
    'Losartan', 'Omeprazol', 'Clonazepam', 'Enalapril', 'Valsartan', 
    'Aspirina', 'Dipirona']
excipientes_base = ['Lactosa', 'Almidón de Maíz', 'Estearato de Magnesio', 'Celulosa', 'Talco', 'Povidona', 'Dióxido de Silicio']
variantes = ['Micronizado', 'Directo', 'USP', 'BP', 'Granulado', 'Malla 200']

mps_data: List[MateriaPrima] = []
conteo_mp: int = 1

# Generación de Activos
for nombre in activos_base:
    for var in variantes[:3]:
        mp: MateriaPrima = {
            'Codigo_MP': f"MP-{conteo_mp:04d}",
            'Nombre_MP': f"{nombre} {var}",
            'Categoria': 'Activo'
        }
        mps_data.append(mp)
        conteo_mp += 1
        
# Generación de Excipientes

for nombre in excipientes_base:
    for var in variantes:
        mp: MateriaPrima = {
            'Codigo_MP': f"MP-{conteo_mp:04d}",
            'Nombre_MP': f"{nombre} {var}",
            'Categoria': 'Excipiente'
        }
        mps_data.append(mp)
        conteo_mp += 1

df_mps = pd.DataFrame(mps_data)
df_mps.to_csv('data/raw/dim_materias_primas.csv', index=False, encoding='utf-8-sig')



# ==================================================
# 2.0 DIMENSIÓN PRODUCTOS
# ==================================================

print("    Generando Maestro de Productos y asignando Recetas Fijas...")
n_productos: int = 50
tipos_producto: List[str]= ['Comprimidos', 'Jarabe', 'Inyectable', 'Crema']
origenes: List[str] = ['Propio', 'Propio', 'Propio', 'Tercerista']
sufijos_prod: List[str] = ['Forte', 'Plus', '500', 'Ped', 'Lib. Prolongada', 'Max', 'Dúo', 'Compuesto', 'Cb']

# Estrategia de Nombres Únicos: Generar universo y muestrear
nombres_posibles = [f"{activo} {sufijo}" for activo in activos_base for sufijo in sufijos_prod]

# Verificación de seguridad
if len(nombres_posibles) < n_productos:
    raise ValueError(f"Error: Se requieren {n_productos} productos, pero sólo hay {len(nombres_posibles)} combinaciones de nombres.")

nombres_seleccionados: List[str] = random.sample(nombres_posibles, k=n_productos)

productos_data: List[Producto] = []
# Diccionario para guardar la BOM: Clave (SKU) -> Valor (Lista de Códigos MP)
boms_maestras: Dict[str, List[str]] = {}

# Listas auxiliares para elegir ingredientes
lista_activos = [mp['Codigo_MP'] for mp in mps_data if mp['Categoria'] == 'Activo']
lista_excipientes = [mp['Codigo_MP'] for mp in mps_data if mp['Categoria'] == 'Excipiente']

for i in range(1, n_productos + 1):
    sku = f"PROD-{i:04d}"
    origen = str(np.random.choice(origenes))
    # Tomamos un nombre de los seleccionados
    nombre_producto: str = nombres_seleccionados.pop()
    # 1. Crear Producto
    prod: Producto = {
        'SKU': sku,
        'Nombre': nombre_producto,
        'Tipo': random.choice(tipos_producto),
        'Segmentacion': str(np.random.choice(['A', 'B', 'C'], p=[0.2, 0.5, 0.3])),
        'Origen_Fabricacion': origen,
        'Estacionalidad': random.choice([None, 'Invierno', 'Verano'])
    }
    productos_data.append(prod)

    # Asignar Receta Fija (BOM)
    if origen == 'Propio':
        # Regla: 1 Activo + 2 a 4 Excipientes
        mi_activo: str = random.choice(lista_activos)
        mis_excipientes: List[str] = random.sample(lista_excipientes, k=random.randint(2, 4))
        boms_maestras[sku] = [mi_activo] + mis_excipientes
    else:
        boms_maestras[sku] = [] # Tercerista no tiene receta interna

df_productos = pd.DataFrame(productos_data)
df_productos.to_csv('data/raw/dim_productos.csv', index=False, encoding='utf-8-sig')

# ==================================================
# 2.1 DIMENSIÓN PRODUCTOS - BOMs
# ==================================================

print("    Exportando Tabla puente de BOMs")
# Mapeo en un diccionario para no recorrer la lista con 100 materias primas cada vez.
mapa_categorias: Dict[str, str] = {mp['Codigo_MP']: mp['Categoria'] for mp in mps_data}
bom_data_flat: List[ItemBOM] = []

for sku, lista_mps in boms_maestras.items():
    for mp_codigo in lista_mps:
        categoria: str = mapa_categorias[mp_codigo]

        if categoria == 'Activo':
            cant = round(random.uniform(0.5, 5.0), 3)
        else:
            cant = round(random.uniform(2.0, 15.0), 3)

        item: ItemBOM = {
            'SKU_Producto': sku,
            'Codigo_MP': mp_codigo,
            'Cantidad_Teorica_por_1000_unid': cant
        }
        bom_data_flat.append(item)
        
df_bom = pd.DataFrame(bom_data_flat)
df_bom.to_csv('data/raw/bridge_BOM.csv', index=False, encoding='utf-8-sig')

# ==================================================
# 3.0 FACT CALIDAD (Recepción y Análisis)
# ==================================================

print("    Simulando Análisis de Calidad...")
n_analisis: int = 3500
analisis_data: List[AnalisisCalidad] = []

fecha_inicio = datetime(2020, 1, 1)
dias_simulacion = 365 * 5

for i in range(1, n_analisis +1):
    fecha = fecha_inicio + timedelta(days=random.randint(0, dias_simulacion))
    prov = random.choice(proveedores_list)
    mp = random.choice(mps_data)

    es_muestra = random.random() < 0.10
    cantidad = round(random.uniform(0.1, 1.0),2) if es_muestra else round(random.uniform(10, 5000), 2)

    # Crecimiento anual
    cantidad = round(cantidad * (1 + (fecha.year - 2020) * 0.1), 2)

    tasa_falla = 0.1 if prov['Tipo'] == 'Tercerista' else 0.05
    estado = str(np.random.choice(['Aprobado', 'Rechazado'], p=[1-tasa_falla, tasa_falla]))
    reg: AnalisisCalidad = {
        'Nro_Analisis': f'QC-{fecha.year}-{i:05d}',
        'Codigo_MP': mp['Codigo_MP'],
        'ID_Proveedor': prov['ID_Proveedor'],
        'Fecha_Recepcion': fecha,
        'Cantidad_Recibida': cantidad,
        'Es_Muestra': 'Si' if es_muestra else 'No',
        'Estado_Calidad': estado
    }
    analisis_data.append(reg)
df_calidad = pd.DataFrame(analisis_data)
df_calidad.to_csv('data/raw/fact_calidad.csv', index=False, encoding='utf-8-sig')

# ==================================================
# 4.0 FACT ÓRDENES DE PRODUCCIÓN
# ==================================================
print("    Planificando Órdenes de Producción...")
n_ordenes: int = 3000
ordenes_data: List[OrdenProduccion] = []
consumos_data: List[Consumo] = []
# Indexación del stock disponible para búsqueda rápida
# Clave: Codigo_MP -> Valor: Lista de Análisis Aprobados

stock_disponible: Dict[str, List[AnalisisCalidad]] = {}
for a in analisis_data:
    if a['Estado_Calidad'] == 'Aprobado':
        mp_code = a['Codigo_MP']
        if mp_code not in stock_disponible:
            stock_disponible[mp_code] = []
        stock_disponible[mp_code].append(a)

for i in range(1, n_ordenes +1):
    prod = random.choice(productos_data)
    fecha_prod = fecha_inicio + timedelta(days=random.randint(0, dias_simulacion))
    
    # Generar Orden
    nro_orden = f"OF-{fecha_prod.year}-{i:04d}"
    #Lógica de cantidad y estacionalidad

    growth = 1 + ((fecha_prod.year - 2020) * 0.15)
    cantidad_prog = random.randint(1000, 50000) * growth

    if prod['Estacionalidad'] == 'Invierno' and fecha_prod.month in [5, 6, 7, 8]:
        cantidad_prog *= 1.5
    elif prod['Estacionalidad'] == 'Verano' and fecha_prod.month in [12, 1, 2]:
        cantidad_prog *= 1.5
    

    orden: OrdenProduccion = {
        'Nro_Orden': nro_orden,
        'SKU': prod['SKU'],
        'Fecha_Inicio': fecha_prod,
        'Cantidad_Programada': int(cantidad_prog),
        'Lote_Producto': f'L-{fake.bothify(text="??###")}'
    }
    ordenes_data.append(orden)

    # Generar Consumos (sólo si es propio)
    if prod['Origen_Fabricacion'] == 'Propio':
        # Vemos la receta fija del diccionario
        receta = boms_maestras[prod['SKU']]
        posicion_counter = 1
        for mp_requerida in receta:
            # Vemos si existe stock histórico de esta MP
            lotes_posibles = stock_disponible.get(mp_requerida, [])

            if lotes_posibles:
                lote_elegido = random.choice(lotes_posibles)

                consumo: Consumo = {
                    'Nro_Orden': nro_orden,
                    'Codigo_MP': mp_requerida,
                    'Nro_Analisis': lote_elegido['Nro_Analisis'], # Trazabilidad
                    'Cantidad_Consumida': round(random.uniform(5, 50), 3),
                    'Posicion': posicion_counter
                }
                consumos_data.append(consumo)
                posicion_counter += 1

df_ordenes = pd.DataFrame(ordenes_data)
df_consumos = pd.DataFrame(consumos_data)

df_ordenes.to_csv('data/raw/fact_ordenes.csv', index=False, encoding='utf-8-sig')
df_consumos.to_csv('data/raw/fact_consumos.csv', index=False, encoding='utf-8-sig')

print(f"✅ ¡SIMULACIÓN FINALIZADA CON ÉXITO!")
    


