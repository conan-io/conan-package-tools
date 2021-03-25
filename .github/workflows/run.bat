conan user
mkdir %USERPROFILE%/.conan/data
set USE_UNSUPPORTED_CONAN_WITH_PYTHON_2=1
nosetests -v cpt.test --nocapture
