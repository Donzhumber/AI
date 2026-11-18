/** Prueba de navegador de anotaciones, sin paquetes npm.
 * Desde la raíz: python3 data/preparar_web.py && node data/web/verificar_anotaciones.mjs
 * Requiere Node 22+ y Chrome. CHROME_BIN permite indicar otro ejecutable Chromium.
 * Usa un perfil aislado y archivos temporales. Nunca utiliza cuentas del usuario.
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
import {setTimeout as sleep} from 'node:timers/promises';
const project=process.cwd(), site=path.join(project,'data/_site');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'ai-notas-browser-'));
const downloads=path.join(temp,'downloads');fs.mkdirSync(downloads);
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.geojson':'application/geo+json','.woff':'font/woff'};
const server=http.createServer((req,res)=>{const name=path.resolve(site,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));if(!name.startsWith(site+path.sep)&&name!==site){res.writeHead(403);res.end();return;}let p=name;if(fs.existsSync(p)&&fs.statSync(p).isDirectory())p=path.join(p,'index.html');if(!fs.existsSync(p)){res.writeHead(404);res.end();return;}res.setHeader('Content-Type',mime[path.extname(p)]||'application/octet-stream');fs.createReadStream(p).pipe(res);});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=`http://127.0.0.1:${server.address().port}`;
const chromeBin=process.env.CHROME_BIN||(process.platform==='darwin'?'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome':'google-chrome');
const chrome=spawn(chromeBin,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${path.join(temp,'profile')}`,'about:blank'],{stdio:['ignore','ignore',fs.openSync(path.join(temp,'chrome.log'),'w')]});
let socket;
async function until(fn,timeout=20000){const end=Date.now()+timeout;let error;while(Date.now()<end){try{const value=await fn();if(value)return value;}catch(e){error=e;}await sleep(120);}throw error||new Error('Tiempo de espera agotado');}
try{
 const portFile=path.join(temp,'profile','DevToolsActivePort');await until(()=>fs.existsSync(portFile));const port=fs.readFileSync(portFile,'utf8').split('\n')[0];
 const tab=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
 socket=new WebSocket(tab.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
 let id=0;const pending=new Map();socket.addEventListener('message',event=>{const data=JSON.parse(event.data);if(data.id){const request=pending.get(data.id);pending.delete(data.id);data.error?request.reject(new Error(JSON.stringify(data.error))):request.resolve(data.result);}});
 const send=(method,params={})=>new Promise((resolve,reject)=>{const key=++id;pending.set(key,{resolve,reject});socket.send(JSON.stringify({id:key,method,params}));});
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw new Error(r.exceptionDetails.text+' '+(r.exceptionDetails.exception?.description||''));return r.result.value;};
 await send('Page.enable');await send('Runtime.enable');await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:downloads});
 const ready=()=>until(()=>evaluate('!!document.querySelector("#ia-notas .notas-lanzador")'));
 const go=async page=>{await send('Page.navigate',{url:base+'/'+page});await ready();};
 const reload=async()=>{await send('Page.reload',{ignoreCache:true});await sleep(300);await ready();};
 const click=async text=>{assert(await evaluate(`(()=>{const b=[...document.querySelectorAll('#ia-notas button')].find(b=>b.textContent===${JSON.stringify(text)});if(!b)return false;b.click();return true;})()`),'Botón no encontrado: '+text);};
 const open=()=>evaluate('document.querySelector("#ia-notas .notas-lanzador").click()');
 const type=async value=>evaluate(`(()=>{const i=document.getElementById('ia-notas-comentario');i.value=${JSON.stringify(value)};i.dispatchEvent(new Event('input',{bubbles:true}));})()`);
 const count=()=>evaluate(`JSON.parse(localStorage.getItem('Donzhumber.AI.anotaciones.v1')||' {"notes":[]}').notes.length`);
 const newest=extension=>{const f=fs.readdirSync(downloads).filter(n=>n.endsWith('.'+extension)).map(n=>({p:path.join(downloads,n),m:fs.statSync(path.join(downloads,n)).mtimeMs})).sort((a,b)=>b.m-a.m);return f[0]?.p;};
 const exportFile=async(ext,label)=>{const before=newest(ext);const stamp=before?fs.statSync(before).mtimeMs:0;await click(label);await until(()=>{const n=newest(ext);return n&&fs.statSync(n).mtimeMs>stamp&&!fs.readdirSync(downloads).some(n=>n.endsWith('.crdownload'));});return newest(ext);};
 const importFile=async file=>{const tree=await send('DOM.getDocument');const q=await send('DOM.querySelector',{nodeId:tree.root.nodeId,selector:'#ia-notas input[type=file]'});await send('DOM.setFileInputFiles',{nodeId:q.nodeId,files:[file]});await sleep(250);};
 await go('Principal/principal.html');
 await evaluate(`(()=>{const p=document.querySelector('main section p');const r=document.createRange();r.selectNodeContents(p);const s=window.getSelection();s.removeAllRanges();s.addRange(r);document.dispatchEvent(new Event('selectionchange'));})()`);
 await click('Anotar selección');await type('Precisar el supuesto y contrastar la referencia.');await click('Guardar nota');assert.equal(await count(),1);
 assert(await evaluate(`JSON.parse(localStorage.getItem('Donzhumber.AI.anotaciones.v1')).notes[0].quote.length>20`));
 await reload();await open();assert.equal(await count(),1);await click('Editar');await type('Precisar el supuesto y revisar la referencia en casa.');await click('Guardar nota');assert.equal(await count(),1);
 console.log('OK selección, guardado, recarga y edición');
 await click('Nueva nota');await type('Borrador para revisar al llegar a casa.');await reload();await open();await click('Continuar borrador');assert.equal(await evaluate("document.getElementById('ia-notas-comentario').value"),'Borrador para revisar al llegar a casa.');await click('Guardar nota');assert.equal(await count(),2);
 await exportFile('json','Exportar JSON');const md=await exportFile('md','Descargar texto');assert(fs.readFileSync(md,'utf8').includes('Borrador para revisar'));
 console.log('OK borradores y exportaciones JSON/Markdown');
 await go('Anexo_a/anexo_a.html');await open();assert.equal(await evaluate("document.querySelectorAll('#ia-notas .notas-tarjeta').length"),0);
 await click('Nueva nota');await type('Revisar los errores estándar del anexo.');await click('Guardar nota');assert.equal(await count(),3);
 await evaluate("const f=document.querySelector('#ia-notas select');f.value='all';f.dispatchEvent(new Event('change'))");assert.equal(await evaluate("document.querySelectorAll('#ia-notas .notas-tarjeta').length"),3);
 const exported=await exportFile('json','Exportar JSON');const data=JSON.parse(fs.readFileSync(exported,'utf8'));assert.equal(data.notes.length,3);
 await evaluate("localStorage.removeItem('Donzhumber.AI.anotaciones.v1')");await reload();await open();assert.equal(await count(),0);
 await importFile(exported);await until(async()=>await count()===3);await importFile(exported);assert.equal(await count(),3);
 console.log('OK documentos separados, importación en navegador vacío y deduplicación');
 await evaluate("const f=document.querySelector('#ia-notas select');f.value='all';f.dispatchEvent(new Event('change'))");await click('Eliminar');assert.equal(await count(),2);await click('Deshacer eliminación');assert.equal(await count(),3);
 const hostile={...data,notes:[{...data.notes[0],id:'qa-html',comment:'<img src=x onerror="window.__notesXss=1">',updatedAt:new Date().toISOString()}]};const hostilePath=path.join(temp,'texto-seguro.json');fs.writeFileSync(hostilePath,JSON.stringify(hostile));await importFile(hostilePath);await until(async()=>await count()===4);assert(await evaluate("!document.querySelector('#ia-notas img') && !window.__notesXss"));
 console.log('OK deshacer y texto importado sin ejecución de HTML');
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await sleep(250);const rect=await evaluate("(()=>{const r=document.querySelector('#ia-notas-panel').getBoundingClientRect();return{x:r.x,right:r.right,height:r.height,viewport:visualViewport.width,screenHeight:visualViewport.height,top:r.top,bottom:r.bottom}})()");assert(rect.x>=0&&rect.right<=rect.viewport+1&&rect.height<=rect.screenHeight&&rect.top>=0&&rect.bottom<=rect.screenHeight&&rect.height>100);const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,'notas-movil.png'),Buffer.from(shot.data,'base64'));
 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 await click('Nueva nota');await evaluate("Storage.prototype.setItem=function(){throw new DOMException('quota','QuotaExceededError')}");await type('Nota preservada aunque no haya espacio de almacenamiento.');await click('Guardar nota');assert(await evaluate("document.querySelector('#ia-notas .notas-estado').dataset.error==='true'"));const fallback=await exportFile('json','Exportar JSON');assert.equal(JSON.parse(fs.readFileSync(fallback,'utf8')).notes.length,5);
 console.log('OK diseño móvil y exportación de rescate si falla el almacenamiento');
 await go('Principal/principal.html?notas=1');assert(await evaluate("!document.querySelector('#ia-notas-panel').hidden && document.querySelector('#ia-notas select').value==='all'"));
 await go('Dashboard/dashboard.html');await open();assert(await evaluate("!document.querySelector('#ia-notas-panel').hidden"));
 const result={correcto:true,pruebas:['seleccion','guardado','edicion','persistencia','borradores','exportar_json','exportar_markdown','filtro_documento','importar','deduplicar','deshacer','texto_seguro','movil','fallo_almacenamiento','dashboard','acceso_inicio'],captura:path.join(temp,'notas-movil.png'),carpeta:temp};fs.writeFileSync(path.join(temp,'resultado.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
}finally{socket?.close();chrome.kill('SIGTERM');server.close();}
