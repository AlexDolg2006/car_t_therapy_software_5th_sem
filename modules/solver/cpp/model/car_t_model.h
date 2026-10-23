#pragma once
#include <vector>
#include <cmath>
#include "sources.h"

struct Grid {
    int Nx = 100, Ny = 100;
    double Lx = 100.0, Ly = 100.0;
    double dx = 0.0, dy = 0.0;
    double x_center = 0.0, y_center = 0.0;

    void init(int nx, int ny, double lx, double ly) {
        Nx = nx; Ny = ny; Lx = lx; Ly = ly;
        dx = Lx / (Nx - 1);
        dy = Ly / (Ny - 1);
        x_center = Lx / 2.0;   // ← координата в мм, не индекс
        y_center = Ly / 2.0;
    }
    inline int idx(int i, int j) const { return i * Ny + j; }
};

struct ModelParams {
    double Dc = 0.05,  Dt = 0.00005;
    double Dch = 0.015, Dim = 0.015;
    double rc = 0.5,  rt = 0.1;
    double hc = 0.001, ht = 0.004;
    double kct = 0.64, ki = 0.03;
    double uc = 0.1,  ut = 0.10, ui = 0.2;
    double a = 0.1,   b = 0.1,   g = 0.05;
    double deltach = 0.04, deltaim = 0.03;
};

struct State {
    std::vector<double> C, T, I, a_t, Ch, Im;

    explicit State(int n = 0)
        : C(n, 0.0), T(n, 0.0), I(n, 0.0),
          a_t(n, 0.0), Ch(n, 0.0), Im(n, 0.0) {}

    State clone() const { return *this; }
};

inline double laplacian(const std::vector<double>& F,
                        int i, int j, const Grid& g) {
    int ip = (i + 1 < g.Nx) ? i + 1 : i;
    int im = (i - 1 >= 0)    ? i - 1 : i;
    int jp = (j + 1 < g.Ny) ? j + 1 : j;
    int jm = (j - 1 >= 0)    ? j - 1 : j;

    auto idx = [&](int a, int b){ return g.idx(a,b); };

    return (F[idx(ip,j)] - 2*F[idx(i,j)] + F[idx(im,j)]) / (g.dx*g.dx)
         + (F[idx(i,jp)] - 2*F[idx(i,j)] + F[idx(i,jm)]) / (g.dy*g.dy);
}

inline void rhs(const State& s, State& d, const Grid& g,
                const ModelParams& p, double time) {
    for (int i = 0; i < g.Nx; ++i) {
        for (int j = 0; j < g.Ny; ++j) {
            int c = g.idx(i, j);

            double lapC  = laplacian(s.C,  i, j, g);
            double lapT  = laplacian(s.T,  i, j, g);
            double lapCh = laplacian(s.Ch, i, j, g);
            double lapIm = laplacian(s.Im, i, j, g);

            double x = i * g.dx;
            double y = j * g.dy;

            d.C[c] = p.Dc * lapC
                   + p.rc * s.C[c] * (1.0 - s.C[c])
                   - p.kct * s.C[c] * s.T[c] * (1.0 - s.a_t[c])
                   - p.ki * s.C[c] * s.I[c]
                   - p.hc * s.C[c]
                   - p.uc * s.Ch[c] * s.C[c]
                   + uC(time, x, y);

            d.T[c] = p.Dt * lapT
                   + p.rt * s.T[c] * (1.0 - s.T[c])
                   - p.kct * s.C[c] * s.T[c] * (1.0 - s.a_t[c])
                   - p.ht * s.T[c]
                   - p.ut * s.Ch[c] * s.T[c];

            d.I[c] = -p.a * s.I[c] + p.b * s.T[c]
                   - p.ui * s.Im[c] * s.I[c];

            d.a_t[c] = p.g * s.T[c] * (1.0 - s.a_t[c]);

            d.Ch[c] = p.Dch * lapCh
                    - p.deltach * s.Ch[c]
                    + uCh(time, x, y);

            d.Im[c] = p.Dim * lapIm
                    - p.deltaim * s.Im[c]
                    + uIm(time, x, y);
        }
    }
}

inline void init_state(State& s, const Grid& g,
                       double T0_volume, double sigma,
                       double xc, double yc) {
    double gauss_sum = 0.0;
    for (int i = 0; i < g.Nx; ++i)
        for (int j = 0; j < g.Ny; ++j) {
            double r2 = std::pow(i*g.dx - xc, 2)
                      + std::pow(j*g.dy - yc, 2);
            gauss_sum += std::exp(-sigma * r2) * g.dx * g.dy;
        }
    double peak = T0_volume / gauss_sum;

    for (int i = 0; i < g.Nx; ++i)
        for (int j = 0; j < g.Ny; ++j) {
            double r2 = std::pow(i*g.dx - xc, 2)
                      + std::pow(j*g.dy - yc, 2);
            s.T[g.idx(i,j)] = peak * std::exp(-sigma * r2);
        }
}