MIN_N = {10: 10, 25: 4, 75: 4}  # abaixo disso o percentil não significa nada; fica vazio

def percentil(valores, p):
    v = sorted(valores)
    if not v or len(v) < MIN_N.get(p, 1):
        return None
    k = (len(v) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)

def sem_outliers(valores):
    """Remove outliers por IQR."""
    if len(valores) < 4:
        return list(valores)
    q1, q3 = percentil(valores, 25), percentil(valores, 75)
    iqr = q3 - q1
    return [x for x in valores if q1 - 1.5 * iqr <= x <= q3 + 1.5 * iqr]
