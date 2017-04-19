SET PATH=%PYTHON%;%PYTHON%\\Scripts;%PATH%
SET PYTHONPATH=%PYTHONPATH%;%CD%
%PYTHON%/Scripts/pip.exe install -r conan/requirements.txt
