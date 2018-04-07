FROM python:3.6
WORKDIR /Users/mkunissery/gitclone
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN git clone https://github.com/mkunissery/data602A2
EXPOSE 5000
CMD [ "python", "/Users/mkunissery/gitclone/data602A2/main.py" ]


