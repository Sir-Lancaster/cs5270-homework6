# runtime environment
FROM python:3.14-slim

# copy program in
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY consumer/ .

# the command to run
ENTRYPOINT ["python", "consumer.py"]