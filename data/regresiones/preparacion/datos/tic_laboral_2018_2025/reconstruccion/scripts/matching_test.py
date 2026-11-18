"""Pruebas sintéticas; no ejecuta imputaciones productivas."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[6]))
import unittest
import numpy as np
import pandas as pd
from matching_anexo import select_donors


class MatchingTest(unittest.TestCase):
    def setUp(self):
        self.g = pd.DataFrame(dict(DPTO=[5, 5], CLASE=[1, 1], P3271=[1, 1],
            P6040=[30, 50], P6050=[1, 1], DIRECTORIO=[1, 2],
            SECUENCIA_P=[1, 1], P6240=[1, 1], EDUCACION_ARM_GEIH=[2., 4.]))
        self.e = pd.DataFrame(dict(P1_DEPARTAMENTO=[5], CLASE=[1], P6020=[1],
            P6040=[31], P6051=[1], CANT_PERSONAS_HOGAR=[1], P6240=[1],
            P8586=[2], P8587=[4], P1088=[np.nan], P1088S1=[np.nan], P6216=[10]))

    def test_nearest(self):
        idx, fallback = select_donors(self.g, self.e)
        self.assertEqual(idx.tolist(), [0])
        self.assertEqual(fallback.tolist(), [False])

    def test_education_missing_omits_dimension(self):
        self.e["P8587"] = np.nan
        idx, _ = select_donors(self.g, self.e)
        self.assertEqual(idx.tolist(), [0])

    def test_missing_age_stops(self):
        self.e["P6040"] = np.nan
        with self.assertRaises(ValueError):
            select_donors(self.g, self.e)

    def test_adult_activity_missing_stops(self):
        self.e["P6240"] = np.nan
        with self.assertRaises(ValueError):
            select_donors(self.g, self.e, activity_structural_under=12)

    def test_territorial_fallback_preserves_sex_zone(self):
        self.e["P1_DEPARTAMENTO"] = 11
        idx, fallback = select_donors(self.g, self.e)
        self.assertEqual(idx.tolist(), [0])
        self.assertEqual(fallback.tolist(), [True])


if __name__ == "__main__":
    unittest.main()
