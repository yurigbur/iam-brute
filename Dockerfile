FROM python:3

RUN git clone https://github.com/yurigbur/iam-brute
WORKDIR /iam-brute
RUN pip install -r requirements.txt

ENTRYPOINT ["python iam-brute.py"]
