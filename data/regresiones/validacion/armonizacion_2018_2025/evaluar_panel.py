"""Diagnostica el panel oficial sin modificar microdatos ni estimaciones.

Ejecutar desde cualquier carpeta con python3 /ruta/a/evaluar_panel.py.
La calidad se resume a partir de los universos y donantes de la construcción
original; no se reconstruyen denominadores con aproximaciones desde el panel.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import pandas as pd

BASE = (Path(__file__).resolve().parents[3])
sys.path.insert(0, str(BASE))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import (
    CARPETA, PANEL_2018_2025, PANEL_CERRADO_2022_2025,
)

DIAGNOSTICOS = (Path(__file__).resolve().parents[3] / 'datos/armonizados_2018_2025/construccion/paneles/diagnosticos_panel_regresion.parquet')
OUT = (Path(__file__).resolve().parents[3] / 'datos/armonizados_2018_2025/diagnosticos/panel_2018_2025')
RESULTADOS = {
    'tasa_desempleo': 'Desempleo',
    'prop_no_cotiza_respuesta12': 'No cotización',
    'log_sal_real_medio': 'Ingreso',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def estructura(d, panel, periodo):
    return dict(panel=panel, periodo=periodo, filas=len(d),
                cohortes=d.id_cohorte.nunique(), columnas=len(d.columns),
                anios=d.anio.nunique(), pet_min=d.n_obs_pet.min(),
                pet_mediana=d.n_obs_pet.median(), pet_max=d.n_obs_pet.max())


def calidad(d, panel, anio=None):
    rows = []
    for variable, etiqueta in RESULTADOS.items():
        z = d.loc[d.variante.eq(panel) & d.variable.eq(variable)]
        if anio is not None:
            z = z.loc[z.anio.eq(anio)]
        o = z.loc[z.n_observados.gt(0)]
        rows.append(dict(panel=panel, anio=anio, variable=variable,
                         resultado=etiqueta, celdas_total=len(z),
                         celdas_observadas=len(o),
                         receptores_min=o.n_observados.min(),
                         receptores_mediana=o.n_observados.median(),
                         donantes_min=o.n_donantes_individuales.min(),
                         donantes_mediana=o.n_donantes_individuales.median(),
                         cobertura_min_pct=100*z.cobertura.min(),
                         kish_receptores_min=o.n_kish_receptores.min(),
                         kish_donantes_min=o.n_kish_donantes_individuales.min()))
    return rows


def clean(obj):
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return float(obj) if np.isfinite(obj) else None
    return obj


def run():
    panel = pd.read_parquet(PANEL_2018_2025)
    cerrado = pd.read_parquet(PANEL_CERRADO_2022_2025)
    diag = pd.read_parquet(DIAGNOSTICOS)
    years = list(range(2018, 2026))
    assert sorted(panel.anio.unique()) == years
    assert not panel.duplicated(['id_cohorte', 'anio']).any()
    assert panel.groupby('anio').id_cohorte.nunique().eq(330).all()
    assert panel.groupby('id_cohorte').anio.nunique().eq(8).all()
    assert len(panel) == 2640
    assert sorted(cerrado.anio.unique()) == list(range(2022, 2026))
    assert not cerrado.duplicated(['id_cohorte', 'anio']).any()
    assert cerrado.groupby('anio').id_cohorte.nunique().eq(330).all()
    assert not diag.duplicated(['variante', 'anio', 'id_cohorte', 'variable']).any()
    # La misma cuenta PET debe respaldar el panel publicado y el diagnóstico.
    pet = diag.loc[diag.variante.eq('principal') & diag.variable.eq('edad_media'),
                   ['id_cohorte', 'anio', 'n_observados']]
    check = panel[['id_cohorte', 'anio', 'n_obs_pet']].merge(
        pet, on=['id_cohorte', 'anio'], how='outer', validate='one_to_one', indicator=True)
    assert check['_merge'].eq('both').all()
    assert check.n_obs_pet.eq(check.n_observados).all()
    pet_cerrado = diag.loc[diag.variante.eq('cerrada') & diag.variable.eq('edad_media')
                          & diag.anio.between(2022, 2025),
                          ['id_cohorte', 'anio', 'n_observados']]
    check_cerrado = cerrado[['id_cohorte', 'anio', 'n_obs_pet']].merge(
        pet_cerrado, on=['id_cohorte', 'anio'], how='outer',
        validate='one_to_one', indicator=True)
    assert check_cerrado['_merge'].eq('both').all()
    assert check_cerrado.n_obs_pet.eq(check_cerrado.n_observados).all()
    # Disponibilidad de cada resultado frente a la base efectivamente usada.
    for variable in RESULTADOS:
        z = diag.loc[diag.variante.eq('principal') & diag.variable.eq(variable),
                     ['id_cohorte', 'anio', 'n_observados']]
        c = panel[['id_cohorte', 'anio', variable]].merge(
            z, on=['id_cohorte', 'anio'], validate='one_to_one')
        assert len(c) == len(panel)
        assert c[variable].notna().eq(c.n_observados.gt(0)).all()
    # Las exposiciones basales se conservan en el tiempo dentro de su unidad.
    basales = [c for c in panel if c.endswith(('_pct_c', '_pct_d', '_mm_c', '_mm_d'))]
    for col in basales:
        assert panel.groupby('id_cohorte')[col].nunique(dropna=False).le(1).all(), col
    anual = [estructura(d, 'Principal', str(y)) | {'anio': int(y)}
             for y, d in panel.groupby('anio')]
    calidad_anual = [row for y in years for row in calidad(diag, 'principal', y)]
    comparacion = [estructura(panel.loc[panel.anio.ge(2022)], 'Principal', '2022–2025'),
                   estructura(cerrado, 'Cerrado hasta 2007', '2022–2025')]
    d22 = diag.loc[diag.anio.between(2022, 2025)]
    resumen = {
        'periodo': '2018–2025', 'estructura': estructura(panel, 'Principal', '2018–2025'),
        'resumen': {'estructura': estructura(panel, 'Principal', '2018–2025'),
                    'calidad': calidad(diag, 'principal'),
                    'cohortes_con_aioe_basal': int(panel.loc[panel.anio.eq(2022), 'aioe_pct_c'].notna().sum())},
        'estructura_anual': anual, 'calidad_anual': calidad_anual,
        'calidad_periodo': calidad(diag, 'principal'),
        'comparacion_2022_2025': comparacion,
        'comparacion_cerrado_2022_2025': {'estructura': comparacion,
             'calidad': calidad(d22, 'principal') + calidad(d22, 'cerrada')},
        'calidad_comparacion_2022_2025': calidad(d22, 'principal') + calidad(d22, 'cerrada'),
        'verificaciones': {'llaves_unicas': True, 'cohortes_por_anio': 330,
            'anios_por_cohorte': 8, 'conteos_pet_coinciden_diagnostico': True,
            'conteos_pet_2021_coinciden': True, 'conteos_cerrado_2022_2025_coinciden': True, 'disponibilidad_resultados_coincide': True,
            'exposiciones_basales_constantes': basales},
        'universos': {
            'pet': 'Personas de 15 años o más; tamaños son conteos muestrales, no población expandida.',
            'Desempleo': 'Desocupados entre fuerza laboral con condición válida.',
            'No cotización': 'Ocupados con respuesta pensional afirmativa o negativa; cobertura respecto de ocupados.',
            'Ingreso': 'Ocupados con ingreso laboral real positivo; cobertura respecto de ocupados.',
            'donantes': 'Donantes individuales distintos dentro del universo del resultado y la celda; su reutilización reduce el soporte independiente.',
            'kish': 'Tamaño efectivo descriptivo por concentración de ponderaciones; no es una varianza de diseño ni incorpora incertidumbre de imputación.'},
        'limitaciones': [
            'Panel cerrado hasta nacimiento en 2007 se compara únicamente en 2022–2025; no es una población cerrada desde 2018.',
            'Disponibilidad de los tres resultados no implica disponibilidad de todas las columnas ni igual precisión por celda.',
            'Los diagnósticos reutilizan los universos y conteos de construcción; los cotejos certifican llaves, PET y disponibilidad, no reestiman por sí solos cada media desde microdatos.',
            'GEIH de 2018 y 2019 tiene 24 dominios departamentales presentes; el panel receptor conserva 33 y los donantes de territorios ausentes proceden de la ampliación del bloqueo.',
            'Los códigos ocupacionales comparables no están disponibles en las bases armonizadas de 2018–2020; las exposiciones basales proceden de 2022, no de esos años.',
            'La igualdad de composición de las cohortes entre encuestas no está garantizada; residencia, migración y selección muestral pueden cambiar.'],
        'fuentes': {str(p.relative_to(BASE)): sha(p) for p in [PANEL_2018_2025, PANEL_CERRADO_2022_2025, DIAGNOSTICOS]},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = (Path(__file__).resolve().parents[3] / 'datos/armonizados_2018_2025/diagnosticos/panel_2018_2025/evaluacion_panel.json')
    path.write_text(json.dumps(clean(resumen), ensure_ascii=False, indent=2, allow_nan=False))
    print(path)
    print(pd.DataFrame(anual).to_string(index=False))
    print(pd.DataFrame(resumen['calidad_periodo']).to_string(index=False))
    print(pd.DataFrame(calidad_anual).to_string(index=False))


if __name__ == '__main__':
    run()
