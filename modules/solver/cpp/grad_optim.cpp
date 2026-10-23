#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <cmath>
#include <vector>
#include <algorithm>
#include <iomanip>
#include <random>
#include <cstring>

using namespace std;

// ── Параметры сетки и модели ────────────────────────────────
static int    Nx = 30;
static int    Ny = 30;
static int    Nt = 2000;
static double Lx = 100.0;
static double Ly = 100.0;
static double Tt = 400.0;
static double x_center = 50.0;
static double y_center = 50.0;
static double SIGMA = 0.003;

// Фиксированные коэффициенты (берутся из --params)
static double Dc = 0.05;
static double Dch = 0.015;
static double Dim = 0.015;
static double rc = 0.5;
static double hc = 0.001;
static double kct = 0.64;
static double ki = 0.03;
static double uc = 0.1;
static double ut = 0.10;
static double ui = 0.2;
static double deltach = 0.04;
static double deltaim = 0.03;

static double dx, dy, dt;
static double gauss_sum = 0.0;

#define idx(i,j) ((i)*(Ny) + (j))

struct ExperimentalData { double day; double volume; };

// ── Пространство поиска ─────────────────────────────────────
enum ParamId { P_DT=0, P_RT, P_HT, P_A, P_B, P_G, P_T0, N_PARAMS };
static const char* PARAM_NAMES[N_PARAMS] = {
    "Dt","rt","ht","a","b","g","T0_volume"
};

struct OptSpace {
    bool   optimize[N_PARAMS];
    double lo[N_PARAMS];
    double hi[N_PARAMS];
    double init[N_PARAMS];
    double step[N_PARAMS];

    OptSpace() {
        double dLo[N_PARAMS]   = {1e-5, 0.01, 0.001, 0.001, 0.001, 0.001,   1.0};
        double dHi[N_PARAMS]   = {1e-4, 0.2,  1.0,   1.0,   1.0,   1.0,   200.0};
        double dInit[N_PARAMS] = {0.00005, 0.05, 0.05, 0.10, 0.05, 0.01, 50.0};
        double dStep[N_PARAMS] = {1e-5, 0.02, 0.02, 0.02, 0.01, 0.005, 5.0};
        for (int i = 0; i < N_PARAMS; ++i) {
            optimize[i] = true;
            lo[i]   = dLo[i];
            hi[i]   = dHi[i];
            init[i] = dInit[i];
            step[i] = dStep[i];
        }
    }
};
static OptSpace SPACE;

void setup_grid() {
    dx = Lx / (Nx - 1);
    dy = Ly / (Ny - 1);
    dt = Tt / Nt;
}

void precompute_gauss_sum() {
    gauss_sum = 0.0;
    for(int i = 0; i < Nx; i++)
        for(int j = 0; j < Ny; j++) {
            double r2 = pow(i*dx - x_center, 2) + pow(j*dy - y_center, 2);
            gauss_sum += exp(-SIGMA * r2) * dx * dy;
        }
}

// ── Чтение CSV ──────────────────────────────────────────────
vector<ExperimentalData> load_csv(const string& path) {
    vector<ExperimentalData> data;
    ifstream f(path);
    if(!f) { cerr << "cannot open csv: " << path << "\n"; return data; }
    string line;
    while(getline(f, line)) {
        if(line.empty()) continue;
        if(line[0] == 'd' || line[0] == 'D' || line[0] == '#') continue;
        stringstream ss(line);
        string a, b;
        if(!getline(ss, a, ',')) continue;
        if(!getline(ss, b, ',')) continue;
        try { data.push_back({stod(a), stod(b)}); } catch(...) { continue; }
    }
    return data;
}

// ── Чтение плоского JSON с параметрами из GUI ───────────────
void load_params_json(const string& path) {
    ifstream pf(path);
    if(!pf) { cerr << "cannot open params: " << path << "\n"; return; }
    string line;
    while(getline(pf, line)) {
        auto c = line.find(':');
        if(c == string::npos) continue;
        auto strip = [](string s) {
            while(!s.empty() && (s.front()==' '||s.front()=='"'||
                                 s.front()=='\t'||s.front()=='{')) s.erase(s.begin());
            while(!s.empty() && (s.back()==' '||s.back()=='"'||
                                 s.back()==','||s.back()=='\n'||
                                 s.back()=='\r'||s.back()=='}')) s.pop_back();
            return s;
        };
        string key = strip(line.substr(0, c));
        string val = strip(line.substr(c + 1));
        if(key.empty() || val.empty()) continue;
        double v;
        try { v = stod(val); } catch(...) { continue; }
        if      (key == "Nx")          Nx = (int)v;
        else if (key == "Ny")          Ny = (int)v;
        else if (key == "Nt")          Nt = (int)v;
        else if (key == "Lx")          Lx = v;
        else if (key == "Ly")          Ly = v;
        else if (key == "Tt")          Tt = v;
        else if (key == "sigma")       SIGMA = v;
        else if (key == "x_center")    x_center = v;
        else if (key == "y_center")    y_center = v;
        else if (key == "Dc")          Dc = v;
        else if (key == "Dch")         Dch = v;
        else if (key == "Dim")         Dim = v;
        else if (key == "rc")          rc = v;
        else if (key == "hc")          hc = v;
        else if (key == "kct")         kct = v;
        else if (key == "ki")          ki = v;
        else if (key == "uc")          uc = v;
        else if (key == "ut")          ut = v;
        else if (key == "ui")          ui = v;
        else if (key == "deltach")     deltach = v;
        else if (key == "deltaim")     deltaim = v;
        else if (key == "Dt")          SPACE.init[P_DT] = v;
        else if (key == "rt")          SPACE.init[P_RT] = v;
        else if (key == "ht")          SPACE.init[P_HT] = v;
        else if (key == "a")           SPACE.init[P_A]  = v;
        else if (key == "b")           SPACE.init[P_B]  = v;
        else if (key == "g")           SPACE.init[P_G]  = v;
        else if (key == "T0_volume")   SPACE.init[P_T0] = v;
    }
}

// ── Чтение optim_space.json ─────────────────────────────────
void load_space_json(const string& path) {
    ifstream f(path);
    if(!f) { cerr << "cannot open space: " << path << "\n"; return; }
    string line, cur;
    while(getline(f, line)) {
        auto q1 = line.find('"');
        if(q1 != string::npos) {
            auto q2 = line.find('"', q1 + 1);
            if(q2 != string::npos) {
                string k = line.substr(q1 + 1, q2 - q1 - 1);
                for(int i = 0; i < N_PARAMS; ++i)
                    if(k == PARAM_NAMES[i]) { cur = k; break; }
            }
        }
        if(cur.empty()) continue;
        int id = -1;
        for(int i = 0; i < N_PARAMS; ++i) if(cur == PARAM_NAMES[i]) id = i;
        if(id < 0) continue;

        auto parseNum = [&](const char* field, double& dst) {
            string tag = string("\"") + field + "\"";
            auto p = line.find(tag);
            if(p == string::npos) return;
            auto c = line.find(':', p);
            if(c == string::npos) return;
            string v = line.substr(c + 1);
            auto end = v.find_first_of(",}");
            if(end != string::npos) v = v.substr(0, end);
            try { dst = stod(v); } catch(...) {}
        };
        auto parseOn = [&]() {
            auto p = line.find("\"on\"");
            if(p == string::npos) return;
            auto c = line.find(':', p);
            if(c == string::npos) return;
            string v = line.substr(c + 1);
            auto end = v.find_first_of(",}");
            if(end != string::npos) v = v.substr(0, end);
            try { SPACE.optimize[id] = stoi(v) != 0; } catch(...) {}
        };
        parseOn();
        parseNum("lo",   SPACE.lo[id]);
        parseNum("hi",   SPACE.hi[id]);
        parseNum("init", SPACE.init[id]);
        parseNum("step", SPACE.step[id]);
    }
}

// ── Функция ошибки ──────────────────────────────────────────
double get_error(double pDt, double prt, double pht,
                 double pa,  double pb,  double pg,
                 double T0_vol,
                 const vector<ExperimentalData>& data)
{
    vector<double> T(Nx*Ny), I(Nx*Ny, 0.0), a_t(Nx*Ny, 0.0);
    vector<double> Td1(Nx*Ny), Id1(Nx*Ny), a_td1(Nx*Ny);

    double peak = T0_vol / gauss_sum;
    for(int i = 0; i < Nx; i++)
        for(int j = 0; j < Ny; j++) {
            double r2 = pow(i*dx - x_center, 2) + pow(j*dy - y_center, 2);
            T[idx(i,j)] = peak * exp(-SIGMA * r2);
        }

    double loss = 0.0;
    int data_idx = 0;

    for(int step = 0; step < Nt && data_idx < (int)data.size(); step++) {
        double current_time = step * dt;
        if(abs(current_time - data[data_idx].day) < dt * 0.5) {
            double model_v = 0;
            for(int k = 0; k < Nx*Ny; k++) model_v += T[k] * dx * dy;
            if(model_v < 1e-9) model_v = 1e-9;
            double res = log(model_v) - log(data[data_idx].volume);
            loss += res * res;
            data_idx++;
        }
        for(int i = 0; i < Nx; i++) {
            for(int j = 0; j < Ny; j++) {
                int c  = idx(i, j);
                int ip = (i+1 < Nx) ? i+1 : i-1;
                int im = (i-1 >= 0) ? i-1 : i+1;
                int jp = (j+1 < Ny) ? j+1 : j-1;
                int jm = (j-1 >= 0) ? j-1 : j+1;

                double laplace_T =
                    (T[idx(ip,j)] - 2*T[c] + T[idx(im,j)]) / (dx*dx) +
                    (T[idx(i,jp)] - 2*T[c] + T[idx(i,jm)]) / (dy*dy);

                double Tpart  = pDt * laplace_T + prt * T[c] * (1.0 - T[c]) - pht * T[c];
                double Ipart  = -pa * I[c] + pb * T[c];
                double ATpart =  pg * T[c] * (1.0 - a_t[c]);

                Td1[c]   = max(0.0, T[c]   + Tpart  * dt);
                Id1[c]   = max(0.0, I[c]   + Ipart  * dt);
                a_td1[c] = max(0.0, min(1.0, a_t[c] + ATpart * dt));
            }
        }
        T.swap(Td1); I.swap(Id1); a_t.swap(a_td1);
    }
    return loss / max(1, data_idx);
}

// ── Координатный спуск ──────────────────────────────────────
double coord_descent(double* p, const vector<ExperimentalData>& data,
                     int max_iter, bool verbose = false)
{
    auto eval = [&]() {
        return get_error(p[P_DT],p[P_RT],p[P_HT],p[P_A],p[P_B],p[P_G],p[P_T0], data);
    };

    double best_err = eval();
    for(int iter = 0; iter < max_iter; iter++) {
        for(int i = 0; i < N_PARAMS; i++) {
            if(!SPACE.optimize[i]) continue;

            double old_val = p[i];
            p[i] = min(SPACE.hi[i], old_val + SPACE.step[i]);
            double ep = eval();
            p[i] = max(SPACE.lo[i], old_val - SPACE.step[i]);
            double em = eval();

            if(ep < best_err && ep <= em) {
                p[i] = min(SPACE.hi[i], old_val + SPACE.step[i]);
                best_err = ep;
                SPACE.step[i] *= 1.2;
            } else if(em < best_err) {
                p[i] = max(SPACE.lo[i], old_val - SPACE.step[i]);
                best_err = em;
                SPACE.step[i] *= 1.2;
            } else {
                p[i] = old_val;
                SPACE.step[i] *= 0.5;
            }
        }
        if(verbose && iter % 30 == 0) {
            cout << "  iter=" << setw(4) << iter
                 << "  loss=" << fixed << setprecision(6) << best_err << "\n";
            cout.flush();
        }
        bool all_tiny = true;
        for(int i = 0; i < N_PARAMS; i++)
            if(SPACE.optimize[i] && SPACE.step[i] > 1e-10) { all_tiny = false; break; }
        if(all_tiny) break;
    }
    return best_err;
}

// ── Градиентный спуск ───────────────────────────────────────
double grad_descent(double* p, double lr, int max_iter,
                    const vector<ExperimentalData>& data, bool verbose = false)
{
    auto eval = [&]() {
        return get_error(p[P_DT],p[P_RT],p[P_HT],p[P_A],p[P_B],p[P_G],p[P_T0], data);
    };

    double best_err = eval();
    for(int iter = 0; iter < max_iter; iter++) {
        double g[N_PARAMS];
        for(int i = 0; i < N_PARAMS; i++) {
            if(!SPACE.optimize[i]) { g[i] = 0.0; continue; }
            double h = max(1e-6, abs(p[i]) * 1e-4);
            double old = p[i];
            p[i] = old + h; double e_plus  = eval();
            p[i] = old - h; double e_minus = eval();
            p[i] = old;
            g[i] = (e_plus - e_minus) / (2.0 * h);
        }
        for(int i = 0; i < N_PARAMS; i++) {
            if(!SPACE.optimize[i]) continue;
            p[i] = p[i] - lr * g[i];
            p[i] = max(SPACE.lo[i], min(SPACE.hi[i], p[i]));
        }
        double new_err = eval();
        if(new_err < best_err) best_err = new_err;
        else lr *= 0.7;

        if(verbose && iter % 30 == 0) {
            cout << "  iter=" << setw(4) << iter
                 << "  loss=" << fixed << setprecision(6) << best_err
                 << "  lr=" << scientific << setprecision(2) << lr << fixed << "\n";
            cout.flush();
        }
        if(lr < 1e-10) break;
    }
    return best_err;
}

// ── main ────────────────────────────────────────────────────
int main(int argc, char** argv) {
    string csv_path    = "";
    string method      = "coord";
    string out_json    = "best_params.json";
    string params_json = "";
    string space_json  = "";

    for(int i = 1; i < argc; i++) {
        string a = argv[i];
        if      (a == "--csv"    && i+1 < argc) csv_path    = argv[++i];
        else if (a == "--method" && i+1 < argc) method      = argv[++i];
        else if (a == "--out"    && i+1 < argc) out_json    = argv[++i];
        else if (a == "--params" && i+1 < argc) params_json = argv[++i];
        else if (a == "--space"  && i+1 < argc) space_json  = argv[++i];
    }

    if(csv_path.empty()) {
        cerr << "usage: grad_optim --csv data.csv [--method coord|grad] "
             << "[--out out.json] [--params params.json] [--space space.json]\n";
        return 1;
    }

    if(!params_json.empty()) load_params_json(params_json);
    if(!space_json.empty())  load_space_json(space_json);

    setup_grid();
    precompute_gauss_sum();

    // ── [+] ПРОВЕРКА УСТОЙЧИВОСТИ ДЛЯ ОПТИМИЗАТОРА ────────
    // Поскольку оптимизатор использует явный Эйлер (c=2),
    // проверяем условие для него.
    {
        double Dmax = std::max({Dc, Dch, Dim, SPACE.init[P_DT]});
        double c = 2.0; // Явный Эйлер
        double dt_diff = c / (2.0 * (Dmax/(dx*dx) + Dmax/(dy*dy)));
        
        // Также учитываем скорость роста rt (для реакций)
        double rmax = std::max({rc, SPACE.init[P_RT], SPACE.init[P_HT], 
                                kct, ki, uc, ut, ui});
        double dt_react = (rmax > 0.0) ? c / rmax : 1e300;
        
        double dt_crit = std::min(dt_diff, dt_react);

        if (dt > dt_crit) {
            int rec_Nt = (int)std::ceil(Tt / dt_crit) + 1;
            cerr << "\n[ERROR] Нарушено условие устойчивости в оптимизаторе!\n"
                 << "Шаг dt = " << dt << " больше критического dt_crit = " << dt_crit << ".\n"
                 << "Пожалуйста, увеличьте Nt (минимум до " << rec_Nt << ") в параметрах.\n\n";
            return 1; // Аварийный выход, Python перехватит ошибку
        }
    }

    vector<ExperimentalData> data = load_csv(csv_path);
    if(data.empty()) { cerr << "no data loaded\n"; return 1; }

    cout << "Loaded " << data.size() << " points\n";
    cout << "Method: " << method << "\n";
    cout << "Grid: " << Nx << "x" << Ny << " Nt=" << Nt << " dt=" << dt << "\n";
    cout << "Optimized:";
    for(int i = 0; i < N_PARAMS; ++i) if(SPACE.optimize[i])
        cout << " " << PARAM_NAMES[i];
    cout << "\n"; cout.flush();

    double p[N_PARAMS];
    p[P_DT] = SPACE.init[P_DT]; p[P_RT] = SPACE.init[P_RT];
    p[P_HT] = SPACE.init[P_HT]; p[P_A]  = SPACE.init[P_A];
    p[P_B]  = SPACE.init[P_B];  p[P_G]  = SPACE.init[P_G];
    p[P_T0] = SPACE.init[P_T0];

    double best_loss;
    if(method == "grad") {
        best_loss = grad_descent(p, 1e-3, 500, data, true);
    } else {
        best_loss = coord_descent(p, data, 400, true);
        double sf[N_PARAMS];
        for(int i = 0; i < N_PARAMS; ++i)
            sf[i] = (SPACE.hi[i]-SPACE.lo[i]) * 0.001;
        for(int i = 0; i < N_PARAMS; ++i) SPACE.step[i] = sf[i];
        best_loss = coord_descent(p, data, 500, true);
    }

    string traj_csv = out_json;
    { auto dot = traj_csv.find_last_of('.');
      if(dot != string::npos) traj_csv = traj_csv.substr(0, dot);
      traj_csv += "_traj.csv"; }

    // ── Траектория V(t) ─────────────────────────────────────
    {
        ofstream tf(traj_csv);
        tf << "day,volume\n";
        vector<double> Tm(Nx*Ny), Im(Nx*Ny, 0.0), atm(Nx*Ny, 0.0);
        vector<double> Tdm(Nx*Ny), Idm(Nx*Ny), atdm(Nx*Ny);

        double peak = p[P_T0] / gauss_sum;
        for(int i = 0; i < Nx; i++)
            for(int j = 0; j < Ny; j++) {
                double r2 = pow(i*dx - x_center, 2) + pow(j*dy - y_center, 2);
                Tm[idx(i,j)] = peak * exp(-SIGMA * r2);
            }
        int stride = max(1, Nt / 500);
        for(int step = 0; step < Nt; step++) {
            if(step % stride == 0) {
                double mv = 0;
                for(int k = 0; k < Nx*Ny; k++) mv += Tm[k] * dx * dy;
                tf << step * dt << "," << mv << "\n";
            }
            for(int i = 0; i < Nx; i++) {
                for(int j = 0; j < Ny; j++) {
                    int c  = idx(i, j);
                    int ip = (i+1 < Nx) ? i+1 : i-1;
                    int im = (i-1 >= 0) ? i-1 : i+1;
                    int jp = (j+1 < Ny) ? j+1 : j-1;
                    int jm = (j-1 >= 0) ? j-1 : j+1;
                    double laplace_T =
                        (Tm[idx(ip,j)] - 2*Tm[c] + Tm[idx(im,j)]) / (dx*dx) +
                        (Tm[idx(i,jp)] - 2*Tm[c] + Tm[idx(i,jm)]) / (dy*dy);
                    double Tpart  = p[P_DT] * laplace_T + p[P_RT] * Tm[c] * (1.0 - Tm[c]) - p[P_HT] * Tm[c];
                    double Ipart  = -p[P_A] * Im[c] + p[P_B] * Tm[c];
                    double ATpart =  p[P_G] * Tm[c] * (1.0 - atm[c]);
                    Tdm[c]  = max(0.0, Tm[c]  + Tpart  * dt);
                    Idm[c]  = max(0.0, Im[c]  + Ipart  * dt);
                    atdm[c] = max(0.0, min(1.0, atm[c] + ATpart * dt));
                }
            }
            Tm.swap(Tdm); Im.swap(Idm); atm.swap(atdm);
        }
        tf.close();
        cout << "Trajectory: " << traj_csv << "\n";
    }

    // ── JSON-результат ──────────────────────────────────────
    ofstream jf(out_json);
    jf << "{\n";
    jf << "  \"Dt\": "        << scientific << setprecision(10) << p[P_DT] << ",\n";
    jf << "  \"rt\": "        << fixed      << setprecision(10) << p[P_RT] << ",\n";
    jf << "  \"ht\": "        << fixed      << setprecision(10) << p[P_HT] << ",\n";
    jf << "  \"a\": "         << fixed      << setprecision(10) << p[P_A]  << ",\n";
    jf << "  \"b\": "         << fixed      << setprecision(10) << p[P_B]  << ",\n";
    jf << "  \"g\": "         << fixed      << setprecision(10) << p[P_G]  << ",\n";
    jf << "  \"T0_volume\": " << fixed      << setprecision(10) << p[P_T0] << ",\n";
    jf << "  \"loss\": "      << scientific << setprecision(10) << best_loss << ",\n";
    jf << "  \"method\": \""  << method << "\",\n";
    jf << "  \"n_points\": "  << data.size() << ",\n";
    jf << "  \"optimized\": [";
    bool first = true;
    for(int i = 0; i < N_PARAMS; ++i) if(SPACE.optimize[i]) {
        if(!first) jf << ", ";
        jf << "\"" << PARAM_NAMES[i] << "\"";
        first = false;
    }
    jf << "],\n";
    jf << "  \"traj_csv\": \"" << traj_csv << "\"\n";
    jf << "}\n";
    jf.close();

    cout << "\nSaved: " << out_json << "\n";
    cout << "Best loss: " << scientific << best_loss << "\n";
    return 0;
}