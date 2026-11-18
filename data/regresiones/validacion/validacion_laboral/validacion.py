"""Diagnóstico descriptivo: no ajusta el matching ni sustituye inferencia de encuesta."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
import hashlib
import numpy as np
import pandas as pd
from regresiones.validacion.correcciones.empates import buscar_vecinos
from regresiones.validacion.validacion_laboral.armonizacion_posicion import armonizar_posicion_geih, armonizar_posicion_ecv


def ocupacion_ecv(e):
    """PET; rutas afirmativas al bloque ocupados, negativas completas o salto 5.
    Un faltante no se convierte en no ocupado. Contradicciones quedan sin clasificar.
    """
    p, a, b, c = [e[x] for x in ['P6240', 'P6250', 'P6260', 'P6270']]
    sigue = p.isin([2, 3, 4, 6])
    si = p.eq(1) | (sigue & a.eq(1)) | (sigue & a.eq(2) & b.eq(1)) | (sigue & a.eq(2) & b.eq(2) & c.eq(1))
    no = p.eq(5) | (sigue & a.eq(2) & b.eq(2) & c.eq(2))
    # Una respuesta tras una ruta que ya terminó viola el salto del cuestionario.
    # No interpretar esos registros como confirmación independiente de ocupación.
    conflicto = (p.isin([1, 5]) & (a.notna() | b.notna() | c.notna())) | (
        sigue & a.eq(1) & (b.notna() | c.notna())) | (
        sigue & a.eq(2) & b.eq(1) & c.notna())
    out = np.full(len(e), np.nan)
    pet = e.P6040.ge(15).to_numpy()
    out[pet & no.to_numpy() & ~conflicto.to_numpy()] = 0
    out[pet & si.to_numpy() & ~conflicto.to_numpy()] = 1
    return out


def reserva_hogares(e, year):
    # Bloqueo a nivel de hogar; hash estable, no usa resultados laborales.
    keys = e.DIRECTORIO.astype(str) + '_' + e.SECUENCIA_P.astype(str)
    flags = {k: int(hashlib.sha256(f'validacion-v1:{year}:{k}'.encode()).hexdigest()[:8], 16) % 5 == 0 for k in keys.unique()}
    return keys.map(flags).to_numpy()


def media(x, w, mask):
    mask = np.asarray(mask) & np.isfinite(x) & np.isfinite(w) & (w > 0)
    return float(np.average(np.asarray(x)[mask], weights=w[mask])) if mask.any() else np.nan


def evaluar(year, g, e, gf, ef, gs, es, matched, fallback):
    """Ablación con exactamente los mismos pools; elimina solo la sexta dimensión."""
    alt = np.zeros(len(e), dtype=int)
    for s, grp in e.groupby(es):
        pos = grp.index.to_numpy()
        pool = g.index[gs == s].to_numpy()
        if not len(pool):
            _, c, sex = s.split('_')
            pool = g.index[(g.CLASE.astype(int).astype(str) == c) & (g.P3271.astype(int).astype(str) == sex)].to_numpy()
            if not len(pool):
                raise ValueError('No hay donantes con la misma zona y sexo; no se relaja este bloqueo.')
        _, idx = buscar_vecinos(gf[:, :5], ef[:, :5], pool, pos, k=1)
        alt[pos] = idx
    truth = ocupacion_ecv(e)
    pet = e.P6040.ge(15).to_numpy()
    valid = np.isfinite(truth)
    w = e.FEX_C.to_numpy(dtype=float)
    weighted_valid = np.isfinite(w) & (w > 0)
    reserve = reserva_hogares(e, year)
    direct = e.P6240.eq(1).to_numpy()
    masks = {'total': np.ones(len(e), bool), 'reserva_hogares': reserve,
             'soporte_exacto': ~fallback, 'fallback': fallback}
    rows, matrices, details = [], [], []
    for variant, idx in [('actual_6D', matched), ('sin_P6240_5D', alt)]:
        donor = g.iloc[idx].reset_index(drop=True)
        pred = donor.OCI.eq(1).to_numpy() & pet
        for scope, domain in masks.items():
            base = valid & domain & weighted_valid
            for weighting in ['sin_ponderar', 'FEX_C']:
                weights = np.ones(len(e)) if weighting == 'sin_ponderar' else w
                cells = {}
                for a in [0, 1]:
                    for b in [0, 1]:
                        m = base & (truth == a) & (pred == b)
                        cells[a,b] = float(weights[m].sum())
                        matrices.append(dict(anio=year, variante=variant, dominio=scope, ponderacion=weighting, observado=a, imputado=b, n=int(m.sum()), masa=cells[a,b]))
                tn, fp, fn, tp = [cells[k] for k in [(0,0),(0,1),(1,0),(1,1)]]
                ratio = lambda a,b: 100*a/b if b else np.nan
                hidden = base & (truth == 1) & ~direct
                rows.append(dict(anio=year, variante=variant, dominio=scope, ponderacion=weighting,
                    n=int(base.sum()), pet_sin_clasificar=int((pet & domain & ~valid).sum()),
                    sensibilidad=ratio(tp,tp+fn), especificidad=ratio(tn,tn+fp), vpp=ratio(tp,tp+fp),
                    concordancia=ratio(tp+tn,tp+tn+fp+fn), n_ocupados_no_principal=int(hidden.sum()),
                    recuperacion_no_principal=100*media(pred.astype(float),weights,hidden)))
        # Variables no utilizadas en la distancia, entre ocupados en ambas fuentes.
        # Cobertura explícita: no extrapolar estas métricas a ocupados no recuperados.
        gp = armonizar_posicion_geih(donor.P6430, year)
        ep = armonizar_posicion_ecv(e.P6435, year)
        # Grupo 6: categoría amplia sin remuneración; grupo 7: jornaleros.
        # GEIH 8 (otro) permanece excluido por falta de equivalencia específica.
        for scope, domain in masks.items():
            eligible = domain & (truth == 1) & weighted_valid
            both = eligible & pred
            for variable, x, y in [('pension', donor.P6920, e.P6920), ('posicion_grupos', gp, ep), ('horas', donor.P6800, e.P415)]:
                x, y = np.asarray(x,dtype=float), np.asarray(y,dtype=float)
                m = both & np.isfinite(x) & np.isfinite(y)
                if variable == 'pension': m &= np.isin(x,[1,2,3]) & np.isin(y,[1,2,3])
                if variable == 'horas': m &= (x>=0)&(x<=168)&(y>=0)&(y<=168)
                details.append(dict(anio=year,variante=variant,dominio=scope,variable=variable,
                    n_ocupados_ecv=int(eligible.sum()),n_comparables=int(m.sum()),
                    cobertura_pct=100*media(m.astype(float),w,eligible),
                    acuerdo_pct=100*media((x==y).astype(float),w,m) if variable!='horas' else np.nan,
                    mae_horas=media(np.abs(x-y),w,m) if variable=='horas' else np.nan,
                    sesgo_horas=media(x-y,w,m) if variable=='horas' else np.nan))
    flow = dict(anio=year, pet=int(pet.sum()), sin_clasificar=int((pet & ~valid).sum()),
                pesos_invalidos_pet=int((pet & ~weighted_valid).sum()), hogares_reserva=int(e.loc[reserve,['DIRECTORIO','SECUENCIA_P']].drop_duplicates().shape[0]),
                discrepancia_bloque_posicion=int((valid & ((truth==1)!=e.P6435.notna().to_numpy())).sum()))
    return rows, matrices, details, flow
