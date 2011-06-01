
import os

from norc.settings import NORC_LOG_DIR, BACKUP_SYSTEM

if BACKUP_SYSTEM == 'AmazonS3':
    from norc.norc_utils.aws import set_s3_key
    from norc.settings import (AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME)


def s3_backup(fp, target):
    NUM_TRIES = 3
    for i in range(NUM_TRIES):
        try:
            set_s3_key(target, fp)
            return True
        except:
            if i == NUM_TRIES - 1:
                raise
    return False

BACKUP_SYSTEMS = {
    'AmazonS3': s3_backup,
}

def backup_log(rel_log_path):
    log_path = os.path.join(NORC_LOG_DIR, rel_log_path)
    log_file = open(log_path, 'rb')
    target = os.path.join('norc_logs/', rel_log_path)
    try:
        return _backup_file(log_file, target)
    finally:
        log_file.close()

def _backup_file(fp, target):
    if BACKUP_SYSTEM:
        return BACKUP_SYSTEMS[BACKUP_SYSTEM](fp, target)
    else:
        return False
