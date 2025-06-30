# stockfish-remote

## server

Listens a tcp socket, runs stockfish and connect them.

```shell
python server.py -s <stockfish-binary>
```

## client

Has to been compiled with `pyinstaller`. Change server hostname in `client.ini`.

```shell
python # will be installed from store
pip install pyinstaller
# add packages script dir to path
pyinstall -F client.py
client.exe
```
