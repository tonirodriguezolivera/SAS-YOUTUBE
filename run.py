"""Alias opcional; la entrada principal es app.py."""

from application import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
