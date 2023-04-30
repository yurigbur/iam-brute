FROM python:3

RUN git clone https://github.com/yurigbur/iam-brute.git
WORKDIR /iam-brute
RUN pip install -r requirements.txt

ENTRYPOINT [ "./iam-brute.py" ]
