FROM python:3.9-slim
WORKDIR /app
COPY scanner.py /app/
ADD requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
CMD ["python", "scanner.py"]