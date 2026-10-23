#pragma once
#include "../model/car_t_model.h"
#include <algorithm>
#include <cmath>

// ─────────────────────────────────────────────────────────────
// Классический метод Рунге–Кутты 4-го порядка для системы 6 PDE.
//
// На каждом шаге:
//     k1 = f(u^n,        t^n)
//     k2 = f(u^n + dt/2·k1, t^n + dt/2)
//     k3 = f(u^n + dt/2·k2, t^n + dt/2)
//     k4 = f(u^n + dt·k3,   t^n + dt)
//     u^{n+1} = u^n + dt/6 · (k1 + 2k2 + 2k3 + k4)
//
// Требует 4 вызова rhs() на шаг.
// ─────────────────────────────────────────────────────────────

// Сложение: out = a + c · b  (поэлементно, для всех 6 полей)
inline void state_axpy(State& out,
                       const State& a,
                       const State& b,
                       double c, int n) {
    for (int k = 0; k < n; ++k) {
        out.C[k]   = a.C[k]   + c * b.C[k];
        out.T[k]   = a.T[k]   + c * b.T[k];
        out.I[k]   = a.I[k]   + c * b.I[k];
        out.a_t[k] = a.a_t[k] + c * b.a_t[k];
        out.Ch[k]  = a.Ch[k]  + c * b.Ch[k];
        out.Im[k]  = a.Im[k]  + c * b.Im[k];
    }
}

// Поэлементная линейная комбинация: out = u + dt/6·(k1 + 2k2 + 2k3 + k4)
inline void rk4_combine(State& out,
                        const State& u,
                        const State& k1, const State& k2,
                        const State& k3, const State& k4,
                        double dt, int n) {
    double f = dt / 6.0;
    for (int k = 0; k < n; ++k) {
        out.C[k]   = u.C[k]   + f * (k1.C[k]   + 2*k2.C[k]   + 2*k3.C[k]   + k4.C[k]);
        out.T[k]   = u.T[k]   + f * (k1.T[k]   + 2*k2.T[k]   + 2*k3.T[k]   + k4.T[k]);
        out.I[k]   = u.I[k]   + f * (k1.I[k]   + 2*k2.I[k]   + 2*k3.I[k]   + k4.I[k]);
        out.a_t[k] = u.a_t[k] + f * (k1.a_t[k] + 2*k2.a_t[k] + 2*k3.a_t[k] + k4.a_t[k]);
        out.Ch[k]  = u.Ch[k]  + f * (k1.Ch[k]  + 2*k2.Ch[k]  + 2*k3.Ch[k]  + k4.Ch[k]);
        out.Im[k]  = u.Im[k]  + f * (k1.Im[k]  + 2*k2.Im[k]  + 2*k3.Im[k]  + k4.Im[k]);
    }
}

// Обрезка по физическим границам
inline void rk4_clamp(State& s, int n) {
    for (int k = 0; k < n; ++k) {
        if (s.C[k]   < 0.0) s.C[k]   = 0.0;
        if (s.T[k]   < 0.0) s.T[k]   = 0.0;
        if (s.I[k]   < 0.0) s.I[k]   = 0.0;
        if (s.a_t[k] < 0.0) s.a_t[k] = 0.0;
        if (s.a_t[k] > 1.0) s.a_t[k] = 1.0;
        if (s.Ch[k]  < 0.0) s.Ch[k]  = 0.0;
        if (s.Im[k]  < 0.0) s.Im[k]  = 0.0;
    }
}

// Один шаг РК4
inline void rk4_step(State& s, const Grid& g, const ModelParams& p,
                     double t, double dt, int n) {
    State k1(n), k2(n), k3(n), k4(n);
    State tmp(n);

    // k1 = f(u, t)
    rhs(s, k1, g, p, t);

    // k2 = f(u + dt/2 · k1, t + dt/2)
    state_axpy(tmp, s, k1, 0.5 * dt, n);
    rhs(tmp, k2, g, p, t + 0.5 * dt);

    // k3 = f(u + dt/2 · k2, t + dt/2)
    state_axpy(tmp, s, k2, 0.5 * dt, n);
    rhs(tmp, k3, g, p, t + 0.5 * dt);

    // k4 = f(u + dt · k3, t + dt)
    state_axpy(tmp, s, k3, dt, n);
    rhs(tmp, k4, g, p, t + dt);

    // u^{n+1} = u + dt/6 · (k1 + 2k2 + 2k3 + k4)
    State s_new(n);
    rk4_combine(s_new, s, k1, k2, k3, k4, dt, n);
    rk4_clamp(s_new, n);

    s = s_new;
}