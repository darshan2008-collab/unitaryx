"""Root launcher for Unitary X.

This file delegates to the freelancer app so running `python app.py`
from the workspace root always serves the same templates/static assets.
"""

import os

from freelancer.app import app


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("FLASK_RUN_PORT", "10184")))
    app.run(host="0.0.0.0", port=port, debug=False)
