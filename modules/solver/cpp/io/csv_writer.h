#pragma once
#include <fstream>
#include <string>
#include "../model/car_t_model.h"

inline void write_csv_row(std::ofstream& f, double t, const Grid& g,
                          int i, int j, const State& s) {
    int c = g.idx(i, j);
    f << t << "," << (i * g.dx) << "," << (j * g.dy) << ","
      << s.C[c]   << "," << s.T[c]  << "," << s.I[c]  << ","
      << s.a_t[c] << "," << s.Ch[c] << "," << s.Im[c] << "\n";
}

inline void write_csv_header(std::ofstream& f) {
    f << "time,x,y,C,T,I,a_t,Ch,Im\n";
}