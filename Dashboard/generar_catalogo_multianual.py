
# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'data'))
from pathlib import Path
import pandas as pd
import numpy as np
import json
import sys
import hashlib

BASE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[1] / 'data'
sys.path.insert(0, str(ROOT))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import MICRODATOS, INDICES
from regresiones.preparacion.datos.exposicion_ia.indices_comunes import ocupacion_analitica
OUTPUT = (ROOT / 'datos/publicacion/dashboard/catalogo_ocupaciones_multianual.json')

CIUO_TITLES = {
    # Grupo 1: Directores y Gerentes
    1111: ("Legisladores y congresistas", "senador, representante, congreso, diputado, concejal, político"),
    1112: ("Directores y altos funcionarios de la administración pública", "ministro, viceministro, secretario de despacho, director de entidad, alcalde, gobernador"),
    1114: ("Dirigentes de organizaciones políticas y de interés", "dirigente social, sindicato, gremio, ong, partido político"),
    1120: ("Directores generales y gerentes ejecutivos (CEO)", "presidente ejecutivo, gerente general, director ejecutivo, ceo, socio director"),
    1211: ("Directores de finanzas y tesorería", "gerente financiero, director financiero, cfo, tesorero, contralor"),
    1212: ("Directores de recursos humanos y talento", "gerente de rrhh, gestión humana, talento humano, director de personal"),
    1213: ("Directores de políticas y planificación estratégica", "gerente de planeación, estrategia, desarrollo organizacional"),
    1219: ("Directores de servicios administrativos no clasificados", "gerente administrativo, director administrativo, servicios generales"),
    1221: ("Directores de ventas y comercialización", "gerente comercial, director comercial, gerente de ventas"),
    1222: ("Directores de publicidad y relaciones públicas", "gerente de mercadeo, cmo, director de marketing, publicidad, rrpp"),
    1223: ("Directores de investigación y desarrollo (I+D)", "gerente de i+d, director científico, director de innovación"),
    1311: ("Directores de producción agropecuaria y pesquera", "administrador de finca, gerente agrícola, gerente ganadero"),
    1321: ("Directores de industrias manufactureras", "gerente de planta, director de producción, jefe de fábrica"),
    1323: ("Directores de construcción y obras civiles", "director de obra, gerente de proyectos de construcción, constructor"),
    1324: ("Directores de logística y suministros", "gerente de logística, cadena de suministros, supply chain, transporte"),
    1330: ("Directores de tecnologías de la información y comunicación (CTO/CIO)", "gerente de ti, director de tecnología, sistemas, cto, cio"),
    1341: ("Directores de servicios de cuidado infantil", "director de guardería, jardín infantil, centro de desarrollo"),
    1342: ("Directores de servicios de salud y clínicas", "director médico, gerente de hospital, director de clínica, eps, ips"),
    1345: ("Directores de servicios de educación, decanos y directores de programa", "decano, director de programa, rector de universidad, vicerrector, director de colegio, jefe de departamento académico"),
    1346: ("Directores de sucursales financieras y de seguros", "gerente de banco, gerente de sucursal bancaria, director de oficina de seguros"),
    1411: ("Gerentes de hoteles y alojamientos", "gerente de hotel, hostal, administrador hotelero"),
    1412: ("Gerentes de restaurantes y bares", "administrador de restaurante, gerente de alimentos y bebidas, bar"),
    1420: ("Gerentes y administradores de comercio al por menor y mayor", "administrador de tienda, almacén, supermercado, comercio, jefe de ventas"),
    1431: ("Gerentes de centros deportivos y de recreación", "administrador de gimnasio, club deportivo, recreación"),
    1439: ("Otros gerentes de servicios no clasificados", "gerente de servicios, administrador de empresa de servicios"),

    # Grupo 2: Profesionales, Científicos e Intelectuales
    2111: ("Físicos y astrónomos", "físico, astrónomo, investigación física"),
    2112: ("Meteorólogos", "meteorólogo, clima, ciencias atmosféricas"),
    2113: ("Químicos", "químico, químico farmacéutico, laboratorio químico"),
    2114: ("Geólogos y geofísicos", "geólogo, minería, petróleo, hidrocarburos, sismólogo"),
    2120: ("Matemáticos, actuarios y estadísticos", "matemático, estadístico, actuario, analista de datos cuánticos"),
    2131: ("Biólogos, botánicos y zoólogos", "biólogo, microbiólogo, botánico, ecólogo"),
    2132: ("Agrónomos, forestales y zootecnistas", "ingeniero agrónomo, zootecnista, ingeniero forestal"),
    2141: ("Ingenieros industriales y de producción", "ingeniero industrial, procesos, mejora continua, calidad, operaciones"),
    2142: ("Ingenieros civiles y de obras", "ingeniero civil, calculista, estructuras, vías, transporte"),
    2143: ("Ingenieros ambientales", "ingeniero ambiental, saneamiento, sostenibilidad, impacto ambiental"),
    2144: ("Ingenieros mecánicos", "ingeniero mecánico, diseño mecánico, climatización, automotriz"),
    2145: ("Ingenieros químicos", "ingeniero químico, procesos químicos, refinación, polímeros"),
    2146: ("Ingenieros de minas y metalurgia", "ingeniero de minas, metalúrgico, extracción mineral"),
    2151: ("Ingenieros electricistas", "ingeniero electricista, redes eléctricas, alta tensión, energía"),
    2152: ("Ingenieros electrónicos", "ingeniero electrónico, hardware, microcontroladores, automatización industrial"),
    2153: ("Ingenieros de telecomunicaciones", "ingeniero de telecomunicaciones, redes, telefonía, fibra óptica, 5g"),
    2161: ("Arquitectos de edificaciones", "arquitecto, diseño arquitectónico, urbanismo"),
    2164: ("Diseñadores urbanistas y viales", "urbanista, planificador urbano, movilidad"),
    2211: ("Médicos generales", "médico general, médico de urgencias, consulta médica"),
    2212: ("Médicos especialistas y cirujanos", "médico especialista, cirujano, pediatra, cardiólogo, ginecólogo, anestesiólogo, oncólogo"),
    2221: ("Profesionales de enfermería", "enfermero jefe, enfermera profesional, enfermería clínica"),
    2230: ("Veterinarios y médicos de animales", "médico veterinario, veterinaria, clínica de animales"),
    2261: ("Odontólogos y dentistas", "odontólogo, dentista, ortodoncista, cirujano maxilofacial"),
    2262: ("Farmacéuticos", "farmacéutico, químico farmacéutico, regente de farmacia hospitalaria"),
    2263: ("Profesionales de salud ocupacional y ergonomía", "seguridad y salud en el trabajo, sst, salud ocupacional"),
    2264: ("Fisioterapeutas y terapeutas físicos", "fisioterapeuta, terapia física, rehabilitación"),
    2265: ("Dietistas y nutricionistas", "nutricionista, dietista, alimentación clínica"),
    2269: ("Otros profesionales de la salud", "fonoaudiólogo, terapeuta ocupacional, optometrista"),
    2310: ("Profesores de universidades y educación superior", "profesor universitario, docente universitario, catedrático, investigador académico"),
    2320: ("Profesores de formación técnica y tecnológica", "instructor de sena, docente técnico, formación profesional"),
    2330: ("Profesores de educación secundaria y media", "profesor de bachillerato, docente de secundaria, profesor de matemáticas, historia, ciencias"),
    2341: ("Profesores de educación primaria", "profesor de primaria, docente escolar, maestro de escuela"),
    2342: ("Profesores de educación preescolar e infantil", "profesora de preescolar, educación inicial, parvularia"),
    2351: ("Especialistas en métodos pedagógicos y currículo", "pedagogo, asesor curricular, diseño educativo"),
    2352: ("Profesores de educación especial", "docente de educación especial, inclusión educativa"),
    2411: ("Contadores públicos y auditores", "contador público, contador, revisor fiscal, auditor financiero"),
    2412: ("Asesores financieros y de inversiones", "analista financiero, asesor de inversiones, banca de inversión, riesgos"),
    2413: ("Analistas de mercados y finanzas", "analista bursátil, analista de mercado, research financiero"),
    2421: ("Analistas de gestión y organización", "consultor de empresas, consultor de gestión, analista de procesos"),
    2422: ("Especialistas en políticas públicas", "analista de políticas públicas, formulador de proyectos, asesor estatal"),
    2431: ("Especialistas en publicidad y mercadeo", "profesional de mercadeo, estratega digital, copywriter publicitario"),
    2432: ("Profesionales de relaciones públicas", "comunicador corporativo, jefe de prensa, vocero, relaciones públicas"),
    2511: ("Analistas de sistemas informáticos", "analista de sistemas, arquitecto de software, requerimientos de software"),
    2512: ("Desarrolladores de software y programadores", "desarrollador de software, programador, ingeniero de software, developer, backend, frontend, fullstack, python, java, react"),
    2513: ("Desarrolladores web y multimedia", "diseñador web, desarrollador web, frontend dev, multimedia"),
    2514: ("Programadores de aplicaciones móviles", "programador de apps, desarrollador móvil, android, ios, flutter"),
    2519: ("Otros desarrolladores y analistas de software", "devops, qa tester, ingeniero de calidad de software, cloud engineer"),
    2521: ("Diseñadores y administradores de bases de datos", "administrador de bases de datos, dba, data engineer, sql"),
    2522: ("Administradores de sistemas y redes", "administrador de servidores, sysadmin, ingeniero de redes, soporte nivel 3"),
    2523: ("Profesionales en ciberseguridad y redes", "especialista en ciberseguridad, seguridad de la información, ethical hacker"),
    2529: ("Científicos de datos y especialistas en IA", "científico de datos, data scientist, machine learning engineer, analista de ia"),
    2611: ("Abogados y juristas", "abogado, jurista, litigante, asesor jurídico, derecho penal, laboral, civil"),
    2612: ("Jueces y magistrados", "juez, magistrado, fiscal, tribunal judicial"),
    2621: ("Archivistas y curadores de museos", "archivista, curador de arte, bibliotecólogo"),
    2631: ("Economistas", "economista, analista económico, macroeconomista, econometría"),
    2632: ("Sociólogos, antropólogos y arqueólogos", "sociólogo, antropólogo, arqueólogo, investigador social"),
    2634: ("Psicólogos", "psicólogo, psicólogo clínico, psicólogo organizacional"),
    2635: ("Trabajadores sociales", "trabajador social, gestor social, desarrollo comunitario"),
    2641: ("Escritores y autores", "escritor, autor, redactor editorial, novelista"),
    2642: ("Periodistas y reporteros", "periodista, comunicador social, reportero, presentador de noticias, redactor"),
    2651: ("Artistas plásticos y visuales", "artista plástico, pintor, escultor, ilustrador"),
    2652: ("Músicos, cantantes y compositores", "músico, cantante, compositor, productor musical"),
    2654: ("Directores de cine, teatro y televisión", "director de cine, productor audiovisual, televisión"),
    2655: ("Actores", "actor, actriz, teatro, televisión"),

    # Grupo 3: Técnicos y Profesionales de Nivel Medio
    3112: ("Técnicos en ingeniería civil y topografía", "topógrafo, técnico en construcción, inspector de obra"),
    3113: ("Técnicos en electricidad", "técnico electricista, técnico de subestaciones, instalador eléctrico certificado"),
    3114: ("Técnicos en electrónica", "técnico electrónico, reparación de circuitos, mantenimiento electrónico"),
    3115: ("Técnicos en mecánica industrial y automotriz", "técnico mecánico, mantenimiento industrial, técnico diesel"),
    3119: ("Otros técnicos en ciencias físicas y químicas", "técnico de laboratorio químico, analista de calidad industrial"),
    3121: ("Supervisores de minería y canteras", "supervisor minero, jefe de cuadrilla minera"),
    3122: ("Supervisores de producción manufacturera", "supervisor de producción, jefe de turno, líder de línea industrial"),
    3123: ("Supervisores de construcción y obras", "maestro de obra, supervisor de construcción, jefe de cuadrilla civil"),
    3131: ("Operadores de plantas de energía", "operador de planta eléctrica, hidroeléctrica, termoeléctrica"),
    3132: ("Operadores de plantas de tratamiento de agua", "operador de acueducto, planta de agua potable, ptarm"),
    3211: ("Técnicos en radiología y equipos médicos", "técnico en radiología, tecnólogo en imágenes diagnósticas, tomografía"),
    3212: ("Técnicos de laboratorio médico y clínico", "técnico de laboratorio clínico, bacteriólogo técnico, toma de muestras"),
    3213: ("Técnicos en farmacia", "regente de farmacia, técnico auxiliar de droguería, farmacia"),
    3221: ("Técnicos de enfermería y auxiliares", "auxiliar de enfermería, técnico en enfermería, enfermero asistente"),
    3251: ("Higienistas y técnicos dentales", "mecánico dental, técnico en prótesis dental, higienista dental"),
    3311: ("Agentes de bolsa y operadores financieros", "corredor de bolsa, operador de divisas, trader"),
    3312: ("Oficiales de préstamos y crédito", "analista de crédito, oficial de microcrédito, asesor de préstamos"),
    3313: ("Asistentes contables y de auditoría", "asistente contable, auxiliar contable, auxiliar de auditoría, causador"),
    3314: ("Asistentes de estadística y matemáticas", "asistente estadístico, digitador analítico, encuestador jefe"),
    3321: ("Agentes y corredores de seguros", "asesor de seguros, corredor de pólizas, agente de seguros"),
    3322: ("Representantes comerciales y ejecutivos de cuenta", "ejecutivo de cuenta, asesor comercial corporativo, vendedor b2b"),
    3323: ("Agentes de compras y adquisiciones", "comprador, auxiliar de compras, adquisiciones"),
    3331: ("Agentes de aduanas y comercio exterior", "agente aduanero, tramitador de importaciones, comercio exterior"),
    3332: ("Organizadores de eventos y conferencias", "organizador de bodas, eventos corporativos, ferias"),
    3334: ("Agentes inmobiliarios y de bienes raíces", "asesor inmobiliario, corredor de finca raíz, agente de bienes raíces"),
    3341: ("Supervisores de oficina y secretariado", "supervisor de oficina, jefe de secretaría, coordinador administrativo"),
    3343: ("Secretarios ejecutivos y asistentes de gerencia", "secretaria de gerencia, asistente ejecutiva, asistente de dirección"),
    3411: ("Asistentes jurídicos y paralegales", "paralegal, auxiliar judicial, asistente de abogado, tramitador legal"),
    3422: ("Entrenadores deportivos y de acondicionamiento", "entrenador personal, preparador físico, instructor de gimnasio"),
    3431: ("Fotógrafos y camarógrafos", "fotógrafo, camarógrafo de video, editor audiovisual"),
    3432: ("Diseñadores gráficos y decoradores de interiores", "diseñador gráfico, diseñador de interiores, ilustrador digital"),
    3434: ("Chefs y cocineros de alta cocina", "chef ejecutivo, sous chef, chef de restaurante"),
    3511: ("Técnicos de soporte informático y mesa de ayuda", "técnico de soporte, mesa de ayuda, help desk, mantenimiento de computadores"),
    3512: ("Técnicos en gestión de redes y telecomunicaciones", "técnico de redes, soporte de cableado estructurado, wifi, router"),
    3513: ("Técnicos en transmisión de radio y televisión", "técnico de sonido, audio, televisión, transmisión"),

    # Grupo 4: Personal de Apoyo Administrativo (Incluye Call Centers)
    4110: ("Oficinistas generales y secretarios administrativos", "oficinista, auxiliar de oficina, asistente administrativo general"),
    4120: ("Secretarios y recepcionistas administrativos", "secretaria, recepcionista, atención en recepción, conmutador"),
    4131: ("Mecanógrafos y operadores de procesamiento de texto", "mecanógrafo, transcriptora, transcriptor de audio"),
    4132: ("Digitadores de datos y captura de información", "digitador, capturista de datos, ingreso de información"),
    4211: ("Cajeros de banco y ventanilla bancaria", "cajero de banco, asesor de ventanilla bancaria, recaudador de banco"),
    4212: ("Receptores de apuestas y juegos de azar", "cajero de apuestas, loterías, chances, casino"),
    4213: ("Prestamistas de empeño y casas de empeño", "empleado de compraventa, casa de empeño"),
    4214: ("Cobradores y cobro de cartera", "asesor de cobranzas, cobrador de cartera, gestor de cobro"),
    4221: ("Empleados de agencias de viajes y turismo", "asesor de viajes, agente de viajes, reservas de turismo"),
    4222: ("Operadores de Call Center, telemercadeo y atención telefónica", "agente de call center, contact center, televentas, asesor telefónico, bpo, teleoperador"),
    4223: ("Operadores de central telefónica", "telefonista, conmutador central, operadora de llamadas"),
    4224: ("Recepcionistas de hotel", "recepcionista de hotel, check-in, conserje de recepción"),
    4225: ("Empleados de información y orientación", "informador de centro comercial, orientador de usuarios, taquillero"),
    4226: ("Recepcionistas generales (médicos y consultorios)", "recepcionista de consultorio, citas médicas, admisiones de clínica"),
    4227: ("Entrevistadores y encuestadores de opinión", "encuestador, entrevistador de campo, censo"),
    4311: ("Auxiliares de contabilidad y cálculo de nómina", "auxiliar de contabilidad, nómina, facturación, liquidación"),
    4312: ("Auxiliares de estadística y finanzas", "asistente de finanzas, auxiliar de tesorería"),
    4313: ("Auxiliares de nómina y liquidación salarial", "liquidador de nómina, auxiliar de recursos humanos administrativo"),
    4321: ("Auxiliares de almacén, inventarios y bodegaje", "auxiliar de bodega, control de inventarios, auxiliar de almacén"),
    4322: ("Auxiliares de transporte y despacho de carga", "auxiliar de despacho, despachador de carga, logística de envío"),
    4323: ("Controladores de tráfico y transporte terrestre", "despachador de buses, controlador de flota, transporte urbano"),
    4411: ("Empleados de archivo y correspondencia", "archivista de oficina, auxiliar de archivo, correspondencia"),
    4412: ("Carteros y mensajeros postales", "cartero, mensajero de correo, repartidor postal"),

    # Grupo 5: Trabajadores de Servicios y Vendedores (Presenciales)
    5111: ("Auxiliares de vuelo y azafatas", "azafata, auxiliar de vuelo, tripulante de cabina"),
    5112: ("Revisores y conductores de transporte público de pasajeros", "revisor de tiquetes, conductor de buseta, chofer de colectivo"),
    5113: ("Guías turísticos", "guía de turismo, ecoturismo, guía histórico"),
    5120: ("Cocineros y parrilleros de restaurantes", "cocinero, cocinera, parrillero, ayudante de cocina, chef de restaurante"),
    5131: ("Meseros, camareros y capitanes de servicio", "mesero, camarero, mesera, capitán de meseros, bartender"),
    5132: ("Barmans y preparadores de bebidas", "barman, bartender, barista de café"),
    5141: ("Peluqueros, barberos y estilistas", "peluquero, barbero, estilista, peluquería, corte de pelo"),
    5142: ("Esteticistas y cosmetólogos", "esteticista, manicurista, pedicurista, spa, masajista"),
    5151: ("Supervisores de limpieza en hoteles y oficinas", "gobernanta de hotel, supervisor de aseo, ama de llaves"),
    5153: ("Conserjes y mayordomos de edificios", "conserje, portero de edificio, mayordomo de finca"),
    5161: ("Trabajadores de pompas fúnebres y funerarias", "embalsamador, empleado de funeraria, tanatopraxia"),
    5162: ("Cuidadores de mascotas y peluqueros caninos", "paseador de perros, peluquero canino, adiestrador"),
    5163: ("Instructores de conducción de vehículos", "profesor de conducción, instructor de manejo"),
    5211: ("Vendedores ambulantes de alimentos y bebidas", "vendedor ambulante de café, empanadas, comida callejera"),
    5212: ("Vendedores de quioscos, casetas y puestos de mercado", "vendedor de plaza de mercado, quiosco, puesto de dulces"),
    5221: ("Comerciantes y tenderos de barrio", "tendero, administrador de tienda de barrio, micromercado"),
    5222: ("Supervisores de almacén y tienda retail", "jefe de pasillo, supervisor de supermercado, retail"),
    5223: ("Vendedores de almacenes, tiendas y mostrador (Retail presencial)", "vendedor de ropa, calzado, tecnología, mostrador, almacén, dependiente"),
    5230: ("Cajeros de comercio, supermercado y autoservicio", "cajero de supermercado, cajera de almacén, punto de pago"),
    5241: ("Modelos de modas y maniquíes", "modelo de pasarela, modelo publicitario, anfitriona"),
    5242: ("Demostradores e impulsadores de productos", "impulsadora de supermercado, demostrador de marca, degustador"),
    5244: ("Vendedores independientes por teléfono (Telemercadeo)", "vendedor telefónico informal, telemarketing independiente"),
    5245: ("Despachadores de estaciones de gasolina y combustible", "islero, despachador de gasolina, bombero de estación de servicio"),
    5246: ("Vendedores de comida en mostrador y autoservicio", "atención en mostrador de comidas rápidas, cafetería"),
    5311: ("Cuidadores de niños y niñeras", "niñera, cuidadora de niños, niñero, baby sitter"),
    5321: ("Auxiliares de cuidados personales en salud y clínicas", "auxiliar de enfermería de planta, cuidado geriátrico institucional"),
    5322: ("Cuidadores a domicilio de enfermos y ancianos", "cuidador de ancianos, cuidado a domicilio, enfermera de casa"),
    5411: ("Bomberos y rescatistas", "bombero, rescatista de emergencias, socorrista"),
    5414: ("Guardas de seguridad, celadores y vigilantes", "guarda de seguridad, vigilante privado, celador, seguridad privada"),

    # Grupo 6: Trabajadores Calificados Agropecuarios
    6111: ("Agricultores de cultivos transitorios (café, cereales, flores)", "cafetero, cultivador de café, arroz, maíz, flores, hortalizas"),
    6112: ("Agricultores de árboles y arbustos frutales", "cultivador de frutas, cítricos, aguacate, plátano, palma"),
    6121: ("Criadores y trabajadores de ganado vacuno y lechero", "ganadero, ordeñador, vaquero, cuidado de ganado lechero"),
    6122: ("Criadores y trabajadores avícolas (pollos y huevos)", "avicultor, galponero, trabajador de granja avícola"),
    6123: ("Criadores y cuidadores de cerdos y porcinos", "porcicultor, trabajador de granja porcina"),
    6210: ("Trabajadores de subsistencia agrícola y pecuaria", "campesino de subsistencia, huerta familiar"),
    6310: ("Pescadores artesanales y acuicultores", "pescador, acuicultor, piscícola, cultivo de trucha y tilapia"),

    # Grupo 7: Oficiales, Operarios y Artesanos
    7111: ("Albañiles y constructores de mampostería", "albañil, maestro albañil, mampostería, pañetador, pegador de ladrillo"),
    7112: ("Operarios de concreto armado y encofradores", "encofrador, fundidor de concreto, armado de vigas"),
    7115: ("Carpinteros de obra y armadores", "carpintero de obra, instalación de techos, formaleta"),
    7121: ("Techadores e instaladores de cubiertas", "techador, colocador de tejas, impermeabilización"),
    7122: ("Enchapadores, colocadores de baldosas y azulejos", "enchapador, pegador de baldosa, cerámica, porcelanato"),
    7123: ("Yeseros, revocadores y frisadores", "yesero, drywall, estucador, frisador"),
    7124: ("Instaladores de material aislante e insonorización", "instalador de aislamiento térmico, acústico"),
    7126: ("Fontaneros, plomeros e instaladores de tuberías", "plomero, fontanero, gasista, instalación de tuberías"),
    7131: ("Pintores y empapeladores de edificaciones", "pintor de casas, pintor de interiores, brocha gorda"),
    7212: ("Soldadores y oxicortadores", "soldador, soldadura eléctrica, tig, mig, oxicorte"),
    7213: ("Caldereros y chapistas de metal", "pailero, calderero, ornamentador, doblador de lámina"),
    7222: ("Cerrajeros y fabricantes de herramientas", "cerrajero, fabricación de llaves, candados"),
    7231: ("Mecánicos y reparadores de vehículos automotores", "mecánico automotriz, mecánico de carros, taller mecánico"),
    7233: ("Mecánicos de maquinaria agrícola e industrial", "mecánico industrial, mecánico de tractores, maquinaria pesada"),
    7411: ("Electricistas de la construcción y afines", "electricista residencial, electricista instalador, redes domiciliarias"),
    7412: ("Mecánicos electricistas y reparadores de motores", "bobinador de motores, electromecánico, alternadores"),
    7421: ("Técnicos de reparación de electrodomésticos y electrónicos", "reparador de televisores, lavadoras, neveras, celulares"),
    7511: ("Carniceros, pescaderos y charcuteros", "carnicero, despostador de carne, pescadero"),
    7512: ("Panaderos, pasteleros y confiteros", "panadero, pastelero, panadería, repostería"),
    7531: ("Sastres, modistos y confeccionistas a medida", "sastre, modista, costurera, confección a medida"),
    7533: ("Costureros y bordadores", "costurero de confección, operario de confección, rematador"),
    7543: ("Inspectores de calidad en manufactura artesanal", "control de calidad de confección, calzado, artesanías"),

    # Grupo 8: Operadores de Instalaciones y Máquinas
    8111: ("Mineros y operadores de perforación de pozos", "minero de carbón, operador de taladro de petróleo, perforador"),
    8141: ("Operadores de máquinas de procesamiento de madera", "aserrador, operador de sierra industrial, cepilladora"),
    8152: ("Operadores de máquinas de tejer y tejedores", "operador de telar, tejeduría industrial"),
    8183: ("Operadores de máquinas de embalaje y etiquetado", "empacador de máquina, etiquetador industrial"),
    8311: ("Maquinistas de trenes y ferrocarriles", "maquinista de tren, operador ferroviario"),
    8321: ("Conductores de motocicletas y mototaxis", "mototaxista, mensajero en moto, repartidor en motocicleta"),
    8322: ("Conductores de taxis, camionetas y automóviles", "taxista, conductor de taxi, conductor de uber/plataformas, chofer"),
    8323: ("Conductores de microbuses y furgonetas", "conductor de microbús, van, furgón de reparto"),
    8331: ("Conductores de autobuses urbanos y tranvías", "conductor de bus, transmilenio, sitp, bus intermunicipal"),
    8332: ("Conductores de camiones pesados y tractomulas", "camionero, conductor de tractomula, chofer de tractocamión, volqueta"),
    8341: ("Operadores de maquinaria agrícola móvil (tractores)", "tractorista, operador de cosechadora"),
    8342: ("Operadores de maquinaria pesada de movimiento de tierras", "operador de retroexcavadora, motoniveladora, buldócer, pala mecánica"),
    8343: ("Operadores de grúas y montacargas", "operador de montacargas, operador de grúa torre, telehandler"),

    # Grupo 9: Ocupaciones Elementales
    9111: ("Empleadas domésticas y limpiadores de casas", "empleada doméstica, trabajadora del hogar, aseadora de casas, limpieza de hogar"),
    9112: ("Limpiadores de oficinas, hoteles y establecimientos", "aseador de oficinas, conserje de aseo, camarera de hotel, todoterreno"),
    9121: ("Lavadores de ropa a mano y planchadores", "lavandera, planchadora, lavador de ropa"),
    9122: ("Lavadores de vehículos y automóviles", "lavador de carros, lavadero de autos, lavacoches"),
    9123: ("Limpiadores de ventanas y vidrios de alturas", "limpiavidrios, limpieza de fachadas en alturas"),
    9211: ("Jornaleros y peones agrícolas (cultivos)", "jornalero, peón agrícola, cogedor de café, recolector de fruta, machetero"),
    9212: ("Jornaleros y peones ganaderos", "peón de ganado, ordeñador manual, corralero"),
    9312: ("Peones de obras públicas y mantenimiento de vías", "obrero de vías, peón de carretera, reparador de pavimento"),
    9313: ("Peones de la construcción y obreros de edificación", "ayudante de construcción, peón de albañil, obrero de obra, bultista"),
    9329: ("Peones de manufactura y fábricas", "ayudante de planta, ayudante de producción, empaquetador manual"),
    9333: ("Cargadores de bultos y coteros", "cotero, cargador de bultos, descargador de camiones, bracero"),
    9411: ("Ayudantes y auxiliares de cocina rápida", "ayudante de cocina rápida, pelador de papas, lavaplatos"),
    9412: ("Lavadores de platos y vajilla", "lavaplatos, auxiliar de lavado, steward"),
    9510: ("Vendedores ambulantes de mercancías y artículos varios", "vendedor ambulante, buhonero, vendedor de buses, comercio informal"),
    9611: ("Recolectores de basura y desechos reciclables", "recolector de basura, reciclador de oficio, recuperador ambiental"),
    9612: ("Clasificadores de desechos en rellenos y reciclaje", "clasificador de reciclaje, seleccionador de residuos"),
    9613: ("Barrenderos de calles y espacios públicos", "barrendero, aseador de calles, escobita"),
    9622: ("Personas que realizan mandados y diligencias (mandaderos)", "mandadero, mensajero a pie, tramitador"),
}

NOMBRES_GRUPOS = [
    "Fuerzas armadas", "Dirección y gerencia", "Profesionales", "Técnicos",
    "Apoyo administrativo", "Servicios y ventas", "Agropecuarios",
    "Oficios y artesanías", "Operadores y conductores", "Ocupaciones elementales"
]

# Alias de presentación para las vistas históricas del tablero. Sus percentiles
# se expresan en 0–100 multiplicando por cien el catálogo fijo 0–1 del Anexo.
# No se ponderan, recalculan ni normalizan por año.
ALIASES = {
    "exp_aioe": ("AIOE", "aioe_pct", "AIOE"),
    "exp_webb_ia": ("ai_score", "webb_ia_pct", "IA de Webb"),
    "exp_gpt4_beta": ("dv_rating_beta", "llm_pct", "Modelos de lenguaje"),
    "exp_webb_software": ("software_score", "software_pct", "Software de Webb"),
    "exp_webb_robot": ("robot_score", "robots_pct", "Robots de Webb"),
}
INDICADORES_X = [{"id": alias+"_pct", "nombre": label+" · percentil fijo", "descripcion": "Percentil del catálogo ocupacional fijo del Anexo, mostrado en escala 0–100; no probabilidad de automatización.", "recomendado": alias=="exp_webb_robot"} for alias, (_, _, label) in ALIASES.items()]
INDICADORES_Y = [dict(item, recomendado=item["id"]=="exp_aioe_pct") for item in INDICADORES_X]
INDICES_COLS_RAW = list(ALIASES)
INDICES_COLS_PCT = [f"{c}_pct" for c in INDICES_COLS_RAW]
INDICES_COLS = INDICES_COLS_RAW + INDICES_COLS_PCT
INDICES_COLS_AFINIDAD = INDICES_COLS_PCT

def media_ponderada(serie, pesos):
    s = pd.to_numeric(serie, errors="coerce")
    w = pd.to_numeric(pesos, errors="coerce")
    val = np.isfinite(s) & np.isfinite(w) & (w > 0)
    if not val.any():
        return None
    return float(np.average(s[val], weights=w[val]))

def calcular_tasa_informalidad(p6920_series, pesos):
    """
    Informalidad según no cotización a pensión: P6920 == 2.
    Base de cálculo: ocupados con respuesta válida en P6920 in [1, 2].
    """
    p = pd.to_numeric(p6920_series, errors="coerce")
    w = pd.to_numeric(pesos, errors="coerce")
    val = p.isin([1, 2]) & np.isfinite(w) & (w > 0)
    if not val.any():
        return None
    informal_w = w[val & (p == 2)].sum()
    total_w = w[val].sum()
    return float(informal_w / total_w) if total_w > 0 else None

def salario_formateado(val):
    if val is None or not np.isfinite(val):
        return "No evaluable"
    return f"${val:,.0f} COP (2026)"

CIUO_2D_TITLES = {
    11: "Directores ejecutivos, legisladores y altos funcionarios",
    12: "Directores de adm., finanzas, ventas y mercadeo",
    13: "Directores de producción, logística y operaciones",
    14: "Gerentes de hoteles, restaurantes y comercio",
    21: "Profesionales de ciencias físicas, químicas e ingeniería",
    22: "Profesionales de la salud (médicos, enfermeros)",
    23: "Profesionales de la educación y profesores",
    24: "Especialistas en finanzas, contabilidad y adm.",
    25: "Profesionales en tecnologías de la información (TI/IA)",
    26: "Especialistas en leyes, ciencias sociales y artes",
    31: "Técnicos en ciencias físicas e ingeniería",
    32: "Técnicos de la salud y medicina",
    33: "Técnicos en finanzas, administración y ventas",
    34: "Técnicos en servicios sociales, cultura y deportes",
    35: "Técnicos en soporte TI y telecomunicaciones",
    41: "Oficinistas generales y secretarios",
    42: "Empleados de trato directo, cajeros y Call Center",
    43: "Auxiliares contables, de nómina e inventarios",
    44: "Otro personal de apoyo administrativo y archivo",
    51: "Trabajadores de servicios personales (cocineros, meseros)",
    52: "Vendedores de mostrador, tiendas y comercios",
    53: "Trabajadores de los cuidados personales y niñeras",
    54: "Personal de servicios de protección y vigilancia",
    61: "Agricultores y trabajadores calificados de cultivos",
    62: "Trabajadores agropecuarios de subsistencia",
    63: "Pescadores, acuicultores y recolectores",
    71: "Oficiales y operarios de la construcción (albañiles)",
    72: "Oficiales y operarios de metalurgia y mecánica",
    73: "Artesanos y operarios de artes gráficas",
    74: "Trabajadores especializados en electricidad",
    75: "Operarios de alimentos, confección y madera",
    81: "Operadores de instalaciones fijas y máquinas",
    82: "Ensambladores industriales",
    83: "Conductores y choferes (taxis, buses, camiones)",
    91: "Personal de limpieza y trabajadoras del hogar",
    92: "Peones agrícolas, ganaderos y forestales",
    93: "Peones de construcción, obras y fábricas",
    94: "Ayudantes de cocina y comida rápida",
    95: "Vendedores ambulantes y comercio informal",
    96: "Recolectores de basura, recicladores y barrenderos",
    1: "Oficiales de las fuerzas armadas",
    2: "Suboficiales de las fuerzas armadas",
    3: "Otros miembros de las fuerzas armadas"
}

def procesar_ano(year):
    path = MICRODATOS[year]
    print(f"Procesando año {year} desde {path.name}...")
    cols = ["OCI_geih", "DSI_geih", "P6040", "FEX_C", "OFICIO_C8_geih", "OFICIO2_C8_geih", "P6920_geih", "inglabo_real_geih"]
    df = pd.read_parquet(path, columns=cols)
    df["ciuo08"] = ocupacion_analitica(df)
    reference = pd.read_csv(INDICES, dtype={"ciuo08": "string"}).set_index("ciuo08")
    for alias, (raw, percentile, _) in ALIASES.items():
        df[alias] = df.ciuo08.map(reference[raw])
        df[alias+"_pct"] = 100*df.ciuo08.map(reference[percentile])
    
    # Filtro ocupados >= 15 años con factor positivo
    ocup = df[(df["OCI_geih"] == 1) & (df["P6040"] >= 15) & (df["FEX_C"] > 0)].copy()
    
    ocup["inglabo_real_geih"] = ocup["inglabo_real_geih"].where(ocup["inglabo_real_geih"].gt(0))
    # Código CIUO válido
    cod = pd.to_numeric(ocup["OFICIO_C8_geih"], errors="coerce")
    val_cod = cod.notna() & (cod >= 110) & (cod <= 9999) & (cod != 9999) & (cod == np.floor(cod))
    ocup = ocup[val_cod].copy()
    ocup["ciuo"] = cod[val_cod].astype(int)
    ocup["gran_grupo"] = ocup["ciuo"].map(lambda x: int(str(x).zfill(4)[0]))
    ocup["ciuo_2d"] = ocup["ciuo"].map(lambda x: int(str(x).zfill(4)[:2]))
    
    total_ocupados = float(ocup["FEX_C"].sum())
    tasa_informalidad_nal = calcular_tasa_informalidad(ocup["P6920_geih"], ocup["FEX_C"])
    salario_medio_nal = media_ponderada(ocup["inglabo_real_geih"], ocup["FEX_C"])
    
    # Macro grupos (1 dígito)
    macro_grupos = []
    for gg, g in ocup.groupby("gran_grupo"):
        gg_int = int(gg)
        pob_gg = float(g["FEX_C"].sum())
        sal_gg = media_ponderada(g["inglabo_real_geih"], g["FEX_C"])
        inf_gg = calcular_tasa_informalidad(g["P6920_geih"], g["FEX_C"])
        
        item_gg = {
            "id": gg_int,
            "ciuo": gg_int,
            "nombre": NOMBRES_GRUPOS[gg_int] if gg_int < len(NOMBRES_GRUPOS) else f"Grupo {gg_int}",
            "titulo": f"Grupo {gg_int}: {NOMBRES_GRUPOS[gg_int]}" if gg_int < len(NOMBRES_GRUPOS) else f"Grupo {gg_int}",
            "poblacion_estimada": pob_gg,
            "poblacion_texto": f"{pob_gg:,.0f} personas",
            "share_pct": float(pob_gg / total_ocupados * 100),
            "salario_medio": sal_gg,
            "salario_texto": salario_formateado(sal_gg),
            "tasa_informalidad": inf_gg,
            "informalidad_pct": float(inf_gg * 100) if inf_gg is not None else None,
            "n_ocupaciones": len(g["ciuo"].unique())
        }
        for idx in INDICES_COLS:
            item_gg[idx] = media_ponderada(g[idx], g["FEX_C"])
        macro_grupos.append(item_gg)
        
    # MÁXIMO 8 MACRO-FAMILIAS OCUPACIONALES (Consolidando grupos 7 y 8, excluyendo militares 0)
    macro_8_familias = []
    familias_def = [
        (1, [1], "Dirección y gerencia", "1: Dirección y gerencia"),
        (2, [2], "Profesionales y científicos", "2: Profesionales y científicos"),
        (3, [3], "Técnicos y asistentes", "3: Técnicos y asistentes"),
        (4, [4], "Personal administrativo", "4: Personal administrativo"),
        (5, [5], "Servicios y vendedores", "5: Servicios y vendedores"),
        (6, [6], "Agropecuarios y pesqueros", "6: Agropecuarios y pesqueros"),
        (7, [7, 8], "Operarios, oficios y transporte", "7: Operarios, oficios y transporte"),
        (8, [9], "Ocupaciones elementales", "8: Ocupaciones elementales"),
    ]
    for f_id, g_list, f_nom, f_tit in familias_def:
        g_fam = ocup[ocup["gran_grupo"].isin(g_list)]
        if len(g_fam) == 0:
            continue
        pob_f = float(g_fam["FEX_C"].sum())
        sal_f = media_ponderada(g_fam["inglabo_real_geih"], g_fam["FEX_C"])
        inf_f = calcular_tasa_informalidad(g_fam["P6920_geih"], g_fam["FEX_C"])
        
        item_f = {
            "id": f_id,
            "ciuo": f_id,
            "gran_grupo": f_id,
            "nombre": f_nom,
            "titulo": f_tit,
            "poblacion_estimada": pob_f,
            "poblacion_texto": f"{pob_f:,.0f} personas",
            "share_pct": float(pob_f / total_ocupados * 100),
            "salario_medio": sal_f,
            "salario_texto": salario_formateado(sal_f),
            "tasa_informalidad": inf_f,
            "informalidad_pct": float(inf_f * 100) if inf_f is not None else None,
            "n_ocupaciones": len(g_fam["ciuo"].unique())
        }
        for idx in INDICES_COLS:
            item_f[idx] = media_ponderada(g_fam[idx], g_fam["FEX_C"])
        macro_8_familias.append(item_f)
        
    # Subgrupos Principales (2 dígitos CIUO)
    subgrupos_2d = []
    for code_2d, g in ocup.groupby("ciuo_2d"):
        c2_int = int(code_2d)
        gg_int = int(g["gran_grupo"].iloc[0])
        nombre_2d = CIUO_2D_TITLES.get(c2_int, f"Subgrupo {c2_int:02d}")
        pob_2d = float(g["FEX_C"].sum())
        sal_2d = media_ponderada(g["inglabo_real_geih"], g["FEX_C"])
        inf_2d = calcular_tasa_informalidad(g["P6920_geih"], g["FEX_C"])
        
        item_2d = {
            "ciuo_2d": c2_int,
            "ciuo": c2_int,
            "nombre": nombre_2d,
            "titulo": f"{c2_int:02d}: {nombre_2d}",
            "gran_grupo": gg_int,
            "gran_grupo_nombre": NOMBRES_GRUPOS[gg_int] if gg_int < len(NOMBRES_GRUPOS) else f"Grupo {gg_int}",
            "poblacion_estimada": pob_2d,
            "poblacion_texto": f"{pob_2d:,.0f} personas",
            "share_pct": float(pob_2d / total_ocupados * 100),
            "salario_medio": sal_2d,
            "salario_texto": salario_formateado(sal_2d),
            "tasa_informalidad": inf_2d,
            "informalidad_pct": float(inf_2d * 100) if inf_2d is not None else None,
            "n_ocupaciones": len(g["ciuo"].unique())
        }
        for idx in INDICES_COLS:
            item_2d[idx] = media_ponderada(g[idx], g["FEX_C"])
        subgrupos_2d.append(item_2d)
    subgrupos_2d.sort(key=lambda x: x["ciuo_2d"])

    # Profesiones (4 dígitos CIUO)
    profesiones = []
    for code, g in ocup.groupby("ciuo"):
        code_int = int(code)
        gg_int = int(g["gran_grupo"].iloc[0])
        c2_int = int(str(code_int).zfill(4)[:2])
        titulo, alias = CIUO_TITLES.get(code_int, (f"Ocupación CIUO {code_int:04d}", f"ciuo {code_int:04d}"))
        pob = float(g["FEX_C"].sum())
        sal = media_ponderada(g["inglabo_real_geih"], g["FEX_C"])
        inf = calcular_tasa_informalidad(g["P6920_geih"], g["FEX_C"])
        
        prof = {
            "ciuo": code_int,
            "ciuo_2d": c2_int,
            "titulo": titulo,
            "alias": f"{titulo.lower()}, {alias.lower()}",
            "gran_grupo": gg_int,
            "gran_grupo_nombre": NOMBRES_GRUPOS[gg_int] if gg_int < len(NOMBRES_GRUPOS) else f"Grupo {gg_int}",
            "subgrupo_nombre": CIUO_2D_TITLES.get(c2_int, f"Subgrupo {c2_int:02d}"),
            "poblacion_estimada": pob,
            "poblacion_texto": f"{pob:,.0f} personas",
            "share_pct": float(pob / total_ocupados * 100),
            "salario_medio": sal,
            "salario_texto": salario_formateado(sal),
            "tasa_informalidad": inf,
            "informalidad_pct": float(inf * 100) if inf is not None else None,
            "n_observaciones": len(g)
        }
        for idx in INDICES_COLS:
            prof[idx] = media_ponderada(g[idx], g["FEX_C"])
            
        profesiones.append(prof)
        
    profesiones.sort(key=lambda x: x["titulo"])
    
    return {
        "total_ocupados": total_ocupados,
        "tasa_informalidad_nacional": tasa_informalidad_nal,
        "salario_medio_nacional": salario_medio_nal,
        "macro_8_familias": macro_8_familias,
        "macro_grupos": macro_grupos,
        "subgrupos_2d": subgrupos_2d,
        "profesiones": profesiones
    }

def calcular_ocupaciones_relacionadas(datos_por_anio):
    """
    Calcula las 5 ocupaciones más cercanas a cada CIUO mediante distancia
    euclidiana en el espacio estandarizado de los 8 índices de exposición.
    Utiliza los datos consolidados (2025 como referencia principal).
    """
    print("Calculando ocupaciones relacionadas por distancia euclidiana en índices...")
    # Usar las profesiones de 2025 como base (contiene la lista más completa y actualizada)
    prof_ref = datos_por_anio["2025"]["profesiones"]
    df_ref = pd.DataFrame(prof_ref)
    
    # Filtrar profesiones con al menos un índice válido (solo _pct: evita que
    # crudo+percentil, altamente correlacionados, pesen doble en la distancia)
    valid_mask = df_ref[INDICES_COLS_AFINIDAD].notna().any(axis=1)
    df_valid = df_ref[valid_mask].copy()

    # Afinidad descriptiva separada de las puntuaciones oficiales.
    # Se exigen las cinco puntuaciones, sin rellenar exposiciones ausentes.
    df_valid = df_valid.dropna(subset=INDICES_COLS_AFINIDAD).copy()
    # Estandarización z-score de los índices
    mat = df_valid[INDICES_COLS_AFINIDAD].copy()
    for c in INDICES_COLS_AFINIDAD:
        col_mean = mat[c].mean()
        col_std = mat[c].std()
        if col_std > 0:
            mat[c] = (mat[c] - col_mean) / col_std
        else:
            mat[c] = 0.0
    mat = mat.fillna(0.0).values
    
    ciuos = df_valid["ciuo"].tolist()
    titulos = df_valid["titulo"].tolist()
    salarios = df_valid["salario_medio"].tolist()
    sal_txt = df_valid["salario_texto"].tolist()
    gpt_vals = df_valid["exp_gpt4_beta"].tolist()
    gpt_pct_vals = df_valid["exp_gpt4_beta_pct"].tolist()
    rob_vals = df_valid["exp_webb_robot"].tolist()
    rob_pct_vals = df_valid["exp_webb_robot_pct"].tolist()
    
    n = len(ciuos)
    # Matriz de distancias euclidianas
    dist_mat = np.zeros((n, n))
    for i in range(n):
        diff = mat - mat[i]
        dist_mat[i] = np.sqrt(np.sum(diff**2, axis=1))
        
    relacionadas = {}
    for i in range(n):
        c_i = ciuos[i]
        # Ordenar por distancia (excluyendo a sí mismo en pos 0)
        idx_orden = np.argsort(dist_mat[i])
        idx_vecinos = [idx for idx in idx_orden if idx != i][:5]
        
        vecinos_info = []
        for j in idx_vecinos:
            d_val = float(dist_mat[i, j])
            # Proximidad normalizada (0 a 100%)
            similitud = max(0.0, 100.0 - (d_val * 15.0))
            vecinos_info.append({
                "ciuo": ciuos[j],
                "titulo": titulos[j],
                "distancia": round(d_val, 3),
                "similitud_pct": round(similitud, 1),
                "salario_medio": salarios[j],
                "salario_texto": sal_txt[j],
                "exp_gpt4_beta": gpt_vals[j],
                "exp_gpt4_beta_pct": gpt_pct_vals[j],
                "exp_webb_robot": rob_vals[j],
                "exp_webb_robot_pct": rob_pct_vals[j]
            })
        relacionadas[str(c_i)] = vecinos_info
        
    return relacionadas

def limpiar_nans(obj):
    if isinstance(obj, float):
        return float(obj) if np.isfinite(obj) else None
    elif isinstance(obj, (np.floating, np.integer)):
        val = float(obj)
        return val if np.isfinite(val) else None
    elif isinstance(obj, dict):
        return {k: limpiar_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [limpiar_nans(v) for v in obj]
    return obj

def main():
    anios = [2022, 2023, 2024, 2025]
    datos_por_anio = {}
    for yr in anios:
        datos_por_anio[str(yr)] = procesar_ano(yr)
        
    ocupaciones_rel = calcular_ocupaciones_relacionadas(datos_por_anio)
    
    catalogo = {
        "anios_disponibles": anios,
        "anio_defecto": 2025,
        "indicadores_x": INDICADORES_X,
        "indicadores_y": INDICADORES_Y,
        "datos_por_anio": datos_por_anio,
        "ocupaciones_relacionadas": ocupaciones_rel,
        "metodologia": (
            "Índices ocupacionales transferidos mediante correspondencias internacionales "
            "desde O*NET/SOC hacia la clasificación CIUO-08 a 4 dígitos del DANE. "
            "Salarios reales deflactados a precios constantes de octubre de 2025 (IPC observado = 151.76). "
            "No cotización calculada con P6920_geih == 2 entre ocupados con respuesta 1/2 válida, ponderada por FEX_C; no es informalidad oficial. Los percentiles de las vistas históricas se muestran en escala 0–100 mediante multiplicación por cien del catálogo fijo."
        )
    }
    
    catalogo_limpio = limpiar_nans(catalogo)
    
    catalogo["fuentes_sha256"] = {str(INDICES.relative_to(ROOT)): hashlib.sha256(INDICES.read_bytes()).hexdigest(), **{str(MICRODATOS[y].relative_to(ROOT)): hashlib.sha256(MICRODATOS[y].read_bytes()).hexdigest() for y in anios}}
    catalogo_limpio = limpiar_nans(catalogo)
    out_file = OUTPUT
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Guardando catálogo multianual en {out_file}...")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(catalogo_limpio, f, ensure_ascii=False, indent=2, allow_nan=False)
        
    print(f"¡Catálogo generado exitosamente! Tamaño: {out_file.stat().st_size / 1024:.1f} KB")
    print(f"Total ocupaciones en 2025: {len(datos_por_anio['2025']['profesiones'])}")
    print(f"Total ocupaciones con red de afinidad: {len(ocupaciones_rel)}")

if __name__ == "__main__":
    main()
