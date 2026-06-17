"""Contexto estático (CAG): ejemplos de estimaciones previas.

Estos ejemplos son el "conocimiento" del sistema. Funcionan como few-shot
examples: viajan dentro del prompt en cada llamada al LLM para que el modelo
genere nuevas estimaciones con un formato y criterio coherentes.

Son datos ficticios pero representativos. Cuanto más representativos sean del
tipo de estimaciones que queremos generar, mejor será la calidad del output.
"""

ESTIMATION_EXAMPLES = [
    {
        "meeting_summary": (
            "El cliente necesita una plataforma web de gestión de inventario para "
            "una cadena de tiendas de retail. Requiere CRUD de productos, control de "
            "stock por sucursal, roles de usuario (admin, encargado, vendedor) y un "
            "dashboard con métricas de ventas e inventario. Sin app móvil por ahora."
        ),
        "estimation": """## Estimación: Plataforma de Gestión de Inventario

### Desglose de tareas:
1. Diseño UI/UX: 40 horas
2. Backend API (CRUD inventario + stock por sucursal): 70 horas
3. Autenticación y roles: 20 horas
4. Dashboard con métricas: 30 horas
5. Testing y QA: 25 horas

**Total estimado: 185 horas**
**Equipo recomendado: 2 desarrolladores full-stack + 1 diseñador UX (part-time)**
**Duración estimada: 6-8 semanas**
""",
    },
    {
        "meeting_summary": (
            "Una startup quiere un MVP de marketplace de servicios profesionales: "
            "registro de prestadores y clientes, búsqueda y filtros por categoría, "
            "sistema de reservas con calendario y pagos en línea integrados con una "
            "pasarela. El diseño base ya está definido en Figma. Plazo agresivo."
        ),
        "estimation": """## Estimación: MVP Marketplace de Servicios

### Desglose de tareas:
1. Maquetación a partir de Figma: 30 horas
2. Backend API (usuarios, servicios, búsqueda/filtros): 80 horas
3. Sistema de reservas con calendario: 45 horas
4. Integración de pagos (pasarela): 35 horas
5. Panel de prestador y de cliente: 40 horas
6. Testing y QA: 30 horas

**Total estimado: 260 horas**
**Equipo recomendado: 2 desarrolladores backend + 1 frontend + 1 QA (part-time)**
**Duración estimada: 9-11 semanas**

**Riesgo a vigilar:** la integración de pagos suele tardar más de lo previsto por
verificación de cuentas y manejo de estados de transacción (idempotencia, reintentos).
""",
    },
]
