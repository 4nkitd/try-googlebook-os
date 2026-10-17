import fcntl
import os
from pathlib import Path
import subprocess
import sys


def setup(source, work):
    if os.geteuid() == 0:
        raise SystemExit("Run setup as your normal macOS user, not with sudo.")
    source = Path(source).expanduser().resolve()
    work = Path(work).expanduser().resolve()
    os.umask(0o077)
    work.parent.mkdir(parents=True, exist_ok=True)
    with (work.parent / "setup.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another setup is already running for this VM.")
        app = work / "host/Googlebook VM.app"
        if (work / "image/googlebook.raw").exists():
            raise SystemExit(
                f"Existing VM preserved at {work}. Open {app}; setup will not overwrite its disk."
            )
        env = dict(os.environ, GOOGLEBOOK_WORK=str(work))
        print(
            f"VM files: {work}\nSetup keeps the existing macOS installation untouched.",
            flush=True,
        )
        subprocess.run(
            ["/usr/bin/caffeinate", "-i", "/bin/bash", str(source / "install.sh")],
            env=env,
            check=True,
        )
        subprocess.run(["/usr/bin/open", str(app)], env=env, check=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: setup.py SOURCE_DIRECTORY WORK_DIRECTORY")
    setup(sys.argv[1], sys.argv[2])
