from urllib import request, error
import tempfile
import os, sys, shutil
from importlib import reload
from pytket.qasm import circuit_from_qasm_str


def prepare_code_from_data(data, input_params):
    """Get implementation code from data. Set input parameters into implementation. Return circuit."""
    temp_dir = tempfile.mkdtemp()
    with open(os.path.join(temp_dir, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(temp_dir, "downloaded_code.py"), "w") as f:
        f.write(data)
    sys.path.append(temp_dir)
    try:
        import downloaded_code

        reload(downloaded_code)
        if 'get_circuit' in dir(downloaded_code):
            circuit = downloaded_code.get_circuit(**input_params)
        elif 'qc' in dir(downloaded_code):
            circuit = downloaded_code.qc
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


def prepare_code_from_qasm_url(url):
    """Get implementation code from URL. Set input parameters into implementation. Return circuit."""
    try:
        impl = request.urlopen(url).read().decode("utf-8")
    except (error.HTTPError, error.URLError):
        return None

    return prepare_code_from_qasm(impl)