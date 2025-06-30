import argparse
import configparser
import logging
import socket
import sys
import time
import threading

from env import BUFFER_SIZE,\
    PING,\
    EVENT_LOOP_TIMEOUT,\
    KEEPALIVE_TIMEOUT


mutex = threading.Lock()


def write2sock(sock, data):
    with mutex:
        sock.send(data)


def pipe2sock(pipe, sock):
    logging.debug(f'[pipe ==> sock] starting datatransfer')
    t = threading.current_thread()

    while getattr(t, 'do_run', True):
        try:
            data = pipe.readline()
            write2sock(sock, data.encode())

        except:
            break

    logging.debug(f'[pipe ==> sock] stopping datatransfer')


def sock2pipe(sock, pipe):
    logging.debug(f'[sock ==> pipe] starting datatransfer')
    t = threading.current_thread()

    while getattr(t, 'do_run', True):
        try:
            data = sock.recv(BUFFER_SIZE)

            if len(data) == 0:
                break

            pipe.write(data.decode())
            pipe.flush()

        except:
            break

    logging.debug(f'[sock ==> pipe] stopping datatransfer')


def sock_keepalive(sock, timeout):
    logging.debug(f'[sockkeepalive] starting')
    t = threading.current_thread()

    mark = int(time.time())

    while getattr(t, 'do_run', True):
        ts = int(time.time())
        if ts - mark >= timeout:
            mark = ts
            try:
                write2sock(sock, PING)
            except:
                break

        time.sleep(EVENT_LOOP_TIMEOUT)

    logging.debug(f'[sockkeepalive] stopping')


def main():
    logging.basicConfig(
        format='%(asctime)s %(levelname)8s %(message)s',
        level=logging.INFO,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c',
        '--config',
        default='client.ini',
        help='configuration file',
    )
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(
            (
                config['server']['hostname'],
                int(config['server']['port']),
            ),
        )

        handlers = []
        handlers.append(
            threading.Thread(
                target=sock2pipe,
                args=[s, sys.stdout],
            )
        )
        handlers.append(
            threading.Thread(
                target=pipe2sock,
                args=[sys.stdin, s],
            )
        )
        handlers.append(
            threading.Thread(
                target=sock_keepalive,
                args=[s, KEEPALIVE_TIMEOUT],
            )
        )

        for handler in handlers:
            handler.daemon = True
            handler.start()

        while True:
            if len([h for h in handlers if not h.is_alive()]) > 0:
                for handler in [h for h in handlers if h.is_alive()]:
                    handler.do_run = False

                break

            time.sleep(EVENT_LOOP_TIMEOUT)




if __name__ == '__main__':
    main()
