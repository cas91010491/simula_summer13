from numpy import *

x1 = [-4.652905000000000e+00, 6.122390000000000e-01, 2.452448000000000e+00]

x2 = [-4.629167000000000e+00, 1.466620000000000e-01, 2.537269000000000e+00]

x3 = [-4.500890000000000e+00, 3.435120000000000e-01, 2.258370000000000e+00]

y1 = [-0.13053999999999999,  -0.15320300000000001,  -3.0811739999999999]

y2 = [-0.085587999999999997,  -0.97470199999999996,  -2.3163490000000002]

y3 = [-0.70269599999999999,  -0.13383300000000001,  -2.4570690000000002]

R = [[ -8.66025404e-01,  -1.06057524e-16,   5.00000000e-01],
 [ -2.50000000e-01,  -8.66025404e-01,  -4.33012702e-01],
 [  4.33012702e-01,  -5.00000000e-01,   7.50000000e-01]]

print dot(R,y1)