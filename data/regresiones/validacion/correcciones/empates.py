"""Vecinos y sensibilidad descriptiva; no constituye imputación múltiple.

La dimensión 1 corresponde a educación. Si falta en el receptor, se omite;
si está observada se exigen donantes con educación observada, salvo que el
pool completo carezca de ella. Las otras dimensiones deben ser finitas.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
import numpy as np
from scipy.spatial import cKDTree


def buscar_vecinos(gf, ef, pool, pos, k=1):
    """Devuelve distancias e índices absolutos; -1 indica vecino inexistente.

    Conserva el desempate cKDTree original (orden del pool), sin aleatorizar.
    """
    pool, pos = np.asarray(pool, dtype=int), np.asarray(pos, dtype=int)
    if not len(pool):
        raise ValueError('No hay donantes en el pool')
    if k < 1:
        raise ValueError('k debe ser positivo')
    if not np.isfinite(np.delete(gf[pool], 1, axis=1)).all() or not np.isfinite(np.delete(ef[pos], 1, axis=1)).all():
        raise ValueError('Faltantes no educativos en el vector de distancia')
    distances = np.full((len(pos), k), np.inf)
    indices = np.full((len(pos), k), -1, dtype=int)
    donor_known = np.isfinite(gf[pool, 1])
    recipient_known = np.isfinite(ef[pos, 1])
    for known in (False, True):
        subset = np.flatnonzero(recipient_known == known)
        if not len(subset):
            continue
        use_education = known and donor_known.any()
        candidates = pool[donor_known] if use_education else pool
        columns = np.arange(gf.shape[1]) if use_education else np.delete(np.arange(gf.shape[1]), 1)
        tree = cKDTree(gf[np.ix_(candidates, columns)])
        d, ix = tree.query(ef[np.ix_(pos[subset], columns)], k=k)
        d, ix = np.asarray(d).reshape(len(subset), k), np.asarray(ix).reshape(len(subset), k)
        valid = ix < len(candidates)
        absolute = np.full(ix.shape, -1, dtype=int)
        absolute[valid] = candidates[ix[valid]]
        distances[subset], indices[subset] = d, absolute
    return (distances[:, 0], indices[:, 0]) if k == 1 else (distances, indices)


def diagnosticar_empates(year, g, e, gf, ef, gs, es, matched):
    """Diagnóstico por año y alternativa segundo vecino solo cuando hay empate.

    No cambia matched. La alternativa no es un sorteo uniforme entre todos
    los minimizadores; mide sensibilidad a un candidato equivalente observado.
    """
    tied = np.zeros(len(e), dtype=bool)
    alternative = np.asarray(matched, dtype=int).copy()
    no_education = np.zeros(len(e), dtype=bool)
    for stratum, grp in e.groupby(es):
        pos = grp.index.to_numpy()
        pool = g.index[gs == stratum].to_numpy()
        if not len(pool):
            _, zone, sex = stratum.split('_')
            pool = g.index[(g.CLASE.astype(int).astype(str) == zone) & (g.P3271.astype(int).astype(str) == sex)].to_numpy()
            if not len(pool):
                raise ValueError('No hay donantes con la misma zona y sexo; no se relaja este bloqueo.')
        no_education[pos] = ~np.isfinite(ef[pos, 1]) | ~np.isfinite(gf[pool, 1]).any()
        d, ix = buscar_vecinos(gf, ef, pool, pos, k=2)
        tie = np.isfinite(d[:, 1]) & np.isclose(d[:, 0], d[:, 1], rtol=1e-12, atol=1e-12)
        tied[pos] = tie
        # k=2 puede ordenar los empates distinto de k=1: elegir otro índice.
        other = np.where(ix[:, 0] != alternative[pos], ix[:, 0], ix[:, 1])
        alternative[pos[tie]] = other[tie]
    w = e.FEX_C.to_numpy(dtype=float)
    valid_w = np.isfinite(w) & (w > 0)
    pet = e.P6040.ge(15).to_numpy() & valid_w
    base, alt = g.iloc[matched], g.iloc[alternative]
    occupied = base.OCI.eq(1).to_numpy()
    occupied_alt = alt.OCI.eq(1).to_numpy()
    average = lambda x, mask: float(np.average(x[mask], weights=w[mask])) if mask.any() else np.nan
    return dict(anio=int(year), receptores=len(e), empates=int(tied.sum()),
                empates_pct=100*float(tied.mean()),
                empates_ponderados_pct=100*average(tied, valid_w),
                receptores_sin_dimension_educativa=int(no_education.sum()),
                cambios_donante_alternativo=int((alternative != matched).sum()),
                cambios_ocupacion=int((pet & (occupied != occupied_alt)).sum()),
                tasa_ocupacion_actual=100*average(occupied, pet),
                tasa_ocupacion_alternativa=100*average(occupied_alt, pet))
