#!/bin/sh

[ -f defunct_checker ] && rm defunct_checker

pyinstaller -w -F defunct_checker.py

mv -f dist/defunct_checker ./defunct_checker

rm -rf build
rm -rf dist
rm defunct_checker.spec

echo "Executable file 'defunct_checker' was created!"