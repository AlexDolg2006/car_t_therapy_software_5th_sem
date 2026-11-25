#include "sources.h"
#include <cstdlib>
#include <iostream>
#include <algorithm>

std::vector<double> vessel_x;
std::vector<double> vessel_y;

double DAY_CART_INJECTION = 0.0;
double DAY_CHEMO_START    = 30.0;
double DAY_IMMUNO_START   = 30.0;
double TIME_SMOOTH        = 0.0;

static double DOMAIN_Lx = 100.0;
static double DOMAIN_Ly = 100.0;

void init_vessels(int N, int seed, double Lx, double Ly) {
    DOMAIN_Lx = Lx;
    DOMAIN_Ly = Ly;

    vessel_x.clear();
    vessel_y.clear();
    srand(seed);

    for (int v = 0; v < N; ++v) {
        double x = (rand() / double(RAND_MAX)) * Lx;
        double y = (rand() / double(RAND_MAX)) * Ly;
        vessel_x.push_back(x);
        vessel_y.push_back(y);
    }
    std::cout << "Инициализировано " << N << " сосудов в [0,"
              << Lx << "]x[0," << Ly << "]\n";
}

static inline double vessel_radius() {
    return 0.1 * std::min(DOMAIN_Lx, DOMAIN_Ly);
}

// ── Временные профили ────────────────────────────────────────
// Ступенька «t >= t0»
static inline double step_on(double t, double t0) {
    if (TIME_SMOOTH <= 0.0) return (t >= t0) ? 1.0 : 0.0;
    return 0.5 * (1.0 + std::tanh((t - t0) / TIME_SMOOTH));
}

// Окно [a, b]
static inline double window(double t, double a, double b) {
    if (TIME_SMOOTH <= 0.0) return (t < a || t > b) ? 0.0 : 1.0;
    return 0.5 * (std::tanh((t - a) / TIME_SMOOTH)
                - std::tanh((t - b) / TIME_SMOOTH));
}

// Еженедельный импульс. Исходный: 5 при fmod(t,7)<0.5, иначе 0 (доза 2.5 за неделю).
// Гладкий: гауссиан с той же дозой, центр 0.25 дня после начала недели.
static inline double weekly_pulse(double t) {
    if (TIME_SMOOTH <= 0.0) return (std::fmod(t, 7.0) < 0.5) ? 5.0 : 0.0;
    const double sg = TIME_SMOOTH;
    const double k  = std::round((t - 0.25) / 7.0);
    const double d  = t - 0.25 - 7.0 * k;
    const double z  = d * d / (sg * sg);
    if (z > 40.0) return 0.0;
    return 2.5 / (sg * std::sqrt(M_PI)) * std::exp(-z);
}

double uC(double t, double x, double y) {
    double w = window(t, DAY_CART_INJECTION, DAY_CART_INJECTION + 2.0);
    if (w < 1e-14) return 0.0;
    double source = 0.0;
    const double strength = 0.05;
    const double radius   = vessel_radius();
    for (size_t v = 0; v < vessel_x.size(); ++v) {
        double dx = x - vessel_x[v];
        double dy = y - vessel_y[v];
        double dist = std::sqrt(dx*dx + dy*dy);
        if (dist < radius)
            source += strength * std::exp(-dist*dist / (radius*radius*0.2));
    }
    return w * source;
}

double uCh(double t, double x, double y) {
    double tf = step_on(t, DAY_CHEMO_START) * weekly_pulse(t);
    if (tf < 1e-14) return 0.0;
    double source = 0.0;
    const double strength = 0.03 * tf;
    const double radius   = vessel_radius();
    for (size_t v = 0; v < vessel_x.size(); ++v) {
        double dx = x - vessel_x[v];
        double dy = y - vessel_y[v];
        double dist = std::sqrt(dx*dx + dy*dy);
        if (dist < radius)
            source += strength * (1.0 - dist / radius);
    }
    return source;
}

double uIm(double t, double x, double y) {
    double tf = step_on(t, DAY_IMMUNO_START) * weekly_pulse(t);
    if (tf < 1e-14) return 0.0;
    double source = 0.0;
    const double strength = 0.02 * tf;
    const double radius   = vessel_radius();
    for (size_t v = 0; v < vessel_x.size(); ++v) {
        double dx = x - vessel_x[v];
        double dy = y - vessel_y[v];
        double dist = std::sqrt(dx*dx + dy*dy);
        if (dist < radius)
            source += strength * std::exp(-dist*dist / (radius*radius));
    }
    return source;
}