#pragma once
#include <vector>
#include <cmath>

extern std::vector<double> vessel_x;
extern std::vector<double> vessel_y;

extern double DAY_CART_INJECTION;
extern double DAY_CHEMO_START;
extern double DAY_IMMUNO_START;

// Ширина сглаживания импульсов по времени (дни). 0 = исходные разрывные.
extern double TIME_SMOOTH;

void init_vessels(int N, int seed, double Lx, double Ly);

double uC (double t, double x, double y);
double uCh(double t, double x, double y);
double uIm(double t, double x, double y);