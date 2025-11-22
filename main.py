from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Use port 5001 as agreed in the plan, or environment variable if set
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, port=port)
