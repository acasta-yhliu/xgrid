from dataclasses import dataclass
import tqdm
import xgrid
from matplotlib import pyplot, animation
import numpy

xgrid.init(cacheroot=".xgridtest", parallel=True, precision="float")

float2d = xgrid.grid[float, 2]  # type: ignore


@dataclass
class Config:
    rho: float
    nu: float
    dt: float
    dx: float
    dy: float


SIZE_X = SIZE_Y = 51

u = xgrid.Grid((SIZE_X, SIZE_Y), float)
v = xgrid.Grid((SIZE_X, SIZE_Y), float)
p = xgrid.Grid((SIZE_X, SIZE_Y), float)
pt = xgrid.Grid((SIZE_X, SIZE_Y), float)
b = xgrid.Grid((SIZE_X, SIZE_Y), float)


u.boundary[0, :] = 1
u.boundary[:, 0] = 1
u.boundary[:, -1] = 1
u.boundary[-1, :] = 2

v.boundary[0, :] = 1
v.boundary[-1, :] = 1
v.boundary[:, 0] = 1
v.boundary[:, -1] = 1

p.boundary[:, -1] = 1
p.boundary[0, :] = 2
p.boundary[:, 0] = 3
p.boundary[-1, :] = 4

pt.boundary[:, -1] = 1
pt.boundary[0, :] = 2
pt.boundary[:, 0] = 3
pt.boundary[-1, :] = 4

b.boundary[0, :] = 1
b.boundary[-1, :] = 1
b.boundary[:, 0] = 1
b.boundary[:, -1] = 1

x = numpy.linspace(0, 2, SIZE_X)
y = numpy.linspace(0, 2, SIZE_Y)
X, Y = numpy.meshgrid(x, y)

config = Config(1.0, 0.1, 0.001, 2 / (SIZE_X - 1), 2 / (SIZE_Y - 1))


@xgrid.kernel()
def cavity_kernel(b: float2d, p: float2d, pt: float2d, u: float2d, v: float2d, cfg: Config) -> None:
    b[0, 0] = (cfg.rho * (1.0 / cfg.dt *
                          ((u[0, 1] - u[0, -1]) /
                           (2.0 * cfg.dx) + (v[1, 0] - v[-1, 0]) / (2.0 * cfg.dy)) -
                          ((u[0, 1] - u[0, -1]) / (2.0 * cfg.dx))**2.0 -
                          2.0 * ((u[1, 0] - u[-1, 0]) / (2.0 * cfg.dy) *
                                 (v[0, 1] - v[0, -1]) / (2.0 * cfg.dx)) -
                          ((v[1, 0] - v[-1, 0]) / (2.0 * cfg.dy))**2.0))

    p[0, 0] = (((p[0, 1] + p[0, -1]) * cfg.dy**2.0 +
                (p[1, 0] + p[-1, 0]) * cfg.dx**2.0) /
               (2.0 * (cfg.dx**2.0 + cfg.dy**2.0)) -
               cfg.dx**2.0 * cfg.dy**2.0 / (2.0 * (cfg.dx**2.0 + cfg.dy**2.0)) *
               b[0, 0][0])

    with xgrid.boundary(p, 1):
        p[0, 0] = p[0, -1][0]  # dp/dx = 0 at x = 2
    with xgrid.boundary(p, 2):
        p[0, 0] = p[1, 0][0]   # dp/dy = 0 at y = 0
    with xgrid.boundary(p, 3):
        p[0, 0] = p[0, 1][0]   # dp/dx = 0 at x = 0
    with xgrid.boundary(p, 4):
        p[0, 0] = 0.0

    for _ in range(0, 50):
        pt[0, 0] = (((p[0, 1][0] + p[0, -1][0]) * cfg.dy**2.0 +
                    (p[1, 0][0] + p[-1, 0][0]) * cfg.dx**2.0) /
                    (2.0 * (cfg.dx**2.0 + cfg.dy**2.0)) -
                    cfg.dx**2.0 * cfg.dy**2.0 / (2.0 * (cfg.dx**2.0 + cfg.dy**2.0)) *
                    b[0, 0][0])

        with xgrid.boundary(pt, 1):
            pt[0, 0] = pt[0, -1][0]  # dp/dx = 0 at x = 2
        with xgrid.boundary(pt, 2):
            pt[0, 0] = pt[1, 0][0]   # dp/dy = 0 at y = 0
        with xgrid.boundary(pt, 3):
            pt[0, 0] = pt[0, 1][0]   # dp/dx = 0 at x = 0
        with xgrid.boundary(pt, 4):
            pt[0, 0] = 0.0

        p[0, 0] = (((pt[0, 1][0] + pt[0, -1][0]) * cfg.dy**2.0 +
                    (pt[1, 0][0] + pt[-1, 0][0]) * cfg.dx**2.0) /
                   (2.0 * (cfg.dx**2.0 + cfg.dy**2.0)) -
                   cfg.dx**2.0 * cfg.dy**2.0 / (2.0 * (cfg.dx**2.0 + cfg.dy**2.0)) *
                   b[0, 0][0])

        with xgrid.boundary(p, 1):
            p[0, 0] = p[0, -1][0]  # dp/dx = 0 at x = 2
        with xgrid.boundary(p, 2):
            p[0, 0] = p[1, 0][0]   # dp/dy = 0 at y = 0
        with xgrid.boundary(p, 3):
            p[0, 0] = p[0, 1][0]   # dp/dx = 0 at x = 0
        with xgrid.boundary(p, 4):
            p[0, 0] = 0.0

        u[0, 0] = (u[0, 0] -
                   u[0, 0] * cfg.dt / cfg.dx *
                   (u[0, 0] - u[0, -1]) -
                   v[0, 0] * cfg.dt / cfg.dy *
                   (u[0, 0] - u[-1, 0]) -
                   cfg.dt / (2.0 * cfg.rho * cfg.dx) * (p[0, 1][0] - p[0, -1][0]) +
                   cfg.nu * (cfg.dt / cfg.dx**2.0 *
                             (u[0, 1] - 2.0 * u[0, 0] + u[0, -1]) +
                             cfg.dt / cfg.dy**2.0 *
                             (u[1, 0] - 2.0 * u[0, 0] + u[-1, 0])))

        v[0, 0] = (v[0, 0] -
                   u[0, 0] * cfg.dt / cfg.dx *
                   (v[0, 0] - v[0, -1]) -
                   v[0, 0] * cfg.dt / cfg.dy *
                   (v[0, 0] - v[-1, 0]) -
                   cfg.dt / (2.0 * cfg.rho * cfg.dy) * (p[1, 0][0] - p[-1, 0][0]) +
                   cfg.nu * (cfg.dt / cfg.dx**2.0 *
                             (v[0, 1] - 2.0 * v[0, 0] + v[0, -1]) +
                             cfg.dt / cfg.dy**2.0 *
                             (v[1, 0] - 2.0 * v[0, 0] + v[-1, 0])))

        with xgrid.boundary(u, 1):
            u[0, 0] = 0.0

        with xgrid.boundary(u, 2):
            u[0, 0] = 1.0

        with xgrid.boundary(v, 1):
            v[0, 0] = 0.0


TIME = 1
FRAMES = int(TIME / config.dt)

fig = pyplot.figure(figsize=(11, 7), dpi=100)


def cavity_tick(time_step):
    pyplot.clf()
    pyplot.imshow(p.now)
    cavity_kernel(b, p, pt, u, v, config)

print("saving image to imgs/cavity.gif")
ani = animation.FuncAnimation(fig, cavity_tick, frames=tqdm.tqdm(range(FRAMES)), interval=1, repeat_delay=10)
ani.save("imgs/cavity.gif", writer="pillow")
