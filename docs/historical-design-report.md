# Historical Program Design Report

An edited English text edition of the 2025 COMP9331 report. The program's command interface differs from the sample interaction because it was developed from the Week 5 programming tutorial. The report explicitly acknowledges borrowed tutorial code.

Most operations use UDP. Upload and download operations use TCP for file data. The author describes an additional UDP control socket for the transfer handshake and records uncertainty about why the original client socket could not be reused. That uncertainty is retained; it is not presented as a resolved networking principle.

The implementation supports multiple clients and uses a user lock. The original demonstration arranged separate client working folders and a server folder so uploads and downloads had distinct storage locations. Each process was launched from its own folder. Screenshots showed a server and two clients exchanging messages; the screenshot evidence is not bundled in this text edition.

This is historical design reasoning, not a secure messaging architecture. Plaintext authentication, file-based storage, command compatibility, concurrency, and transfer error handling require review before broader use. The end-to-end session was not rerun during this documentation update.
