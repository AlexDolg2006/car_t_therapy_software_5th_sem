#pragma once
#include "../model/car_t_model.h"
#include <cmath>
#include <algorithm>

// ─────────────────────────────────────────────────────────────
// Неявный метод Эйлера для системы 6 уравнений в частных производных.
//
// Схема: u^{n+1} = u^n + dt · f(u^{n+1})
// Решение: простые итерации (fixed-point):
//     u^{(0)}   = u^n                    (начальное приближение)
//     u^{(k+1)} = u^n + dt · f(u^{(k)})  (пока не сойдётся)
//
// Критерий сходимости: max |u^{(k+1)} − u^{(k)}| < tol
// ─────────────────────────────────────────────────────────────

struct ImplicitConfig {
    int    max_iter = 20;     // максимум итераций на шаг
    double tol      = 1e-6;   // порог сходимости
};

// Вспомогательное: max-норма разности двух состояний
inline double state_diff_max(const State& a, const State& b, int n) {
    double m = 0.0;
    for (int k = 0; k < n; ++k) {
        m = std::max(m, std::fabs(a.C[k]   - b.C[k]));
        m = std::max(m, std::fabs(a.T[k]   - b.T[k]));
        m = std::max(m, std::fabs(a.I[k]   - b.I[k]));
        m = std::max(m, std::fabs(a.a_t[k] - b.a_t[k]));
        m = std::max(m, std::fabs(a.Ch[k]  - b.Ch[k]));
        m = std::max(m, std::fabs(a.Im[k]  - b.Im[k]));
    }
    return m;
}

// Копирование с обрезкой по физическим границам
inline void clamp_state(State& s, int n) {
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

inline void implicit_euler_step(State& s, const Grid& g,
                                const ModelParams& p,
                                double t_new, double dt, int n,
                                const ImplicitConfig& ic = ImplicitConfig{},
                                int* out_iters = nullptr)
{
    State s_old = s;              // u^n — «замороженное» предыдущее состояние
    State s_k   = s;              // u^{(k)} — текущая итерация
    State f_k(n);                 // f(u^{(k)})

    int iters = 0;
    for (int it = 0; it < ic.max_iter; ++it) {
        // f(u^{(k)}) — считаем правую часть с текущей итерацией
        rhs(s_k, f_k, g, p, t_new);

        // u^{(k+1)} = u^n + dt · f(u^{(k)})
        State s_next = s_old;
        for (int k = 0; k < n; ++k) {
            s_next.C[k]   = s_old.C[k]   + dt * f_k.C[k];
            s_next.T[k]   = s_old.T[k]   + dt * f_k.T[k];
            s_next.I[k]   = s_old.I[k]   + dt * f_k.I[k];
            s_next.a_t[k] = s_old.a_t[k] + dt * f_k.a_t[k];
            s_next.Ch[k]  = s_old.Ch[k]  + dt * f_k.Ch[k];
            s_next.Im[k]  = s_old.Im[k]  + dt * f_k.Im[k];
        }

        // физические ограничения
        clamp_state(s_next, n);

        // проверяем сходимость
        double diff = state_diff_max(s_next, s_k, n);
        s_k = s_next;
        iters = it + 1;

        if (diff < ic.tol) break;
    }

    // результат шага
    s = s_k;
    if (out_iters) *out_iters = iters;
}