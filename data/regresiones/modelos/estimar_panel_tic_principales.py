"""Reestima las tres especificaciones FE principales de la sección 4.6."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from pathlib import Path
import sys
import pandas as pd

ROOT = (Path(__file__).resolve().parents[2] / 'regresiones/modelos')
sys.path.insert(0,str((Path(__file__).resolve().parents[2])))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import PANEL_TIC_DTA
sys.path.append("/Applications/Stata/utilities")
from pystata import config
config.init("be")
from pystata import stata
from sfi import Matrix, Scalar


def main():
    stata.run(f'''
    use "{PANEL_TIC_DTA}", clear
    generate departamento = real(substr(id_cohorte, 1, strpos(id_cohorte, "_") - 1))
    xtset coh anio
    ''', quietly=True)
    rows = []
    for outcome, label in [("y_sal", "salario"), ("y_des", "desempleo"),
                           ("y_inf", "no_cotizacion")]:
        stata.run(
            f"quietly xtreg {outcome} x_tic c_edad c_rural c_edu c_hogar c_jefe i.anio, fe vce(cluster departamento)",
            quietly=True)
        names = Matrix.getColNames("r(table)")
        table = Matrix.get("r(table)")
        j = names.index("x_tic")
        stata.run(f'''
        quietly xtreg {outcome} x_tic c_edad c_rural c_edu c_hogar c_jefe i.anio, fe
        estimates store fe_simple
        scalar f_efectos=e(F_f)
        scalar p_f_efectos=Ftail(e(df_a),e(df_r),e(F_f))
        quietly xtreg {outcome} x_tic c_edad c_rural c_edu c_hogar c_jefe i.anio, re
        estimates store re_simple
        quietly hausman fe_simple re_simple
        ''', quietly=True)
        rows.append({"resultado": label, "coef": table[0][j], "se": table[1][j],
                     "p": table[3][j], "N": Scalar.getValue("e(N)"),
                     "cohortes": Scalar.getValue("e(N_g)"), "clusters_departamento": 33,
                     "f_efectos_cohorte": Scalar.getValue("f_efectos"),
                     "p_f_efectos_cohorte": Scalar.getValue("p_f_efectos"),
                     "hausman_chi2": Scalar.getValue("r(chi2)"),
                     "hausman_p": Scalar.getValue("r(p)")})
    result = pd.DataFrame(rows)
    result.to_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/panel_tic_principales_reconstruido.csv'), index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
