from flask import Flask, render_template_string
from pathlib import Path
import json

app = Flask(__name__)
ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "data" / "reports"

HTML_TEMPLATE = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LottoBrain</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #08111f; color: #f5f7fb; }
    .container { max-width: 1100px; margin: 0 auto; padding: 32px; }
    .card { background: #13233d; padding: 20px; border-radius: 16px; margin-bottom: 16px; }
    h1, h2 { color: #7dd3fc; }
    .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
    .pill { display: inline-block; padding: 6px 10px; border-radius: 999px; background: #1d4ed8; margin-right: 8px; margin-bottom: 8px; }
    code { background: #0f172a; padding: 2px 6px; border-radius: 6px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>LottoBrain</h1>
    <p>Dashboard de análise estatística, modelos de machine learning e previsões para loterias.</p>
    <div class="card">
      <h2>Resumo executivo</h2>
      <div class="grid">
        <div><strong>Loterias cobertas</strong><br>6</div>
        <div><strong>Modelos disponíveis</strong><br>1 modelo inicial</div>
        <div><strong>Atualização</strong><br>Pipeline automático</div>
      </div>
    </div>
    {% for lottery in reports %}
    <div class="card">
      <h2>{{ lottery.name }}</h2>
      <p><strong>Estatísticas:</strong> draws={{ lottery.stats.draw_count }}, média de gaps={{ lottery.stats.average_gap }}</p>
      <div>
        {% for prediction in lottery.predictions.predictions %}
        <span class="pill">{{ prediction.numbers }} · {{ prediction.probability }}</span>
        {% endfor %}
      </div>
      <p><strong>Modelos:</strong></p>
      <ul>
        {% for model in lottery.models.models %}
        <li>{{ model.name }} — acurácia {{ model.accuracy }} — {{ model.description }}</li>
        {% endfor %}
      </ul>
    </div>
    {% endfor %}
  </div>
</body>
</html>
"""


@app.route("/")
def index():
    reports = []
    for report_path in sorted(REPORTS_DIR.glob("*_report.json")):
        with report_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        reports.append({
            "name": payload["lottery"],
            "stats": payload["stats"],
            "predictions": payload["predictions"],
            "models": payload["models"],
        })

    return render_template_string(HTML_TEMPLATE, reports=reports)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
