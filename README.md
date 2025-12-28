# 🏭 Pharma TAD: Supply Chain Risk Simulator

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Status](https://img.shields.io/badge/Status-Active-success) ![Domain](https://img.shields.io/badge/Domain-Pharma%20Supply%20Chain-red)

## 📋 Descripción del Proyecto

**Pharma TAD** es un motor de simulación de datos sintéticos diseñado para modelar la cadena de suministros de una planta farmacéutica.

El objetivo principal es generar un **Data Warehouse** robusto y relacional que permita analizar riesgos de abastecimiento, calidad de proveedores y trazabilidad de producción, simulando escenarios complejos que difícilmente se encuentran en datasets públicos (Kaggle, etc.).

El script genera 5 años de historia transaccional utilizando lógica estocástica (aleatoriedad) controlada para simular la variabilidad real de la industria.

## Arquitectura de Datos (Modelo estrella)

El sistema exporta un set de archivos CSV normalizados (`data/raw/`) listos para ser utilizados por herramientas de BI como Power BI o Tableau:

### 🔷 Dimensiones (Maestros)
* **`dim_productos.csv`**: Maestro de SKUs con atributos críticos como Segmentación comercial ABC, Origen (Propio/Tercerista) y Estacionalidad.

* **`dim_proveedores.csv`**: Base de socios comerciales, distinguiendo entre Fabricantes de MP y Terceristas (Fasonería)

* **`dim_materias_primas.csv`**: Catálogo de activos y excipientes con nomenclatura realista generada combinatoriamente.

### 🔷 Hechos (Transaccional)
* **`fact_ordenes.csv`**: Planificación de la producción con tendencias de crecimiento interanual y picos estacionales.

* **`fact_consumos.csv`**: Trazabilidad detallada. Registra qué lotes específicos de materia prima (MP) se consumieron en cada orden.

* **`fact_calidad.csv`**: Historial de recepciones (Lotes de inspección), gestión de muestras y tasas de rechazo variables según el perfil del proveedor.


## ⚙️ Lógica de Negocio y Supuestos

Para enfocar el proyecto en Analytics sin replicar la complejidad transaccional de un ERP (como SAP), se definieron las siguientes reglas de negocio:

1. **Recetas Fijas (BOM):** Cada producto se genera con una estructura de fórmula fija (1 Activo + N Excipientes). Esto garantiza consistencia estructural para análisis de impacto ("Si falla el proveedor X, se detiene el producto Y").

2. **Consumo Estocástico (aleatorio):** Aunque la receta dicta *qué* materiales usar, la *cantidad* varia aleatoriamente en cada orden.

3. **Gestión de Stocks (Simplificación):** Se asume disponibilidad infinita de los lotes aprobados. No se realiza balance de massa de saldos remanentes ni validación de vencimientos (FEFO).

4. **Terceristas:** Los productos fabricados externamente no generan registros de consumo de materia prima, simulando los "vacíos de información" típicos en la gestión de fasonería externos.

## 🛠️ Tecnologías Utilizadas

* **Python:** Lenguaje principal.
* **Pandas:** Estructuración, manipulación y exportación de Dataframes.
* **Faker:** Generación de datos demográficos y empresariales realistas (Localización `es_AR`).
* **Numpy / Random:** Generación de distribuciones estadísticas y muestreo ponderado.
* **Typing:** Uso de `TypedDict`y Type Hinting para asegurar la calidad y consistencia del código.

## 📦 Instalación y Ejecución

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/DaniTadd/Pharma-Tad-Analytics.git](https://github.com/DaniTadd/Pharma-Tad-Analytics.git)
   ```

2. **Crear entorno virtual (Recomendado):**
   ```bash
   python -m venv venv
   # En Windows:
   .\venv\Scripts\activate
   # En Mac/Linux:
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install pandas numpy faker
   ```

4. **Ejecutar la simulación:**
   ```bash
   python scripts/generador_datos_pharma.py
   ```
   *Los archivos generados aparecerán en la carpeta `data/raw/`.*

---
**Autor:** Daniel García Taddía
*Data Science Student / QA Pharma Analist*