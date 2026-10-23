import numpy as np
import matplotlib as mpl
from matplotlib.figure import Figure

# Определяем переменные и их подписи
VARIABLES = ['C', 'T', 'I', 'a_t', 'Ch', 'Im']
TITLES = {
    'C':   'CAR-T клетки',
    'T':   'Опухолевые клетки',
    'I':   'Иммуносупрессия',
    'a_t': 'Активация CAR-T',
    'Ch':  'Хемокины',
    'Im':  'Иммуномодуляторы',
}

# Задаем красивые цветовые карты (colormaps) для каждой переменной
COLORMAPS = {
    'C':   'Blues',      # Синий (как на рис. а)
    'T':   'Reds',       # Красный (как на рис. б)
    'I':   'Greens',     # Зеленый (как на рис. в)
    'a_t': 'Purples',    # Фиолетовый (как на рис. г)
    'Ch':  'cividis',    # Желто-синий (как на рис. д)
    'Im':  'plasma',     # Оранжево-фиолетовый (как на рис. е)
}

def build_grid(day_data, variable):
    pivot = day_data.pivot_table(index='y', columns='x',
                                 values=variable, aggfunc='first')
    x_arr = pivot.columns.to_numpy()
    y_arr = pivot.index.to_numpy()
    Z = pivot.to_numpy(dtype=float)
    X, Y = np.meshgrid(x_arr, y_arr)
    return X, Y, Z

def draw_spatial(fig: Figure, df, day: float, variable: str = 'T'):
    fig.clear()
    ax = fig.add_subplot(111)

    # Фильтруем данные на нужный день
    day_data = df[np.abs(df['time'] - day) < 0.01]
    if day_data.empty:
        ax.set_title("Нет данных")
        fig.canvas.draw_idle()
        return

    X, Y, Z = build_grid(day_data, variable)
    Z_raw = Z.copy()
    
    # Логарифмирование для опухоли, если значения слишком малы
    cbar_label = 'Концентрация'
    if variable == 'T' and Z.max() < 0.1:
        Z = np.log10(Z + 1e-20)
        cbar_label = 'log10(плотность)'

    # Выбираем цветовую карту
    cmap = COLORMAPS.get(variable, 'viridis')

    # 1. Заливка (плавный градиент)
    # Используем 50 уровней, чтобы переходы были гладкими
    contour = ax.contourf(X, Y, Z, levels=50, cmap=cmap)
    
    # 2. Контурные линии (опционально, для красоты)
    ax.contour(X, Y, Z, levels=10, colors='black', linewidths=0.3, alpha=0.3)

    # Добавляем Colorbar
    cbar = fig.colorbar(contour, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(cbar_label)

    # Оформление осей
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_title(f"{TITLES.get(variable, variable)} — день {day:.1f}")
    ax.grid(True, linestyle='--', linewidth=0.5, color='gray', alpha=0.5)
    ax.set_aspect('equal')

    # Выводим максимальное значение в углу
    val = np.nanmax(Z_raw)
    ax.text(0.03, 0.97, f"max={val:.3e}",
            transform=ax.transAxes, fontsize=10, va='top',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="black", linewidth=0.8, alpha=0.85))

    fig.tight_layout()
    fig.canvas.draw_idle()