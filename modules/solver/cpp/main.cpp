#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <cmath>
#include <algorithm>

#include "common/params.h"
#include "model/car_t_model.h"
#include "model/sources.h"
#include "io/csv_writer.h"
#include "methods/explicit_euler.cpp"
#include "methods/implicit_euler.cpp"
#include "methods/runge_kutta_4.cpp"

int main(int argc, char** argv) {
    std::string out_csv  = "car-t-2d.csv";
    std::string params_f = "";
    std::string method   = "explicit_euler";

    double save_dt  = 0.0;     // 0 = как раньше (каждые 100 шагов)
    double smooth   = 0.0;     // 0 = исходные разрывные источники
    double imp_tol  = 1e-6;
    int    imp_iter = 20;

    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if      (a == "--out"      && i+1 < argc) out_csv  = argv[++i];
        else if (a == "--params"   && i+1 < argc) params_f = argv[++i];
        else if (a == "--method"   && i+1 < argc) method   = argv[++i];
        else if (a == "--save_dt"  && i+1 < argc) save_dt  = std::stod(argv[++i]);
        else if (a == "--smooth"   && i+1 < argc) smooth   = std::stod(argv[++i]);
        else if (a == "--tol"      && i+1 < argc) imp_tol  = std::stod(argv[++i]);
        else if (a == "--max_iter" && i+1 < argc) imp_iter = std::stoi(argv[++i]);
    }
    TIME_SMOOTH = smooth;

    Params P = params_f.empty() ? Params{} : load_params(params_f);

    int    Nx          = (int)P.getd("Nx", 100);
    int    Ny          = (int)P.getd("Ny", 100);
    double Lx          = P.getd("Lx", 100.0);
    double Ly          = P.getd("Ly", 100.0);
    int    num_vessels = (int)P.getd("num_vessels", 33);
    int    vessel_seed = (int)P.getd("vessel_seed", 42);

    double T0_volume = P.getd("T0_volume", 50.0);
    double sigma     = P.getd("sigma",     0.003);
    double x_center  = P.getd("x_center",  Lx / 2.0);
    double y_center  = P.getd("y_center",  Ly / 2.0);

    int    Nt = (int)P.getd("Nt", 2000);
    double Tt = P.getd("Tt", 400.0);
    double dt = Tt / Nt;

    std::cout << "=== C++ ПРОЧИТАЛ ===\n";
    std::cout << "  Nx=" << Nx << " Ny=" << Ny
              << " Lx=" << Lx << " Ly=" << Ly << "\n";
    std::cout << "  num_vessels=" << num_vessels
              << " vessel_seed=" << vessel_seed << "\n";
    std::cout << "  x_center=" << x_center
              << " y_center=" << y_center << "\n";
    std::cout << "  T0_volume=" << T0_volume
              << " sigma=" << sigma << "\n";
    std::cout << "  Nt=" << Nt << " Tt=" << Tt << " dt=" << dt << "\n";
    std::cout << "  smooth=" << smooth << " save_dt=" << save_dt << "\n";
    std::cout << "====================\n";

    Grid g;
    g.init(Nx, Ny, Lx, Ly);

    ModelParams mp;
    mp.Dc  = P.getd("Dc",  mp.Dc);   mp.Dt  = P.getd("Dt",  mp.Dt);
    mp.Dch = P.getd("Dch", mp.Dch);  mp.Dim = P.getd("Dim", mp.Dim);
    mp.rc  = P.getd("rc",  mp.rc);   mp.rt  = P.getd("rt",  mp.rt);
    mp.hc  = P.getd("hc",  mp.hc);   mp.ht  = P.getd("ht",  mp.ht);
    mp.kct = P.getd("kct", mp.kct);  mp.ki  = P.getd("ki",  mp.ki);
    mp.uc  = P.getd("uc",  mp.uc);   mp.ut  = P.getd("ut",  mp.ut);
    mp.ui  = P.getd("ui",  mp.ui);
    mp.a   = P.getd("a",   mp.a);    mp.b   = P.getd("b",   mp.b);
    mp.g   = P.getd("g",   mp.g);
    mp.deltach  = P.getd("deltach",  mp.deltach);
    mp.deltaim  = P.getd("deltaim",  mp.deltaim);

    DAY_CART_INJECTION = P.getd("day_cart",   0.0);
    DAY_CHEMO_START    = P.getd("day_chemo",  30.0);
    DAY_IMMUNO_START   = P.getd("day_immuno", 30.0);

    init_vessels(num_vessels, vessel_seed, Lx, Ly);

    int n = g.Nx * g.Ny;
    State s(n);
    init_state(s, g, T0_volume, sigma, x_center, y_center);

    // ── Проверка устойчивости ─────────────────────────────
    if (method == "explicit_euler" || method == "rk4") {
        double hx = Lx / Nx;
        double hy = Ly / Ny;

        double Dmax = std::max({mp.Dc, mp.Dt, mp.Dch, mp.Dim});
        double rmax = std::max({mp.rc, mp.rt, mp.kct, mp.ki,
                                mp.uc, mp.ut, mp.ui});

        double c = (method == "rk4") ? 2.785 : 2.0;

        double dt_diff = c / (2.0 * (Dmax/(hx*hx) + Dmax/(hy*hy)));
        double dt_react = (rmax > 0.0) ? c / rmax : 1e300;
        double dt_crit = std::min(dt_diff, dt_react);

        std::cout << "=== ПРОВЕРКА УСТОЙЧИВОСТИ (" << method << ") ===\n";
        std::cout << "  dt_crit = " << dt_crit << "  (dt = " << dt << ")\n";

        if (dt > dt_crit) {
            int recommended_Nt = (int)std::ceil(Tt / dt_crit) + 1;
            std::cerr << "\n[ERROR] Нарушено условие устойчивости!\n"
                      << "Шаг по времени dt = " << dt
                      << " больше критического dt_crit = " << dt_crit << ".\n"
                      << "Решение будет неустойчивым (взорвется).\n"
                      << "Пожалуйста, увеличьте Nt (минимум до " << recommended_Nt
                      << ") или используйте неявный метод.\n\n";
            return 1;
        }
        std::cout << "  [OK] Условие устойчивости выполнено.\n";
        std::cout << "==================================================\n";
    }

    std::ofstream f(out_csv);
    if (!f) { std::cerr << "cannot open " << out_csv << "\n"; return 1; }
    write_csv_header(f);

    std::cout << "Запуск метода: " << method << "\n";
    std::cout << "Сетка: " << g.Nx << "×" << g.Ny
              << "  Lx=" << Lx << "  Ly=" << Ly
              << "  Nt=" << Nt << "  dt=" << dt << " дней\n";
    std::cout << "Сосудов: " << num_vessels
              << "  seed=" << vessel_seed << "\n";

    // Сохранение: либо через равные промежутки времени (режим сравнения),
    // либо как раньше — каждые 100 шагов
    const bool compare_mode = (save_dt > 0.0);
    const int  save_every   = compare_mode
        ? std::max(1, (int)std::lround(save_dt / dt))
        : 100;

    auto dump = [&](double t) {
        for (int i = 0; i < g.Nx; ++i)
            for (int j = 0; j < g.Ny; ++j)
                write_csv_row(f, t, g, i, j, s);
    };

    ImplicitConfig ic;
    ic.max_iter = imp_iter;
    ic.tol      = imp_tol;

    // ── Цикл по времени ───────────────────────────────────
    for (int step = 0; step < Nt; ++step) {
        double t = step * dt;

        if (step % save_every == 0) {
            dump(t);
            if (!compare_mode)
                std::cout << "Сохранён шаг " << step << " из " << Nt << "\n";
        }

        if (method == "explicit_euler") {
            State d(n);
            rhs(s, d, g, mp, t);
            euler_step(s, d, dt, n);
        }
        else if (method == "implicit_euler") {
            int iters = 0;
            implicit_euler_step(s, g, mp, t + dt, dt, n, ic, &iters);
            if (step % 100 == 0 && !compare_mode) {
                std::cout << "  [implicit] step=" << step
                          << " iters=" << iters << "\n";
            }
        }
        else if (method == "rk4") {
            rk4_step(s, g, mp, t, dt, n);
        }
        else {
            std::cerr << "unknown method: " << method << "\n";
            return 1;
        }
    }

    // Конечный момент t = Tt (только в режиме сравнения,
    // чтобы обычный режим работал как раньше)
    if (compare_mode) dump(Nt * dt);

    std::cout << "Готово.\n";
    return 0;
}