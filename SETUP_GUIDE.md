# Gaboda Setup Guide

## 1. Python Environment Setup (Required)
The automated system could not detect a valid Python installation. Please follow these steps:

1.  **Install Python**: Download and install Python (3.8 or higher) from [python.org](https://www.python.org/).
2.  **Add to PATH**: During installation, ensure you check **"Add Python to PATH"**.
3.  **Install Dependencies**: Open a terminal in the project folder and run:
    ```bash
    pip install -r requirements.txt
    ```

## 2. Supabase Configuration (Required)
To make the login work, you must configure the Redirect URL in your Supabase Dashboard.

1.  Go to your **Supabase Project Dashboard**.
2.  Navigate to **Authentication** -> **URL Configuration**.
3.  In the **Redirect URLs** section, add:
    - `http://localhost:5000`
    - `http://127.0.0.1:5000`
4.  Click **Save**.

## 3. Run the Application
After installing dependencies and configuring Supabase:
```bash
python main.py
```
