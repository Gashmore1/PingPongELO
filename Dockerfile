FROM python:3.11

# upgrade pip
RUN pip install --upgrade pip

RUN mkdir /home/app/ 
RUN mkdir -p /var/log/flask-app && touch /var/log/flask-app/flask-app.err.log && touch /var/log/flask-app/flask-app.out.log
WORKDIR /home/app

# copy all the files to the container
COPY requirements.txt .
COPY src src
COPY tests tests
COPY pyproject.toml .
COPY pytest.ini .

# python setup
RUN export FLASK_APP=scoring.py
RUN pip install -r requirements.txt
RUN python -m build && pip install dist/pingpongelo-*.tar.gz

# define the port number the container should expose
EXPOSE 3000

CMD ["python", "src/PingPongELO/index.py"]
