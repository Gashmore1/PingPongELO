FROM python:3.11

# upgrade pip
RUN pip install --upgrade pip

RUN mkdir /home/app/ 
RUN mkdir -p /var/log/flask-app && touch /var/log/flask-app/flask-app.err.log && touch /var/log/flask-app/flask-app.out.log
WORKDIR /home/app

# copy all the files to the container
COPY __init__.py game.py index.py player.py requirements.txt scoring.py .
COPY tests tests
COPY templates templates
COPY static static
COPY __pycache__ __pycache__

# python setup
RUN export FLASK_APP=scoring.py
RUN pip install -r requirements.txt

# define the port number the container should expose
EXPOSE 3000

CMD ["python", "index.py"]
