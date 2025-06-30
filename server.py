import argparse
import logging
import os.path
import re
import select
import socket
import subprocess
import sys
import threading
import time

from env import \
    SELECT_TIMEOUT,\
    EVENT_LOOP_TIMEOUT,\
    BUFFER_SIZE,\
    PING


REGEXP = re.compile(r'^(?P<pre>.*)?(?P<name>Stockfish) [0-9]+\.[0-9]+(?P<app>.*)$')
REPLACEMENT = r'\g<pre>\g<name> Remote\g<app>'


def proc2conn(proc, conn, addr):
    logging.info(f'[{addr[0]}:{addr[1]}][{proc.pid}] starting datatrasfer from proc to sock')
    t = threading.current_thread()

    while getattr(t, 'do_run', True):
        try:
            ready = select.select([proc.stdout], [], [], SELECT_TIMEOUT)
            if ready[0]:
                data = proc.stdout.readline()

                # Replace stockfish version to 'Remote'
                decoded = data.decode()
                if REGEXP.match(decoded):
                    decoded = REGEXP.sub(REPLACEMENT, decoded)

                logging.debug(f'[{addr[0]}:{addr[1]}][{proc.pid}] send: {decoded.strip()}')
                conn.send(decoded.encode())
        except:
            break

    logging.info(f'[{addr[0]}:{addr[1]}][{proc.pid}] stopping datatransfer from proc to sock')


def conn2proc(conn, addr, proc):
    logging.info(f'[{addr[0]}:{addr[1]}][{proc.pid}] starting datatrasfer from sock to proc')

    conn.setblocking(0)
    t = threading.current_thread()

    while getattr(t, 'do_run', True):
        try:
            ready = select.select([conn], [], [], SELECT_TIMEOUT)
            if ready[0]:
                data = conn.recv(BUFFER_SIZE)

                if len(data) == 0:
                    break

                logging.debug(f'[{addr[0]}:{addr[1]}][{proc.pid}] recv: {data.decode().strip()}')

                if data == PING:
                    continue

                proc.stdin.write(data)
                proc.stdin.flush()
        except:
            break

    logging.info(f'[{addr[0]}:{addr[1]}][{proc.pid}] stopping datatransfer from sock to proc')


def conn(connection, address, stockfish):
    logging.debug(f'[{address[0]}:{address[1]}] accepted connection')

    process = subprocess.Popen(
        [stockfish],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    handlers = []
    handlers.append(
        threading.Thread(
            target=proc2conn,
            args=[
                process,
                connection,
                address,
            ],
        ),
    )
    handlers.append(
        threading.Thread(
            target=conn2proc,
            args=[
                connection,
                address,
                process,
            ],
        ),
    )

    for handler in handlers:
        handler.daemon = True
        handler.start()

    stop = False

    while True:
        if (process.poll() is not None) or \
            (len([h for h in handlers if not h.is_alive()]) > 0):

            for handler in [h for h in handlers if not h.is_alive()]:
                handler.do_run = False

            process.kill()
            break

        time.sleep(EVENT_LOOP_TIMEOUT)

    connection.close()
    logging.info(f'[{address[0]}:{address[1]}] connection closed')


def main():
    logging.basicConfig(
        format='%(asctime)s %(levelname)8s %(message)s',
        level=logging.DEBUG,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-a',
        '--address',
        default='0.0.0.0',
        help='listen on this address',
    )
    parser.add_argument(
        '-p',
        '--port',
        default=9999,
        help='listen on this port',
    )
    parser.add_argument(
        '-s',
        '--stockfish',
        required=True,
        help='stockfish executable engine',
    )

    args = parser.parse_args()

    address = args.address
    port = args.port
    stockfish = args.stockfish

    if not os.path.isfile(stockfish):
        sys.exit(f'Stockfish {stockfish} not found')

    logging.debug(f'Found {stockfish}')

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((address, port,))
        s.listen(5)

        logging.info(f'Started server on {address}:{port}')

        while True:
            try:
                ready = select.select([s], [], [])
                if ready[0]:
                    connection, address = s.accept()
                    connection_handler = threading.Thread(
                        target=conn,
                        args=[
                            connection,
                            address,
                            stockfish,
                        ],
                    )
                    connection_handler.start()
            except:
                break


if __name__ == '__main__':
    main()
