"""Write the supplied-binary dependency inventory from static and runtime evidence."""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / 'analysis' / 'evidence'
inventory = json.loads((EVIDENCE / 'pe_inventory.json').read_text())
roles = {
    'SonarFrontEnd.exe': 'Aplicación GUI y código de QCustomPlot/FFT incorporado',
    'Qt5Core.dll': 'Objetos, eventos, contenedores, temporizadores y serialización',
    'Qt5Gui.dll': 'Pintura, fuentes, imágenes, iconos y soporte gráfico',
    'Qt5Widgets.dll': 'Ventanas, diálogos, acciones, controles y layouts',
    'Qt5SerialPort.dll': 'Enumeración, configuración y E/S del puerto serie',
    'Qt5PrintSupport.dll': 'Infraestructura de impresión/PDF utilizada por QCustomPlot',
    'Qt5Svg.dll': 'Renderizado SVG para iconos y plugins',
    'libgcc_s_seh-1.dll': 'Runtime de GCC y excepciones SEH',
    'libstdc++-6.dll': 'Runtime y biblioteca estándar de C++ de MinGW',
    'libwinpthread-1.dll': 'Implementación de hilos POSIX de MinGW',
    'libEGL.dll': 'Capa EGL del backend ANGLE distribuido con Qt',
    'libGLESv2.dll': 'OpenGL ES/ANGLE sobre Direct3D',
    'D3Dcompiler_47.dll': 'Compilación de shaders de Direct3D para el backend gráfico',
    'opengl32sw.dll': 'Backend OpenGL por software distribuido con Qt',
    'qwindows.dll': 'Plugin de plataforma Windows para Qt; necesario para crear la GUI',
    'qwindowsvistastyle.dll': 'Estilo de widgets Windows',
    'windowsprintersupport.dll': 'Plugin de impresión de Windows',
    'qsvgicon.dll': 'Motor de iconos SVG',
    'qgif.dll': 'Formato de imagen GIF',
    'qicns.dll': 'Formato de imagen ICNS',
    'qico.dll': 'Formato de imagen ICO',
    'qjpeg.dll': 'Formato de imagen JPEG',
    'qsvg.dll': 'Formato de imagen SVG',
    'qtga.dll': 'Formato de imagen TGA',
    'qtiff.dll': 'Formato de imagen TIFF',
    'qwbmp.dll': 'Formato de imagen WBMP',
    'qwebp.dll': 'Formato de imagen WebP',
}
local_names = {Path(item['file']).name.lower() for item in inventory}
runtime_file = EVIDENCE / 'runtime_modules.csv'
runtime = []
if runtime_file.exists():
    with runtime_file.open(encoding='utf-8-sig', newline='') as source:
        runtime = list(csv.DictReader(source))
loaded = {item['ModuleName'].lower() for item in runtime}
lines = [
    '# Dependencias de Echosounder', '',
    'Inventario del 6 de noviembre de 2026. Se han inspeccionado los 27 binarios suministrados: '
    'un EXE y 26 DLL. Todos son AMD64. Las dependencias de ejecución del programa se distinguen '
    'de los componentes que harían falta para construirlo.', '',
    '## Bibliotecas suministradas', '',
    'Las bibliotecas Qt y sus plugins tienen versión de archivo 5.14.2.0. '
    'Los runtimes MinGW se relacionan con el compilador GCC 7.3.0 identificado en los objetos; '
    'no se asigna una versión numérica inventada a las DLL que no la declaran.', '',
    '| Archivo | Función | Cargado en el arranque observado |',
    '| --- | --- | --- |',
]
for item in inventory:
    name = Path(item['file']).name
    lines.append(f"| `{item['file']}` | {roles[name]} | {'Sí' if name.lower() in loaded else 'No observado'} |")
lines += [
    '', 'La columna de carga procede de una ejecución sin conectar al sonar. '
    'Que una DLL no aparezca no significa que sea innecesaria en todos los equipos o al imprimir. '
    'En particular, los backends gráficos se eligen según Qt, Windows y el controlador.', '',
    'El ejecutable importa directamente Qt5Core, Qt5Gui, Qt5Widgets, Qt5SerialPort y Qt5PrintSupport, '
    'además de los runtimes y componentes de Windows indicados abajo. Qt5Svg se carga mediante '
    'los plugins; no necesita figurar como importación directa del EXE para ser necesaria '
    'para sus iconos. QCustomPlot y el módulo FFT están compilados dentro del EXE, sin DLL propia.', '',
    'El paquete contiene nueve plugins de formatos de imagen. Se observaron cargados al resolver '
    'los iconos; esto no demuestra que el flujo de la aplicación utilice cada formato. '
    'No se ha intentado reducir el paquete de distribución.', '',
    '## Importaciones directas por binario', '',
    'Esta tabla contiene los nombres declarados en las tablas PE. El árbol transitivo se obtiene '
    'siguiendo las filas de las DLL suministradas. No se han encontrado importaciones diferidas '
    'en estos binarios; una carga explícita por nombre de plugin sigue siendo posible.', '',
    '| Binario | DLL importadas |', '| --- | --- |',
]
for item in inventory:
    names = ', '.join('`'+name+'`' for name in item['imports'])
    lines.append(f"| `{item['file']}` | {names} |")
external = sorted({name for item in inventory for name in item['imports']
                   if name.lower() not in local_names}, key=str.lower)
lines += [
    '', '## Componentes de Windows', '',
    'Los siguientes nombres importados no se distribuyen en esta carpeta y corresponden a '
    'componentes de Windows. Se enumeran por su nombre real, sin sugerir que se copien desde '
    'System32 al paquete:', '',
    ', '.join('`'+name+'`' for name in external) + '.', '',
    'Cubren ventanas y gráficos, COM, impresión, registro y servicios, enumeración de dispositivos, '
    'temporización, red de bajo nivel y runtime C. Por ejemplo, WS2_32 y NETAPI32 son importaciones '
    'de Qt5Core: por sí solas no prueban una función de red implementada por Echosounder.', '',
    'El controlador del adaptador serie/USB es una dependencia externa del instrumento. '
    'No se suministra un controlador específico ni se puede identificar el modelo exacto '
    'del hardware a partir de estos archivos. Los drivers gráficos y las DLL cargadas dinámicamente '
    'por Windows varían entre equipos; el inventario estático no es una lista universal de todos '
    'los módulos que podría llegar a cargar cualquier instalación.', '',
    '## Traducciones y recursos', '',
    'Se distribuyen 22 traducciones Qt `.qm`: ' + ', '.join('`'+p.name+'`' for p in sorted((ROOT/'translations').glob('*.qm'))) + '.', '',
    'Son recursos, no bibliotecas ejecutables. Su presencia no acredita que la aplicación '
    'traduzca sus propias cadenas: el camino de arranque analizado no muestra instalación '
    'de un traductor de la aplicación.', '',
    'Los diez SVG de la barra de herramientas estaban embebidos en `qrc_reources.o` y el EXE. '
    'Se han recuperado en `recovered-resources/art`, con sus rutas de recurso originales.', '',
    '## Dependencias para construir', '',
    'Para un reenlazado: los nueve `.o` conservados, MinGW GCC 7.3.0 x64 POSIX/SEH y las '
    'bibliotecas de importación/arranque de Qt 5.14.2 para ese kit. Para construir desde fuentes '
    'se añaden cabeceras Qt, qmake/make, moc/uic/rcc, fuentes propios, formularios y QCustomPlot. '
    'No se identifica una dependencia de construcción de FFTW, OpenCV, Python, .NET, CUDA, '
    'Qt Charts, Qt Quick/QML o una base de datos en las unidades observadas.', '',
    'Python, pefile y Capstone se han utilizado solo para este análisis. No son dependencias '
    'de ejecución ni de construcción del programa C++ original.', '',
    'Las bibliotecas Qt/ANGLE también incorporan código de terceros. Sin el fuente y la '
    'configuración de construcción del SDK no se puede emitir una SBOM completa de cada '
    'componente incorporado estáticamente. Este inventario cubre los archivos suministrados, '
    'sus importaciones y las dependencias fuente que pueden identificarse.', '',
    '## Evidencia', '',
    '- `evidence/pe_inventory.json`: SHA-256, arquitectura, secciones e importaciones por función.',
    '- `evidence/runtime_modules.csv`: módulos cargados en el arranque observado.',
    '- `evidence/file_versions.json`: versiones de archivo declaradas por las DLL.',
    '- `evidence/coff_inventory.json`: símbolos y reubicaciones de los objetos.',
    '- `RECOMPILACION.md`: rutas de construcción y plantillas preparadas.', '',
]
assert len(inventory) == 27
assert all(item['machine'] == '0x8664' for item in inventory)
assert not any(item['delay_imports'] for item in inventory)
(ROOT/'analysis'/'DEPENDENCIAS.md').write_text('\n'.join(lines), encoding='utf8')
print(f'Documented {len(inventory)} PE files and {len(external)} Windows import names.')
