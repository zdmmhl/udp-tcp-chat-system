# UDP/TCP Chat System

A coursework client/server system for discussion threads, messaging and file transfer.

## Local setup

Python 3 and its standard library are used. `server.py` reads `credentials.txt` from its working directory; make a local copy of the synthetic `credentials.example.txt`.

```bash
python server.py 55001
python client.py 127.0.0.1 55001
```

Check `client.py` for the exact command-line syntax. This repository preserves the existing protocol and has not run an end-to-end network session.

The protocol uses UDP for commands and TCP for file transfer. Authentication is plaintext and storage is file-based. This is not a secure messaging product.


## Provenance

Originated in UNSW COMP9331. The report explicitly acknowledges using parts of the programming tutorial as a starting point. The root client/server pair is the selected baseline; additional client/server copies are excluded.

## Verification status

Python syntax was checked. An end-to-end client/server session has not been rerun.
