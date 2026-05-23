# Simulación RTV — UTN FRC — Grupo 11 — TP4

## Instalación y ejecución

```bash
pip install django
python manage.py migrate
python manage.py runserver
```

Luego abrir: http://127.0.0.1:8000

## Estructura del proyecto

simulacion_rtv/
├── simulador/
│   ├── simulation.py   ← LÓGICA de simulación completa
│   ├── views.py        ← Endpoint Django
│   ├── urls.py
│   └── templates/simulador/index.html  ← UI web
└── simulacion_rtv/
    ├── settings.py
    └── urls.py

## Sistema simulado

Planta de Revisión Técnica Vehicular con:
- 2 líneas de inspección (Frenos → Luces/Emisiones)
- Autos: llegadas exp neg (media 15 min)
- Camionetas: llegadas exp neg (media 30 min), PRIORIDAD sobre autos
- Frenos: U(4,7) min — con posibilidad de BLOQUEO
- Luces: U(6,10) min
- Jornada 08:00–16:00 (hasta vaciar el sistema)
