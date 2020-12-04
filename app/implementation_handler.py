from urllib import request, error
import tempfile
import os, sys, shutil
from importlib import reload


def prepare_code_from_url(url, input_params):
    """Get implementation code from URL. Set input parameters into implementation. Return circuit."""
    try:
        impl = request.urlopen(url).read().decode("utf-8")
    except (error.HTTPError, error.URLError):
        return None

    temp_dir = tempfile.mkdtemp()
    with open(os.path.join(temp_dir, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(temp_dir, "downloaded_code.py"), "w") as f:
        f.write(impl)
    sys.path.append(temp_dir)
    try:
        import downloaded_code

        reload(downloaded_code)
        circuit = downloaded_code.get_circuit(**input_params)
    finally:
        sys.path.remove(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    return circuit

