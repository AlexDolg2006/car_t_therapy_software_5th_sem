#include "../model/car_t_model.h"

// Один шаг явного метода Эйлера.
// s — текущее состояние, d — уже посчитанные правые части,
// dt — шаг по времени.
inline void euler_step(State& s, const State& d, double dt, int n) {
    for (int k = 0; k < n; ++k) {
        s.C[k]   = std::max(0.0, s.C[k]   + d.C[k]   * dt);
        s.T[k]   = std::max(0.0, s.T[k]   + d.T[k]   * dt);
        s.I[k]   = std::max(0.0, s.I[k]   + d.I[k]   * dt);
        s.a_t[k] = std::min(1.0, std::max(0.0, s.a_t[k] + d.a_t[k] * dt));
        s.Ch[k]  = std::max(0.0, s.Ch[k]  + d.Ch[k]  * dt);
        s.Im[k]  = std::max(0.0, s.Im[k]  + d.Im[k]  * dt);
    }
}