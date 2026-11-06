# Referencia para volver a enlazar los objetos conservados.
# No recompila fuentes y no se ha validado con el SDK original instalado.
TEMPLATE = app
TARGET = SonarFrontEnd-relinked
QT += core gui widgets serialport printsupport
CONFIG += release c++11
CONFIG -= debug debug_and_release console

PROJECT_ROOT = $$clean_path($$PWD/../..)
PRESERVED_OBJECTS = fft.o main.o mainwindow.o settings.o qcustomplot.o \
    moc_mainwindow.o moc_settings.o moc_qcustomplot.o qrc_reources.o
for(objectFile, PRESERVED_OBJECTS) {
    objectPath = $$PROJECT_ROOT/$$objectFile
    !exists($$objectPath): error(Missing preserved object: $$objectPath)
    LIBS += $$quote($$objectPath)
    PRE_TARGETDEPS += $$quote($$objectPath)
}
