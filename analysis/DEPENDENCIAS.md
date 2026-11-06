# Dependencias de Echosounder

Inventario del 6 de noviembre de 2026. Se han inspeccionado los 27 binarios suministrados: un EXE y 26 DLL. Todos son AMD64. Las dependencias de ejecución del programa se distinguen de los componentes que harían falta para construirlo.

## Bibliotecas suministradas

Las bibliotecas Qt y sus plugins tienen versión de archivo 5.14.2.0. Los runtimes MinGW se relacionan con el compilador GCC 7.3.0 identificado en los objetos; no se asigna una versión numérica inventada a las DLL que no la declaran.

| Archivo | Función | Cargado en el arranque observado |
| --- | --- | --- |
| `D3Dcompiler_47.dll` | Compilación de shaders de Direct3D para el backend gráfico | No observado |
| `iconengines/qsvgicon.dll` | Motor de iconos SVG | Sí |
| `imageformats/qgif.dll` | Formato de imagen GIF | Sí |
| `imageformats/qicns.dll` | Formato de imagen ICNS | Sí |
| `imageformats/qico.dll` | Formato de imagen ICO | Sí |
| `imageformats/qjpeg.dll` | Formato de imagen JPEG | Sí |
| `imageformats/qsvg.dll` | Formato de imagen SVG | Sí |
| `imageformats/qtga.dll` | Formato de imagen TGA | Sí |
| `imageformats/qtiff.dll` | Formato de imagen TIFF | Sí |
| `imageformats/qwbmp.dll` | Formato de imagen WBMP | Sí |
| `imageformats/qwebp.dll` | Formato de imagen WebP | Sí |
| `libEGL.dll` | Capa EGL del backend ANGLE distribuido con Qt | No observado |
| `libgcc_s_seh-1.dll` | Runtime de GCC y excepciones SEH | Sí |
| `libGLESv2.dll` | OpenGL ES/ANGLE sobre Direct3D | No observado |
| `libstdc++-6.dll` | Runtime y biblioteca estándar de C++ de MinGW | Sí |
| `libwinpthread-1.dll` | Implementación de hilos POSIX de MinGW | Sí |
| `opengl32sw.dll` | Backend OpenGL por software distribuido con Qt | No observado |
| `platforms/qwindows.dll` | Plugin de plataforma Windows para Qt; necesario para crear la GUI | Sí |
| `printsupport/windowsprintersupport.dll` | Plugin de impresión de Windows | No observado |
| `Qt5Core.dll` | Objetos, eventos, contenedores, temporizadores y serialización | Sí |
| `Qt5Gui.dll` | Pintura, fuentes, imágenes, iconos y soporte gráfico | Sí |
| `Qt5PrintSupport.dll` | Infraestructura de impresión/PDF utilizada por QCustomPlot | Sí |
| `Qt5SerialPort.dll` | Enumeración, configuración y E/S del puerto serie | Sí |
| `Qt5Svg.dll` | Renderizado SVG para iconos y plugins | Sí |
| `Qt5Widgets.dll` | Ventanas, diálogos, acciones, controles y layouts | Sí |
| `SonarFrontEnd.exe` | Aplicación GUI y código de QCustomPlot/FFT incorporado | Sí |
| `styles/qwindowsvistastyle.dll` | Estilo de widgets Windows | Sí |

La columna de carga procede de una ejecución sin conectar al sonar. Que una DLL no aparezca no significa que sea innecesaria en todos los equipos o al imprimir. En particular, los backends gráficos se eligen según Qt, Windows y el controlador.

El ejecutable importa directamente Qt5Core, Qt5Gui, Qt5Widgets, Qt5SerialPort y Qt5PrintSupport, además de los runtimes y componentes de Windows indicados abajo. Qt5Svg se carga mediante los plugins; no necesita figurar como importación directa del EXE para ser necesaria para sus iconos. QCustomPlot y el módulo FFT están compilados dentro del EXE, sin DLL propia.

El paquete contiene nueve plugins de formatos de imagen. Se observaron cargados al resolver los iconos; esto no demuestra que el flujo de la aplicación utilice cada formato. No se ha intentado reducir el paquete de distribución.

## Importaciones directas por binario

Esta tabla contiene los nombres declarados en las tablas PE. El árbol transitivo se obtiene siguiendo las filas de las DLL suministradas. No se han encontrado importaciones diferidas en estos binarios; una carga explícita por nombre de plugin sigue siendo posible.

| Binario | DLL importadas |
| --- | --- |
| `D3Dcompiler_47.dll` | `msvcrt.dll`, `ADVAPI32.dll`, `KERNEL32.dll`, `RPCRT4.dll` |
| `iconengines/qsvgicon.dll` | `KERNEL32.dll`, `msvcrt.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll`, `Qt5Svg.dll` |
| `imageformats/qgif.dll` | `KERNEL32.dll`, `msvcrt.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll` |
| `imageformats/qicns.dll` | `KERNEL32.dll`, `msvcrt.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll` |
| `imageformats/qico.dll` | `KERNEL32.dll`, `msvcrt.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll` |
| `imageformats/qjpeg.dll` | `KERNEL32.dll`, `msvcrt.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll` |
| `imageformats/qsvg.dll` | `KERNEL32.dll`, `msvcrt.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll`, `Qt5Svg.dll` |
| `imageformats/qtga.dll` | `KERNEL32.dll`, `msvcrt.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll` |
| `imageformats/qtiff.dll` | `KERNEL32.dll`, `msvcrt.dll`, `USER32.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll` |
| `imageformats/qwbmp.dll` | `KERNEL32.dll`, `msvcrt.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll` |
| `imageformats/qwebp.dll` | `KERNEL32.dll`, `msvcrt.dll`, `USER32.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll` |
| `libEGL.dll` | `KERNEL32.dll`, `msvcrt.dll`, `libGLESv2.dll` |
| `libgcc_s_seh-1.dll` | `KERNEL32.dll`, `msvcrt.dll`, `libwinpthread-1.dll` |
| `libGLESv2.dll` | `d3d9.dll`, `libgcc_s_seh-1.dll`, `KERNEL32.dll`, `msvcrt.dll`, `libwinpthread-1.dll`, `USER32.dll`, `libstdc++-6.dll` |
| `libstdc++-6.dll` | `libgcc_s_seh-1.dll`, `KERNEL32.dll`, `msvcrt.dll`, `libwinpthread-1.dll`, `USER32.dll` |
| `libwinpthread-1.dll` | `KERNEL32.dll`, `msvcrt.dll` |
| `opengl32sw.dll` | `imagehlp.dll`, `SHELL32.dll`, `ADVAPI32.dll`, `GDI32.dll`, `USER32.dll`, `KERNEL32.dll` |
| `platforms/qwindows.dll` | `dwmapi.dll`, `GDI32.dll`, `IMM32.dll`, `KERNEL32.dll`, `msvcrt.dll`, `ole32.dll`, `OLEAUT32.dll`, `SHELL32.dll`, `USER32.dll`, `WINMM.dll`, `WTSAPI32.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll` |
| `printsupport/windowsprintersupport.dll` | `GDI32.dll`, `KERNEL32.dll`, `msvcrt.dll`, `WINSPOOL.DRV`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll`, `Qt5PrintSupport.dll` |
| `Qt5Core.dll` | `ADVAPI32.dll`, `libgcc_s_seh-1.dll`, `KERNEL32.dll`, `MPR.dll`, `msvcrt.dll`, `NETAPI32.dll`, `ole32.dll`, `libwinpthread-1.dll`, `SHELL32.dll`, `USER32.dll`, `USERENV.dll`, `VERSION.dll`, `WINMM.dll`, `WS2_32.dll`, `libstdc++-6.dll` |
| `Qt5Gui.dll` | `d3d11.dll`, `dxgi.dll`, `libgcc_s_seh-1.dll`, `GDI32.dll`, `KERNEL32.dll`, `msvcrt.dll`, `ole32.dll`, `libwinpthread-1.dll`, `USER32.dll`, `libstdc++-6.dll`, `Qt5Core.dll` |
| `Qt5PrintSupport.dll` | `comdlg32.dll`, `GDI32.dll`, `KERNEL32.dll`, `msvcrt.dll`, `USER32.dll`, `WINSPOOL.DRV`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll`, `Qt5Widgets.dll` |
| `Qt5SerialPort.dll` | `ADVAPI32.dll`, `KERNEL32.dll`, `msvcrt.dll`, `SETUPAPI.dll`, `libstdc++-6.dll`, `Qt5Core.dll` |
| `Qt5Svg.dll` | `KERNEL32.dll`, `msvcrt.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll`, `Qt5Widgets.dll` |
| `Qt5Widgets.dll` | `dwmapi.dll`, `GDI32.dll`, `KERNEL32.dll`, `msvcrt.dll`, `ole32.dll`, `SHELL32.dll`, `USER32.dll`, `UxTheme.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll` |
| `SonarFrontEnd.exe` | `Qt5Core.dll`, `Qt5Gui.dll`, `Qt5PrintSupport.dll`, `Qt5SerialPort.dll`, `Qt5Widgets.dll`, `libgcc_s_seh-1.dll`, `KERNEL32.dll`, `msvcrt.dll`, `SHELL32.dll`, `libstdc++-6.dll` |
| `styles/qwindowsvistastyle.dll` | `GDI32.dll`, `KERNEL32.dll`, `msvcrt.dll`, `USER32.dll`, `UxTheme.dll`, `libstdc++-6.dll`, `Qt5Core.dll`, `Qt5Gui.dll`, `Qt5Widgets.dll` |

## Componentes de Windows

Los siguientes nombres importados no se distribuyen en esta carpeta y corresponden a componentes de Windows. Se enumeran por su nombre real, sin sugerir que se copien desde System32 al paquete:

`ADVAPI32.dll`, `comdlg32.dll`, `d3d11.dll`, `d3d9.dll`, `dwmapi.dll`, `dxgi.dll`, `GDI32.dll`, `imagehlp.dll`, `IMM32.dll`, `KERNEL32.dll`, `MPR.dll`, `msvcrt.dll`, `NETAPI32.dll`, `ole32.dll`, `OLEAUT32.dll`, `RPCRT4.dll`, `SETUPAPI.dll`, `SHELL32.dll`, `USER32.dll`, `USERENV.dll`, `UxTheme.dll`, `VERSION.dll`, `WINMM.dll`, `WINSPOOL.DRV`, `WS2_32.dll`, `WTSAPI32.dll`.

Cubren ventanas y gráficos, COM, impresión, registro y servicios, enumeración de dispositivos, temporización, red de bajo nivel y runtime C. Por ejemplo, WS2_32 y NETAPI32 son importaciones de Qt5Core: por sí solas no prueban una función de red implementada por Echosounder.

El controlador del adaptador serie/USB es una dependencia externa del instrumento. No se suministra un controlador específico ni se puede identificar el modelo exacto del hardware a partir de estos archivos. Los drivers gráficos y las DLL cargadas dinámicamente por Windows varían entre equipos; el inventario estático no es una lista universal de todos los módulos que podría llegar a cargar cualquier instalación.

## Traducciones y recursos

Se distribuyen 22 traducciones Qt `.qm`: `qt_ar.qm`, `qt_bg.qm`, `qt_ca.qm`, `qt_cs.qm`, `qt_da.qm`, `qt_de.qm`, `qt_en.qm`, `qt_es.qm`, `qt_fi.qm`, `qt_fr.qm`, `qt_gd.qm`, `qt_he.qm`, `qt_hu.qm`, `qt_it.qm`, `qt_ja.qm`, `qt_ko.qm`, `qt_lv.qm`, `qt_pl.qm`, `qt_ru.qm`, `qt_sk.qm`, `qt_uk.qm`, `qt_zh_TW.qm`.

Son recursos, no bibliotecas ejecutables. Su presencia no acredita que la aplicación traduzca sus propias cadenas: el camino de arranque analizado no muestra instalación de un traductor de la aplicación.

Los diez SVG de la barra de herramientas estaban embebidos en `qrc_reources.o` y el EXE. Se han recuperado en `recovered-resources/art`, con sus rutas de recurso originales.

## Dependencias para construir

Para un reenlazado: los nueve `.o` conservados, MinGW GCC 7.3.0 x64 POSIX/SEH y las bibliotecas de importación/arranque de Qt 5.14.2 para ese kit. Para construir desde fuentes se añaden cabeceras Qt, qmake/make, moc/uic/rcc, fuentes propios, formularios y QCustomPlot. No se identifica una dependencia de construcción de FFTW, OpenCV, Python, .NET, CUDA, Qt Charts, Qt Quick/QML o una base de datos en las unidades observadas.

Python, pefile y Capstone se han utilizado solo para este análisis. No son dependencias de ejecución ni de construcción del programa C++ original.

Las bibliotecas Qt/ANGLE también incorporan código de terceros. Sin el fuente y la configuración de construcción del SDK no se puede emitir una SBOM completa de cada componente incorporado estáticamente. Este inventario cubre los archivos suministrados, sus importaciones y las dependencias fuente que pueden identificarse.

## Evidencia

- `evidence/pe_inventory.json`: SHA-256, arquitectura, secciones e importaciones por función.
- `evidence/runtime_modules.csv`: módulos cargados en el arranque observado.
- `evidence/file_versions.json`: versiones de archivo declaradas por las DLL.
- `evidence/coff_inventory.json`: símbolos y reubicaciones de los objetos.
- `RECOMPILACION.md`: rutas de construcción y plantillas preparadas.
