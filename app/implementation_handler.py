from urllib import request, error
import tempfile
import os, sys, shutil, re
from importlib import reload
from pytket.qasm import circuit_from_qasm_str
from pyquil import Program as PyQuilProgram


def prepare_code(impl_url, impl_data, impl_language, input_params):

    if impl_url:
        # Download and execute the implementation
        if impl_language.lower() == "openqasm":
            short_impl_name = re.match(".*/(?P<file>.*\\.qasm)", impl_url).group('file')
            circuit = prepare_code_from_qasm_url(impl_url)
        elif impl_language.lower() == "quil":
            short_impl_name = re.match(".*/(?P<file>.*\\.quil)", impl_url).group('file')
            circuit = prepare_code_from_quil_url(impl_url)
        else:
            short_impl_name = re.match(".*/(?P<file>.*\\.py)", impl_url).group('file')
            circuit = prepare_code_from_url(impl_url, input_params)

    elif impl_data:
        short_impl_name = "untitled"
        if impl_language.lower() == "openqasm":
            circuit = prepare_code_from_qasm(impl_data)
        elif impl_language.lower() == "quil":
            circuit = prepare_code_from_quil(impl_data)
        else:
            circuit = prepare_code_from_data(impl_data, input_params)
    else:
        raise Exception("No implementation specified.")

    return circuit, short_impl_name

def prepare_code_from_data(data, input_params):
    """Get implementation code from data. Set input parameters into implementation. Return circuit."""
    temp_dir = tempfile.mkdtemp()
    with open(os.path.join(temp_dir, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(temp_dir, "downloaded_code.py"), "w") as f:
        f.write(data)
    sys.path.append(temp_dir)
    circuit=None
    try:
        import downloaded_code

        reload(downloaded_code)
        if 'get_circuit' in dir(downloaded_code):
            circuit = downloaded_code.get_circuit(**input_params)
        elif 'qc' in dir(downloaded_code):
            circuit = downloaded_code.qc
        elif 'p' in dir(downloaded_code):
            circuit = downloaded_code.p
    finally:
        sys.path.remove(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    if not circuit:
        raise ValueError
    return circuit


def prepare_code_from_url(url, input_params):
    """Get implementation code from URL. Set input parameters into implementation. Return circuit."""
    try:
        impl = request.urlopen(url).read().decode("utf-8")
    except (error.HTTPError, error.URLError):
        return None

    circuit = prepare_code_from_data(impl, input_params)
    return circuit


def prepare_code_from_qasm(qasm):
    return circuit_from_qasm_str(qasm)

def prepare_code_from_quil(quil):
    return PyQuilProgram(quil)

def prepare_code_from_qasm_url(url):
    """Get implementation code from URL. Set input parameters into implementation. Return circuit."""
    try:
        impl = request.urlopen(url).read().decode("utf-8")
    except (error.HTTPError, error.URLError):
        return None

    return prepare_code_from_qasm(impl)

def prepare_code_from_quil_url(url):
    """Get implementation code from URL. Set input parameters into implementation. Return circuit."""
    try:
        impl = request.urlopen(url).read().decode("utf-8")
    except (error.HTTPError, error.URLError):
        return None

    return prepare_code_from_quil(impl)