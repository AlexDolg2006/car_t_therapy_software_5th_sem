#pragma once
#include <string>
#include <fstream>
#include <map>
#include <iostream>

// Простейший парсер JSON-подобного файла: "key": value
// Вложенные объекты игнорируются (только плоские ключи).
struct Params {
    std::map<std::string, double> num;
    std::map<std::string, std::string> str;

    double getd(const std::string& k, double def) const {
        auto it = num.find(k); return it == num.end() ? def : it->second;
    }
    std::string gets(const std::string& k, const std::string& def) const {
        auto it = str.find(k); return it == str.end() ? def : it->second;
    }
};

inline Params load_params(const std::string& path) {
    Params p;
    std::ifstream f(path);
    if (!f) {
        std::cerr << "params file not found: " << path << "\n";
        return p;
    }
    std::string line;
    while (std::getline(f, line)) {
        auto c = line.find(':');
        if (c == std::string::npos) continue;

        auto strip = [](std::string s) {
            while (!s.empty() && (s.front()==' '||s.front()=='"'
                                ||s.front()=='\t'||s.front()=='{')) s.erase(s.begin());
            while (!s.empty() && (s.back()==' '||s.back()=='"'
                                ||s.back()==','||s.back()=='\n'
                                ||s.back()=='\r'||s.back()=='}')) s.pop_back();
            return s;
        };

        std::string key = strip(line.substr(0, c));
        std::string val = strip(line.substr(c + 1));
        if (key.empty() || val.empty()) continue;

        try { p.num[key] = std::stod(val); }
        catch (...) { p.str[key] = val; }
    }
    return p;
}