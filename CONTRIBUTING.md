# Contributing to Duck Monitoring

First off, thank you for considering contributing to Duck Monitoring! It's people like you that make Duck Monitoring such a great tool.

## Where do I go from here?

If you've noticed a bug or have a feature request, make sure to check our Issues tab to see if someone else has already created a ticket. If not, go ahead and make one!

## Setting up your environment

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally.
3. **Backend Setup**:
    ```bash
    cd backend_django
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python manage.py migrate
    ```
4. **Frontend Setup**:
    ```bash
    cd frontend
    npm install
    npm start
    ```

## Submitting a Pull Request

1. **Branch** off of `main` for your work.
2. Write clean, modular code.
3. If you are changing the API or backend logic, please ensure existing tests pass.
4. **Submit a Draft PR** early if you want feedback.
5. Once ready, un-draft it and request a review.

## Code Style

* **Python**: We follow standard PEP 8.
* **React**: We use ESLint standard configurations. Please format your components before submitting.
