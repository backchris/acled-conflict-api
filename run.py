import os
from dotenv import load_dotenv
from app import create_app
from app.config import Config

load_dotenv()
app = create_app(Config)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=True)
