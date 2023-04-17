from dataclasses import dataclass
import random
import xgrid
import matplotlib.pyplot as pyplot
import numpy

xgrid.init(cacheroot=".xgridtest", parallel=False, precision="double")

float2d = xgrid.grid[float, 2]


@dataclass
class Config:
    rho: float
    nu: float
    dt: float
    dx: float
    dy: float


SIZE_X = SIZE_Y = 41

u = xgrid.Grid((SIZE_X, SIZE_Y), float)
v = xgrid.Grid((SIZE_X, SIZE_Y), float)
p = xgrid.Grid((SIZE_X, SIZE_Y), float)
b = xgrid.Grid((SIZE_X, SIZE_Y), float)


def init_random(x: xgrid.Grid):
    for i in range(x.shape[0]):
        for j in range(x.shape[1]):
            x.now[i, j] = random.random() * 0.01


u.boundary[0, :] = 1
u.boundary[:, 0] = 1
u.boundary[:, -1] = 1
u.boundary[-1, :] = 2

v.boundary[0, :] = 1
v.boundary[-1, :] = 1
v.boundary[:, 0] = 1
v.boundary[:, -1] = 1

init_random(u)
init_random(v)

p.boundary[:, -1] = 1
p.boundary[0, :] = 2
p.boundary[:, 0] = 3
p.boundary[-1, :] = 4

b.boundary[0, :] = 1
b.boundary[-1, :] = 1
b.boundary[:, 0] = 1
b.boundary[:, -1] = 1

x = numpy.linspace(0, 2, SIZE_X)
y = numpy.linspace(0, 2, SIZE_Y)
X, Y = numpy.meshgrid(x, y)

config = Config(1.0, 0.1, 0.001, 2 / (SIZE_X - 1), 2 / (SIZE_Y - 1))


def build_up_b(b, rho, dt, u, v, dx, dy):
    b[1:-1, 1:-1] = (rho * (1 / dt *
                            ((u[1:-1, 2:] - u[1:-1, 0:-2]) /
                             (2 * dx) + (v[2:, 1:-1] - v[0:-2, 1:-1]) / (2 * dy)) -
                            ((u[1:-1, 2:] - u[1:-1, 0:-2]) / (2 * dx))**2 -
                            2 * ((u[2:, 1:-1] - u[0:-2, 1:-1]) / (2 * dy) *
                                 (v[1:-1, 2:] - v[1:-1, 0:-2]) / (2 * dx)) -
                            ((v[2:, 1:-1] - v[0:-2, 1:-1]) / (2 * dy))**2))

    return b


@xgrid.kernel()
def build_up_b_kernel(b: float2d, u: float2d, v: float2d, cfg: Config) -> None:
    b[0, 0] = (cfg.rho * (1.0 / cfg.dt *
                          ((u[0, 1] - u[0, -1]) /
                           (2.0 * cfg.dx) + (v[1, 0] - v[-1, 0]) / (2.0 * cfg.dy)) -
                          ((u[0, 1] - u[0, -1]) / (2.0 * cfg.dx))**2.0 -
                          2.0 * ((u[1, 0] - u[-1, 0]) / (2.0 * cfg.dy) *
                                 (v[0, 1] - v[0, -1]) / (2.0 * cfg.dx)) -
                          ((v[1, 0] - v[-1, 0]) / (2.0 * cfg.dy))**2.0))


p_ref = numpy.zeros((SIZE_X, SIZE_Y))
b_ref = numpy.zeros((SIZE_X, SIZE_Y))

b_ref = build_up_b(b_ref, config.rho, config.dt,
                   u.now.copy(), v.now.copy(), config.dx, config.dy)

build_up_b_kernel(b, u, v, config)

pyplot.subplot(1, 3, 1)
pyplot.imshow(b.now)
pyplot.subplot(1, 3, 2)
pyplot.imshow(b_ref)
pyplot.subplot(1, 3, 3)
pyplot.imshow(b.now - b_ref)
pyplot.xlabel('X')
pyplot.ylabel('Y')

pyplot.savefig("imgs/cavity.png")
