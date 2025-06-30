# stockfish-remote

## server

Listens a tcp socket, runs stockfish and connects them.

```shell
python server.py -s <stockfish-binary>
```

Stockfish can be downloaded from [github](https://github.com/official-stockfish/Stockfish/releases)

## client

Has to been compiled with `pyinstaller`. Change a server hostname in `client.ini`.

```shell
python # will be installed from store
pip install pyinstaller
# add packages script dir to path
pyinstaller -F client.py
client.exe
```
