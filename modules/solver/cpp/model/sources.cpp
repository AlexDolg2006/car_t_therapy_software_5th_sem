#include "sources.h"
#include <cstdlib>
#include <iostream>
#include <algorithm>

std::vector<double> vessel_x;
std::vector<double> vessel_y;

double DAY_CART_INJECTION = 0.0;
double DAY_CHEMO_START    = 30.0;
double DAY_IMMUNO_START   = 30.0;

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

double uC(double t, double x, double y) {
    if (t < DAY_CART_INJECTION || t > DAY_CART_INJECTION + 2.0) return 0.0;
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
    return source;
}

double uCh(double t, double x, double y) {
    if (t < DAY_CHEMO_START) return 0.0;
    double tf = (std::fmod(t, 7.0) < 0.5) ? 5.0 : 0.0;
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
    if (t < DAY_IMMUNO_START) return 0.0;
    double tf = (std::fmod(t, 7.0) < 0.5) ? 5.0 : 0.0;
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