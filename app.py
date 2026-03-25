"""
Punto de entrada para Flask CLI (flask run, flask db, flask jobs).

Todo el codigo de la app vive en la raiz del proyecto (auth/, core/, …).
La factoria esta en application.py para no chocar el nombre con este fichero.
"""

from application import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
