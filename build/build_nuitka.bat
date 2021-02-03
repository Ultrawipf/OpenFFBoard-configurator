cd ..
python -m nuitka --show-progress --standalone --windows-dependency-tool=pefile --plugin-enable=qt-plugins --plugin-enable=numpy --follow-imports --windows-icon-from-ico=build\app.ico main.py