@echo off
echo Compiling...
python3 -m PyQt5.pyrcc_main -o resources.py resources.qrc
echo DONE
