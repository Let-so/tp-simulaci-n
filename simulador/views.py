import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .simulation import run_simulation

def index(request):
    return render(request, 'simulador/index.html')

@csrf_exempt
def simulate(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)

        tiempo_max     = int(data.get('tiempo_max', 480))
        inicio_raw     = str(data.get('inicio_mostrar', 0)).replace(',', '.')
        inicio_mostrar = float(inicio_raw)
        cant_mostrar   = int(data.get('cant_mostrar', 50))

        tiempo_max     = max(1, tiempo_max)          # sin límite artificial de días
        cant_mostrar   = max(1, min(cant_mostrar, 100000))
        inicio_mostrar = max(0.0, inicio_mostrar)

        display_rows, last_row, stats, all_rows = run_simulation(
            tiempo_max, inicio_mostrar, cant_mostrar
        )

        return JsonResponse({
            'rows':       display_rows,
            'last_row':   last_row,
            'stats':      stats,
            'total_rows': len(all_rows),
        })
    except Exception as e:
        import traceback
        return JsonResponse({'error': str(e), 'trace': traceback.format_exc()}, status=500)
