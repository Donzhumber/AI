/* Nombres compactos de presentación; el catálogo y los globos conservan el original. */
(() => {
  const nombres = new Map();
  const abreviar = nombre => {
    if (typeof window.dashboardNombreOcupacionCorto === 'function') {
      return window.dashboardNombreOcupacionCorto(nombre);
    }
    let texto = nombre.replace(/\s+/g, ' ').trim()
      .replace(/,?\s+y afines\b/gi, '')
      .replace(/\s+no clasificados en otros grupos\b/gi, '')
      .replace(/\s+no clasificados bajo otros epígrafes\b/gi, '');
    if (texto.length > 54) {
      const corte = texto.lastIndexOf(' ', 51);
      texto = texto.slice(0, corte > 20 ? corte : 51) + '…';
    }
    return texto;
  };
  const recoger = valor => {
    if (!valor || typeof valor !== 'object') return;
    if (typeof valor.ciuo08_desc === 'string') {
      const original = valor.ciuo08_desc;
      nombres.set(original, abreviar(original));
    }
    for (const hijo of Object.values(valor)) if (typeof hijo === 'object') recoger(hijo);
  };
  let pendiente = false;
  const aplicar = () => {
    pendiente = false;
    const raiz = document.getElementById('ia-impacto');
    if (!raiz) return;
    for (const elemento of raiz.querySelectorAll('.exposure-card details div, svg text')) {
      if (elemento.closest('[aria-label="tip"], .plot-tip, .observablehq--inspect')) continue;
      if (elemento.dataset.ocupacionCompleta) continue;
      const texto = elemento.textContent.trim();
      const separador = texto.lastIndexOf(' · ');
      const nombre = nombres.has(texto) ? texto : separador >= 0 ? texto.slice(0, separador) : '';
      const corto = nombres.get(nombre);
      if (!corto || corto === nombre || elemento.children.length) continue;
      elemento.dataset.ocupacionCompleta = nombre;
      elemento.setAttribute('title', nombre);
      elemento.setAttribute('aria-label', texto);
      elemento.textContent = corto + texto.slice(nombre.length);
    }
  };
  const iniciar = async () => {
    const respuesta = await fetch('data/cuadrantes_anexo.json');
    if (!respuesta.ok) throw new Error('No se pudo cargar el catálogo de nombres');
    recoger(await respuesta.json());
    aplicar();
    new MutationObserver(() => {
      if (!pendiente) { pendiente = true; requestAnimationFrame(aplicar); }
    }).observe(document.getElementById('ia-impacto') || document.body, {childList: true, subtree: true});
  };
  const arrancar = () => iniciar().catch(error => console.error('Nombres de ocupación', error));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar);
  else arrancar();
})();
