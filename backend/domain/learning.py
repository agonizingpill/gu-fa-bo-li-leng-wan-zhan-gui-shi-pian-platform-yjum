import numpy as np
from sklearn.linear_model import Lasso
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

def features(row):
    return [row[key] for key in ('heat', 'thick', 'target')]

def calculate(data):
    archive = sorted(data['history'], key=lambda row: row['heat'])
    holdout = [row for index, row in enumerate(archive) if index % 4 == 0]
    train = [row for index, row in enumerate(archive) if index % 4 != 0]
    model = make_pipeline(PolynomialFeatures(degree=2, include_bias=False),
                          StandardScaler(), Lasso(alpha=data['penalty'],max_iter=20000))
    model.fit([features(row) for row in train], [row['measured'] for row in train])
    errors = model.predict([features(row) for row in holdout]) - [row['measured'] for row in holdout]
    terms = model[0].get_feature_names_out(['温度','片厚','目标弯度'])
    return {'prediction': round(float(model.predict([features(data['coupon'])])[0]),3),
            'mae': round(float(np.mean(np.abs(errors))),3), 'held_out': len(holdout),
            'terms': [term for term, coef in zip(terms, model[-1].coef_) if abs(coef) > 1e-10]}
