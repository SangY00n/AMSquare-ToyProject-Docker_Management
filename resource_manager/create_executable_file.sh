#!/bin/sh

[ -f resource_manager ] && rm resource_manager

pyinstaller -w -F resource_manager.py

mv -f dist/resource_manager ./resource_manager

rm -rf build
rm -rf dist
rm resource_manager.spec

echo "Executable file 'resource_manager' was created!"