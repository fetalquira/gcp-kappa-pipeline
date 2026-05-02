# frontend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 1. Install dependencies using pip
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Extract from the src-layout
# This reaches deep into your uv-generated structure and copies ONLY the 
# inner 'shared' directory (containing schemas.py and __init__.py) into /app/shared
COPY shared/src/shared/ shared/

# 3. Copy the frontend code
COPY frontend/app.py .

# 4. Set Python Path
# This ensures Python looks in /app for the 'shared' folder
ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]