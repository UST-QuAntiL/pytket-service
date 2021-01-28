from pyquil import Program, get_qc
from pyquil.gates import *
import numpy as np
p = Program()
ro = p.declare('ro', 'BIT', 3)
p += H(0)
p += H(1)
p += H(1)
p += CPHASE(0.0, 1, 0)
p += H(0)
p += H(2)
p += CNOT(2, 3)
p += CNOT(2, 4)
p += CPHASE(0.0, 1, 2)
p += CPHASE(0.0, 0, 2)
p += H(2)
p += MEASURE(0, ro[0])
p += MEASURE(1, ro[1])
p += MEASURE(2, ro[2])
