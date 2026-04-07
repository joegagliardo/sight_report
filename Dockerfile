FROM python:3.11-slim

WORKDIR /app

# Ensure standard output is not buffered to help with Cloud Run logging
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the Flask web app.
# Cloud Run defines PORT which defaults to 8080, which app.py handles.
CMD ["python", "app.py"]
