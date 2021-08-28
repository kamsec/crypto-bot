
import subprocess
from src.config import logger, set_bot_config


def git_error_check(proc):
    proc_returncode = proc.returncode
    if proc_returncode is not 0:
        proc_stderr = proc.stderr
        error = str(proc_stderr)[2:-3].replace(r'\n', '\n')  # 2 removes b', -3 removes \n'
        logger.error(f'[BACKUP] Git backup error. Message: {error}')
        set_bot_config(BACKUPS_ALLOWED=False)
        raise Exception(f'Git backup error. Message: {error}')

def pull_changes_from_remote():
    # git pull

    proc = subprocess.run(["git", "pull"], capture_output=True)
    git_error_check(proc)

def backup_data_from_RPi():
    # git add .
    # git commit -m "data update"
    # git push

    proc = subprocess.run(["git", "add", "."], capture_output=True)
    git_error_check(proc)
    proc = subprocess.run(["git", "commit", "-m", "Data update by RPi"], capture_output=True)
    git_error_check(proc)
    proc = subprocess.run(["git", "push"], capture_output=True)
    git_error_check(proc)
    return

# commit, no push, but whatever
def get_last_commit_time():
    # git --no-pager log -1 --format=%ai

    proc = subprocess.run(["git", "--no-pager", "log", "-1", "--format=%ai"], capture_output=True)
    # output is b'2021-08-23 19:27:51' +0200 or and sometimes +0100, soi need to grab that offset as well
    last_commit_time = str(proc.stdout)[2:21]
    last_commit_offset = -int(str(proc.stdout)[24])  # -2 or -1 so can be passed directly as h= utils functions
    return last_commit_time, last_commit_offset

