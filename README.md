# CAPEX 80kW Publico

App Streamlit separada de `PILOTOS_ANA` para compartir solo el dashboard `Capex80kW`.

## Ejecutar local

```bash
cd capex80kw_publico
streamlit run app.py
```

## Desplegar aparte

Usa esta carpeta como servicio independiente en Render.

- `buildCommand`: `pip install -r requirements.txt`
- `startCommand`: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`

Asi el link compartido apuntara solo a esta app y no al multipage completo de `PILOTOS_ANA`.
